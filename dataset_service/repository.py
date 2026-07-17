import json
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
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    record_type TEXT NOT NULL CHECK(record_type IN ('profile', 'phone')),
                    filename TEXT,
                    imported_at TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    rejected_count INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS profile_records (
                    id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
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
                    raw_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS phone_records (
                    id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
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

                CREATE INDEX IF NOT EXISTS idx_profile_username
                    ON profile_records(username_normalized);
                CREATE INDEX IF NOT EXISTS idx_profile_display_name
                    ON profile_records(display_name);
                CREATE INDEX IF NOT EXISTS idx_phone_number
                    ON phone_records(phone_number);
                """
            )

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
        accepted: list[dict[str, Any]] = []
        rejected: list[RejectedRow] = []

        for row_number, raw_row in enumerate(request.rows, start=1):
            try:
                if request.record_type.value == "profile":
                    accepted.append(
                        self.prepare_profile(raw_row, request.mapping, request.name)
                    )
                else:
                    accepted.append(
                        self.prepare_phone(raw_row, request.mapping, request.name)
                    )
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
                    len(accepted),
                    len(rejected),
                ),
            )

            if request.record_type.value == "profile":
                connection.executemany(
                    """
                    INSERT INTO profile_records (
                        id, dataset_id, platform, username, username_normalized,
                        profile_url, display_name, bio, location, website, verified,
                        protected, created_at, profile_image_url, profile_banner_url,
                        followers_count, following_count, post_count, listed_count,
                        like_count, media_count, observed_at, confidence, source, raw_json
                    ) VALUES (
                        :id, :dataset_id, :platform, :username, :username_normalized,
                        :profile_url, :display_name, :bio, :location, :website, :verified,
                        :protected, :created_at, :profile_image_url, :profile_banner_url,
                        :followers_count, :following_count, :post_count, :listed_count,
                        :like_count, :media_count, :observed_at, :confidence, :source, :raw_json
                    )
                    """,
                    [dict(record, dataset_id=dataset_id) for record in accepted],
                )
            else:
                connection.executemany(
                    """
                    INSERT INTO phone_records (
                        id, dataset_id, phone_number, valid, national_format,
                        country_code, caller_name, caller_type, carrier_name,
                        line_type, location, observed_at, confidence, source, raw_json
                    ) VALUES (
                        :id, :dataset_id, :phone_number, :valid, :national_format,
                        :country_code, :caller_name, :caller_type, :carrier_name,
                        :line_type, :location, :observed_at, :confidence, :source, :raw_json
                    )
                    """,
                    [dict(record, dataset_id=dataset_id) for record in accepted],
                )

        return DatasetImportResult(
            dataset_id=dataset_id,
            imported=len(accepted),
            rejected=len(rejected),
            rejected_rows=rejected[:100],
        )

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
        return [self.profile_response(row) for row in rows]

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
        return [self.phone_response(row) for row in rows]

    def dataset_records(
        self, dataset_id: str, limit: int, offset: int
    ) -> tuple[str, list[dict[str, Any]]] | None:
        with self.connect() as connection:
            dataset = connection.execute(
                "SELECT record_type FROM datasets WHERE id = ?", (dataset_id,)
            ).fetchone()
            if not dataset:
                return None
            table = (
                "profile_records"
                if dataset["record_type"] == "profile"
                else "phone_records"
            )
            rows = connection.execute(
                f"SELECT * FROM {table} WHERE dataset_id = ? LIMIT ? OFFSET ?",
                (dataset_id, limit, offset),
            ).fetchall()
        return dataset["record_type"], [
            self.profile_response(row)
            if dataset["record_type"] == "profile"
            else self.phone_response(row)
            for row in rows
        ]

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
