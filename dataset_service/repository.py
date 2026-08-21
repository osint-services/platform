import json
from math import asin, cos, radians, sin, sqrt
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from .models import DatasetImportRequest, DatasetImportResult, RejectedRow


PROFILE_FIELDS = (
    "username",
    "platform",
    "profile_url",
    "display_name",
    "bio",
    "location",
    "website",
    "verified",
    "protected",
    "created_at",
    "profile_image_url",
    "profile_banner_url",
    "followers_count",
    "following_count",
    "post_count",
    "listed_count",
    "like_count",
    "media_count",
    "observed_at",
    "confidence",
    "source",
    "latitude",
    "longitude",
    "location_accuracy",
    "location_source",
)

PHONE_FIELDS = (
    "phone_number",
    "valid",
    "national_format",
    "country_code",
    "caller_name",
    "caller_type",
    "carrier_name",
    "line_type",
    "location",
    "observed_at",
    "confidence",
    "source",
)

ENTITY_FIELDS = tuple(dict.fromkeys(PROFILE_FIELDS + PHONE_FIELDS))

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    record_type TEXT NOT NULL CHECK(record_type IN ('entity', 'profile', 'phone')),
    filename TEXT,
    imported_at TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    rejected_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    display_name TEXT,
    bio TEXT,
    location TEXT,
    website TEXT,
    observed_at TEXT,
    confidence REAL,
    source TEXT,
    latitude REAL,
    longitude REAL,
    location_accuracy TEXT,
    location_source TEXT,
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile_records (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    entity_id TEXT REFERENCES entities(id) ON DELETE CASCADE,
    platform TEXT,
    username TEXT,
    username_normalized TEXT,
    profile_url TEXT,
    display_name TEXT,
    bio TEXT,
    location TEXT,
    website TEXT,
    verified INTEGER,
    protected INTEGER,
    created_at TEXT,
    profile_image_url TEXT,
    profile_banner_url TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    post_count INTEGER,
    listed_count INTEGER,
    like_count INTEGER,
    media_count INTEGER,
    observed_at TEXT,
    confidence REAL,
    source TEXT,
    latitude REAL,
    longitude REAL,
    location_accuracy TEXT,
    location_source TEXT,
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS phone_records (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    entity_id TEXT REFERENCES entities(id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    valid INTEGER,
    national_format TEXT,
    country_code TEXT,
    caller_name TEXT,
    caller_type TEXT,
    carrier_name TEXT,
    line_type TEXT,
    location TEXT,
    observed_at TEXT,
    confidence REAL,
    source TEXT,
    raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_dataset ON entities(dataset_id);
CREATE INDEX IF NOT EXISTS idx_profile_username ON profile_records(username_normalized);
CREATE INDEX IF NOT EXISTS idx_profile_entity ON profile_records(entity_id);
CREATE INDEX IF NOT EXISTS idx_profile_display_name ON profile_records(display_name);
CREATE INDEX IF NOT EXISTS idx_phone_number ON phone_records(phone_number);
CREATE INDEX IF NOT EXISTS idx_phone_entity ON phone_records(entity_id);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"'{value}' is not a boolean")


def parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    number = int(str(value).replace(",", "").strip())
    if number < 0:
        raise ValueError("metric values cannot be negative")
    return number


def parse_confidence(value: Any) -> float | None:
    if value is None or value == "":
        return None
    confidence = float(value)
    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be between 0 and 1")
    return confidence


def parse_coordinate_pair(latitude_value: Any, longitude_value: Any) -> tuple[float | None, float | None]:
    has_latitude = latitude_value is not None and str(latitude_value).strip() != ""
    has_longitude = longitude_value is not None and str(longitude_value).strip() != ""
    if has_latitude != has_longitude:
        raise ValueError("latitude and longitude must be provided together")
    if not has_latitude:
        return None, None
    latitude = float(latitude_value)
    longitude = float(longitude_value)
    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180")
    return latitude, longitude


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_miles = 3958.7613
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, (lat1, lon1, lat2, lon2))
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    value = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    return 2 * earth_radius_miles * asin(sqrt(value))


def normalize_username(value: Any) -> str | None:
    username = clean_text(value)
    return username.lstrip("@").lower() if username else None


def username_from_url(value: Any) -> str | None:
    url = clean_text(value)
    if not url:
        return None
    path = urlparse(url).path.strip("/")
    return normalize_username(path.split("/")[0]) if path else None


def normalize_phone(value: Any) -> str:
    phone = clean_text(value)
    if not phone:
        raise ValueError("phone_number is required")
    has_plus = phone.startswith("+")
    digits = re.sub(r"\D", "", phone)
    if not has_plus or not 8 <= len(digits) <= 15:
        raise ValueError("phone_number must use E.164 format, for example +18135551212")
    return f"+{digits}"


class DatasetRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            datasets_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'datasets'"
            ).fetchone()
            profile_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(profile_records)")
            }
            if datasets_sql and (
                "'entity'" not in datasets_sql["sql"] or "entity_id" not in profile_columns
            ):
                self.migrate_legacy_schema(connection)
            else:
                connection.executescript(SCHEMA_SQL)
            self.ensure_geospatial_columns(connection)

    @staticmethod
    def ensure_geospatial_columns(connection: sqlite3.Connection) -> None:
        for table in ("entities", "profile_records"):
            columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            for name, column_type in (
                ("latitude", "REAL"),
                ("longitude", "REAL"),
                ("location_accuracy", "TEXT"),
                ("location_source", "TEXT"),
            ):
                if name not in columns:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_entity_coordinates ON entities(latitude, longitude)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_profile_coordinates ON profile_records(latitude, longitude)")

    @staticmethod
    def migrate_legacy_schema(connection: sqlite3.Connection) -> None:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.executescript(
            """
            ALTER TABLE datasets RENAME TO legacy_datasets;
            ALTER TABLE profile_records RENAME TO legacy_profile_records;
            ALTER TABLE phone_records RENAME TO legacy_phone_records;
            """
        )
        connection.executescript(SCHEMA_SQL)
        connection.executescript(
            """
            INSERT INTO datasets
                (id, name, record_type, filename, imported_at, row_count, rejected_count)
            SELECT id, name, record_type, filename, imported_at, row_count, rejected_count
            FROM legacy_datasets;

            INSERT INTO profile_records (
                id, dataset_id, entity_id, platform, username, username_normalized,
                profile_url, display_name, bio, location, website, verified,
                protected, created_at, profile_image_url, profile_banner_url,
                followers_count, following_count, post_count, listed_count,
                like_count, media_count, observed_at, confidence, source, raw_json
            )
            SELECT
                id, dataset_id, NULL, platform, username, username_normalized,
                profile_url, display_name, bio, location, website, verified,
                protected, created_at, profile_image_url, profile_banner_url,
                followers_count, following_count, post_count, listed_count,
                like_count, media_count, observed_at, confidence, source, raw_json
            FROM legacy_profile_records;

            INSERT INTO phone_records (
                id, dataset_id, entity_id, phone_number, valid, national_format,
                country_code, caller_name, caller_type, carrier_name,
                line_type, location, observed_at, confidence, source, raw_json
            )
            SELECT
                id, dataset_id, NULL, phone_number, valid, national_format,
                country_code, caller_name, caller_type, carrier_name,
                line_type, location, observed_at, confidence, source, raw_json
            FROM legacy_phone_records;

            DROP TABLE legacy_profile_records;
            DROP TABLE legacy_phone_records;
            DROP TABLE legacy_datasets;
            """
        )
        connection.executescript(SCHEMA_SQL)

    @staticmethod
    def mapped_row(
        row: dict[str, Any], mapping: dict[str, str], canonical_fields: tuple[str, ...]
    ) -> dict[str, Any]:
        return {
            field: row.get(mapping.get(field, field))
            for field in canonical_fields
        }

    def import_dataset(self, request: DatasetImportRequest) -> DatasetImportResult:
        dataset_id = str(uuid4())
        entities: list[dict[str, Any]] = []
        profiles: list[dict[str, Any]] = []
        phones: list[dict[str, Any]] = []
        rejected: list[RejectedRow] = []
        imported = 0

        for row_number, raw_row in enumerate(request.rows, start=1):
            try:
                if request.record_type.value == "entity":
                    entity, profile, phone = self.prepare_entity(
                        raw_row, request.mapping, request.name
                    )
                    entities.append(entity)
                    if profile:
                        profiles.append(profile)
                    if phone:
                        phones.append(phone)
                elif request.record_type.value == "profile":
                    profiles.append(
                        self.prepare_profile(raw_row, request.mapping, request.name)
                    )
                else:
                    phones.append(
                        self.prepare_phone(raw_row, request.mapping, request.name)
                    )
                imported += 1
            except (TypeError, ValueError) as exc:
                rejected.append(RejectedRow(row_number=row_number, reason=str(exc)))

        imported_at = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO datasets
                    (id, name, record_type, filename, imported_at, row_count, rejected_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    request.name.strip(),
                    request.record_type.value,
                    request.filename,
                    imported_at,
                    imported,
                    len(rejected),
                ),
            )

            if entities:
                connection.executemany(
                    """
                    INSERT INTO entities (
                        id, dataset_id, display_name, bio, location, website,
                        observed_at, confidence, source, latitude, longitude,
                        location_accuracy, location_source, raw_json
                    ) VALUES (
                        :id, :dataset_id, :display_name, :bio, :location, :website,
                        :observed_at, :confidence, :source, :latitude, :longitude,
                        :location_accuracy, :location_source, :raw_json
                    )
                    """,
                    [dict(record, dataset_id=dataset_id) for record in entities],
                )
            if profiles:
                connection.executemany(
                    """
                    INSERT INTO profile_records (
                        id, dataset_id, entity_id, platform, username, username_normalized,
                        profile_url, display_name, bio, location, website, verified,
                        protected, created_at, profile_image_url, profile_banner_url,
                        followers_count, following_count, post_count, listed_count,
                        like_count, media_count, observed_at, confidence, source,
                        latitude, longitude, location_accuracy, location_source, raw_json
                    ) VALUES (
                        :id, :dataset_id, :entity_id, :platform, :username, :username_normalized,
                        :profile_url, :display_name, :bio, :location, :website, :verified,
                        :protected, :created_at, :profile_image_url, :profile_banner_url,
                        :followers_count, :following_count, :post_count, :listed_count,
                        :like_count, :media_count, :observed_at, :confidence, :source,
                        :latitude, :longitude, :location_accuracy, :location_source, :raw_json
                    )
                    """,
                    [
                        dict(record, dataset_id=dataset_id, entity_id=record.get("entity_id"))
                        for record in profiles
                    ],
                )
            if phones:
                connection.executemany(
                    """
                    INSERT INTO phone_records (
                        id, dataset_id, entity_id, phone_number, valid, national_format,
                        country_code, caller_name, caller_type, carrier_name,
                        line_type, location, observed_at, confidence, source, raw_json
                    ) VALUES (
                        :id, :dataset_id, :entity_id, :phone_number, :valid, :national_format,
                        :country_code, :caller_name, :caller_type, :carrier_name,
                        :line_type, :location, :observed_at, :confidence, :source, :raw_json
                    )
                    """,
                    [
                        dict(record, dataset_id=dataset_id, entity_id=record.get("entity_id"))
                        for record in phones
                    ],
                )

        return DatasetImportResult(
            dataset_id=dataset_id,
            imported=imported,
            rejected=len(rejected),
            rejected_rows=rejected[:100],
            profile_identifiers=len(profiles),
            phone_identifiers=len(phones),
        )

    def prepare_entity(
        self, raw_row: dict[str, Any], mapping: dict[str, str], dataset_name: str
    ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        values = self.mapped_row(raw_row, mapping, ENTITY_FIELDS)
        has_profile = bool(
            normalize_username(values["username"]) or username_from_url(values["profile_url"])
        )
        has_phone = bool(clean_text(values["phone_number"]))
        if not has_profile and not has_phone:
            raise ValueError("username, profile_url, or phone_number is required")

        entity_id = str(uuid4())
        latitude, longitude = parse_coordinate_pair(values["latitude"], values["longitude"])
        observed_at = clean_text(values["observed_at"]) or utc_now()
        confidence = parse_confidence(values["confidence"])
        source = clean_text(values["source"]) or dataset_name
        display_name = clean_text(values["display_name"]) or clean_text(
            values["caller_name"]
        )
        entity = {
            "id": entity_id,
            "display_name": display_name,
            "bio": clean_text(values["bio"]),
            "location": clean_text(values["location"]),
            "website": clean_text(values["website"]),
            "observed_at": observed_at,
            "confidence": confidence,
            "source": source,
            "latitude": latitude,
            "longitude": longitude,
            "location_accuracy": clean_text(values["location_accuracy"]),
            "location_source": clean_text(values["location_source"]),
            "raw_json": json.dumps(raw_row, default=str),
        }

        profile = (
            self.prepare_profile(raw_row, mapping, dataset_name) if has_profile else None
        )
        phone = self.prepare_phone(raw_row, mapping, dataset_name) if has_phone else None
        if profile:
            profile["entity_id"] = entity_id
            profile["display_name"] = profile["display_name"] or display_name
        if phone:
            phone["entity_id"] = entity_id
            phone["caller_name"] = phone["caller_name"] or display_name
        return entity, profile, phone

    def prepare_profile(
        self, raw_row: dict[str, Any], mapping: dict[str, str], dataset_name: str
    ) -> dict[str, Any]:
        values = self.mapped_row(raw_row, mapping, PROFILE_FIELDS)
        username = clean_text(values["username"])
        username_normalized = normalize_username(username) or username_from_url(
            values["profile_url"]
        )
        if not username_normalized:
            raise ValueError("username or profile_url is required")
        username = username or username_normalized
        latitude, longitude = parse_coordinate_pair(values["latitude"], values["longitude"])

        return {
            "id": str(uuid4()),
            "platform": clean_text(values["platform"]) or "Imported",
            "username": username.lstrip("@"),
            "username_normalized": username_normalized,
            "profile_url": clean_text(values["profile_url"]),
            "display_name": clean_text(values["display_name"]),
            "bio": clean_text(values["bio"]),
            "location": clean_text(values["location"]),
            "website": clean_text(values["website"]),
            "verified": parse_bool(values["verified"]),
            "protected": parse_bool(values["protected"]),
            "created_at": clean_text(values["created_at"]),
            "profile_image_url": clean_text(values["profile_image_url"]),
            "profile_banner_url": clean_text(values["profile_banner_url"]),
            "followers_count": parse_int(values["followers_count"]),
            "following_count": parse_int(values["following_count"]),
            "post_count": parse_int(values["post_count"]),
            "listed_count": parse_int(values["listed_count"]),
            "like_count": parse_int(values["like_count"]),
            "media_count": parse_int(values["media_count"]),
            "observed_at": clean_text(values["observed_at"]) or utc_now(),
            "confidence": parse_confidence(values["confidence"]),
            "source": clean_text(values["source"]) or dataset_name,
            "latitude": latitude,
            "longitude": longitude,
            "location_accuracy": clean_text(values["location_accuracy"]),
            "location_source": clean_text(values["location_source"]),
            "raw_json": json.dumps(raw_row, default=str),
        }

    def prepare_phone(
        self, raw_row: dict[str, Any], mapping: dict[str, str], dataset_name: str
    ) -> dict[str, Any]:
        values = self.mapped_row(raw_row, mapping, PHONE_FIELDS)
        return {
            "id": str(uuid4()),
            "phone_number": normalize_phone(values["phone_number"]),
            "valid": parse_bool(values["valid"]),
            "national_format": clean_text(values["national_format"]),
            "country_code": clean_text(values["country_code"]),
            "caller_name": clean_text(values["caller_name"]),
            "caller_type": clean_text(values["caller_type"]),
            "carrier_name": clean_text(values["carrier_name"]),
            "line_type": clean_text(values["line_type"]),
            "location": clean_text(values["location"]),
            "observed_at": clean_text(values["observed_at"]) or utc_now(),
            "confidence": parse_confidence(values["confidence"]),
            "source": clean_text(values["source"]) or dataset_name,
            "raw_json": json.dumps(raw_row, default=str),
        }

    def list_datasets(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM datasets ORDER BY imported_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_dataset(self, dataset_id: str) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM datasets WHERE id = ?", (dataset_id,)
            )
        return cursor.rowcount > 0

    def search_profiles(self, query: str, fuzzy: bool = False) -> list[dict[str, Any]]:
        normalized = normalize_username(query)
        if not normalized:
            return []
        with self.connect() as connection:
            if fuzzy:
                pattern = f"%{normalized}%"
                rows = connection.execute(
                    """
                    SELECT profile_records.*, datasets.name AS dataset_name
                    FROM profile_records
                    JOIN datasets ON datasets.id = profile_records.dataset_id
                    WHERE username_normalized LIKE ?
                       OR LOWER(COALESCE(display_name, '')) LIKE ?
                       OR LOWER(COALESCE(profile_url, '')) LIKE ?
                    ORDER BY confidence DESC, observed_at DESC
                    LIMIT 100
                    """,
                    (pattern, pattern, pattern),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT profile_records.*, datasets.name AS dataset_name
                    FROM profile_records
                    JOIN datasets ON datasets.id = profile_records.dataset_id
                    WHERE username_normalized = ?
                    ORDER BY confidence DESC, observed_at DESC
                    LIMIT 100
                    """,
                    (normalized,),
                ).fetchall()
            records = []
            for row in rows:
                record = self.profile_response(row)
                if row["entity_id"]:
                    record["entity"] = self.entity_summary(connection, row["entity_id"])
                records.append(record)
        return records

    def search_phones(self, phone_number: str) -> list[dict[str, Any]]:
        normalized = normalize_phone(phone_number)
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT phone_records.*, datasets.name AS dataset_name
                FROM phone_records
                JOIN datasets ON datasets.id = phone_records.dataset_id
                WHERE phone_number = ?
                ORDER BY confidence DESC, observed_at DESC
                LIMIT 100
                """,
                (normalized,),
            ).fetchall()
            records = []
            for row in rows:
                record = self.phone_response(row)
                if row["entity_id"]:
                    record["entity"] = self.entity_summary(connection, row["entity_id"])
                records.append(record)
        return records

    def search_geo(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_miles: float,
        query: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        parse_coordinate_pair(latitude, longitude)
        if radius_miles <= 0 or radius_miles > 1000:
            raise ValueError("radius_miles must be greater than 0 and no more than 1000")
        latitude_delta = radius_miles / 69.0
        longitude_scale = max(cos(radians(latitude)), 0.01)
        longitude_delta = radius_miles / (69.172 * longitude_scale)
        normalized_query = query.strip().casefold() if query and query.strip() else None

        with self.connect() as connection:
            entity_rows = connection.execute(
                """
                SELECT entities.*, datasets.name AS dataset_name
                FROM entities
                JOIN datasets ON datasets.id = entities.dataset_id
                WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?
                """,
                (
                    latitude - latitude_delta,
                    latitude + latitude_delta,
                    longitude - longitude_delta,
                    longitude + longitude_delta,
                ),
            ).fetchall()
            profile_rows = connection.execute(
                """
                SELECT profile_records.*, datasets.name AS dataset_name
                FROM profile_records
                JOIN datasets ON datasets.id = profile_records.dataset_id
                WHERE entity_id IS NULL
                  AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?
                """,
                (
                    latitude - latitude_delta,
                    latitude + latitude_delta,
                    longitude - longitude_delta,
                    longitude + longitude_delta,
                ),
            ).fetchall()

            candidates: list[dict[str, Any]] = []
            for row in entity_rows:
                summary = self.entity_summary(connection, row["id"]) or {}
                searchable = " ".join(
                    str(value or "")
                    for value in (row["display_name"], row["bio"], row["location"], row["source"])
                ).casefold()
                if normalized_query and normalized_query not in searchable:
                    continue
                distance = haversine_miles(latitude, longitude, row["latitude"], row["longitude"])
                if distance > radius_miles:
                    continue
                candidates.append(
                    self.geo_feature(
                        feature_id=f"dataset:entity:{row['id']}",
                        latitude=row["latitude"],
                        longitude=row["longitude"],
                        title=row["display_name"] or "Imported entity",
                        text=row["bio"],
                        record_type="entity",
                        row=row,
                        distance=distance,
                        associated_profiles=summary.get("profiles", []),
                        associated_phones=summary.get("phone_numbers", []),
                    )
                )

            for row in profile_rows:
                searchable = " ".join(
                    str(value or "")
                    for value in (row["username"], row["display_name"], row["bio"], row["location"], row["source"])
                ).casefold()
                if normalized_query and normalized_query not in searchable:
                    continue
                distance = haversine_miles(latitude, longitude, row["latitude"], row["longitude"])
                if distance > radius_miles:
                    continue
                candidates.append(
                    self.geo_feature(
                        feature_id=f"dataset:profile:{row['id']}",
                        latitude=row["latitude"],
                        longitude=row["longitude"],
                        title=row["display_name"] or f"@{row['username']}",
                        text=row["bio"],
                        record_type="profile",
                        row=row,
                        distance=distance,
                        associated_profiles=[
                            {
                                "id": row["id"],
                                "platform": row["platform"],
                                "username": row["username"],
                                "profile_uri": row["profile_url"],
                            }
                        ],
                        associated_phones=[],
                    )
                )

        candidates.sort(key=lambda item: item["properties"]["distance_miles"])
        return candidates[:limit]

    @staticmethod
    def geo_feature(
        *,
        feature_id: str,
        latitude: float,
        longitude: float,
        title: str,
        text: str | None,
        record_type: str,
        row: sqlite3.Row,
        distance: float,
        associated_profiles: list[dict[str, Any]],
        associated_phones: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "type": "Feature",
            "id": feature_id,
            "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
            "properties": {
                "source": "datasets",
                "record_type": record_type,
                "title": title,
                "text": text,
                "location_accuracy": row["location_accuracy"] or "unknown",
                "location_source": row["location_source"] or "dataset_import",
                "confidence": row["confidence"],
                "timestamp": row["observed_at"],
                "distance_miles": round(distance, 3),
                "associated_profiles": associated_profiles,
                "associated_phones": associated_phones,
                "provenance": {
                    "provider": "platform_dataset",
                    "dataset_id": row["dataset_id"],
                    "dataset_name": row["dataset_name"],
                    "record_id": row["id"],
                    "record_source": row["source"],
                },
            },
        }

    def dataset_records(
        self, dataset_id: str, limit: int, offset: int
    ) -> tuple[str, list[dict[str, Any]]] | None:
        with self.connect() as connection:
            dataset = connection.execute(
                "SELECT record_type FROM datasets WHERE id = ?", (dataset_id,)
            ).fetchone()
            if not dataset:
                return None
            if dataset["record_type"] == "entity":
                rows = connection.execute(
                    "SELECT * FROM entities WHERE dataset_id = ? LIMIT ? OFFSET ?",
                    (dataset_id, limit, offset),
                ).fetchall()
                return "entity", [
                    self.entity_response(connection, row) for row in rows
                ]
            table = "profile_records" if dataset["record_type"] == "profile" else "phone_records"
            rows = connection.execute(
                f"SELECT * FROM {table} WHERE dataset_id = ? LIMIT ? OFFSET ?",
                (dataset_id, limit, offset),
            ).fetchall()
            records = []
            for row in rows:
                record = (
                    self.profile_response(row)
                    if dataset["record_type"] == "profile"
                    else self.phone_response(row)
                )
                if row["entity_id"]:
                    record["entity"] = self.entity_summary(connection, row["entity_id"])
                records.append(record)
        return dataset["record_type"], records

    def entity_summary(
        self, connection: sqlite3.Connection, entity_id: str
    ) -> dict[str, Any] | None:
        entity = connection.execute(
            "SELECT * FROM entities WHERE id = ?", (entity_id,)
        ).fetchone()
        if not entity:
            return None
        profiles = connection.execute(
            """
            SELECT id, platform, username, profile_url
            FROM profile_records
            WHERE entity_id = ?
            ORDER BY platform, username
            """,
            (entity_id,),
        ).fetchall()
        phones = connection.execute(
            """
            SELECT id, phone_number, caller_name, carrier_name, line_type
            FROM phone_records
            WHERE entity_id = ?
            ORDER BY phone_number
            """,
            (entity_id,),
        ).fetchall()
        return {
            "id": entity["id"],
            "name": entity["display_name"],
            "bio": entity["bio"],
            "location": entity["location"],
            "website": entity["website"],
            "latitude": entity["latitude"],
            "longitude": entity["longitude"],
            "location_accuracy": entity["location_accuracy"],
            "location_source": entity["location_source"],
            "profiles": [
                {
                    "id": row["id"],
                    "platform": row["platform"],
                    "username": row["username"],
                    "profile_uri": row["profile_url"],
                }
                for row in profiles
            ],
            "phone_numbers": [
                {
                    "id": row["id"],
                    "phone_number": row["phone_number"],
                    "caller_name": row["caller_name"],
                    "carrier_name": row["carrier_name"],
                    "line_type": row["line_type"],
                }
                for row in phones
            ],
        }

    def entity_response(
        self, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> dict[str, Any]:
        summary = self.entity_summary(connection, row["id"]) or {}
        return {
            **summary,
            "record_type": "entity",
            "source_type": "dataset",
            "dataset_id": row["dataset_id"],
            "source": row["source"],
            "observed_at": row["observed_at"],
            "confidence": row["confidence"],
            "raw": json.loads(row["raw_json"]),
        }

    @staticmethod
    def profile_response(row: sqlite3.Row) -> dict[str, Any]:
        metrics = {
            key: row[key]
            for key in (
                "followers_count",
                "following_count",
                "post_count",
                "listed_count",
                "like_count",
                "media_count",
            )
            if row[key] is not None
        }
        return {
            "id": row["id"],
            "record_type": "profile",
            "source_type": "dataset",
            "dataset_id": row["dataset_id"],
            "dataset_name": row["dataset_name"] if "dataset_name" in row.keys() else None,
            "source": row["source"],
            "observed_at": row["observed_at"],
            "confidence": row["confidence"],
            "platform": row["platform"],
            "username": row["username"],
            "profile_uri": row["profile_url"],
            "name": row["display_name"],
            "bio": row["bio"],
            "location": row["location"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "location_accuracy": row["location_accuracy"],
            "location_source": row["location_source"],
            "website": row["website"],
            "verified": (
                bool(row["verified"]) if row["verified"] is not None else None
            ),
            "protected": (
                bool(row["protected"]) if row["protected"] is not None else None
            ),
            "created_at": row["created_at"],
            "profile_image_url": row["profile_image_url"],
            "profile_banner_url": row["profile_banner_url"],
            "metrics": metrics,
            "raw": json.loads(row["raw_json"]),
        }

    @staticmethod
    def phone_response(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "record_type": "phone",
            "source_type": "dataset",
            "dataset_id": row["dataset_id"],
            "dataset_name": row["dataset_name"] if "dataset_name" in row.keys() else None,
            "source": row["source"],
            "observed_at": row["observed_at"],
            "confidence": row["confidence"],
            "phone_number": row["phone_number"],
            "valid": bool(row["valid"]) if row["valid"] is not None else None,
            "national_format": row["national_format"],
            "country_code": row["country_code"],
            "caller_name": row["caller_name"],
            "caller_type": row["caller_type"],
            "carrier_name": row["carrier_name"],
            "line_type": row["line_type"],
            "location": row["location"],
            "raw": json.loads(row["raw_json"]),
        }
