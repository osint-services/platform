import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    DatasetImportRequest,
    DatasetImportResult,
    DatasetSchema,
    DatasetSummary,
    FieldDefinition,
    RecordType,
)
from .repository import DatasetRepository


PROFILE_SCHEMA = DatasetSchema(
    record_type=RecordType.profile,
    fields=[
        FieldDefinition(key="username", label="Username", required=True, description="Account handle, with or without @. A profile URL can be used instead."),
        FieldDefinition(key="platform", label="Platform", description="Network or site name, for example X or GitHub."),
        FieldDefinition(key="profile_url", label="Profile URL", description="Canonical public profile URL."),
        FieldDefinition(key="display_name", label="Display name", description="Human-readable account name."),
        FieldDefinition(key="bio", label="Bio", description="Public profile description."),
        FieldDefinition(key="location", label="Location", description="Public or source-provided location."),
        FieldDefinition(key="website", label="Website", description="Website associated with the account."),
        FieldDefinition(key="verified", label="Verified", description="Boolean verification status."),
        FieldDefinition(key="protected", label="Protected", description="Boolean protected/private status."),
        FieldDefinition(key="created_at", label="Created at", description="Account creation timestamp."),
        FieldDefinition(key="profile_image_url", label="Profile image URL", description="Avatar URL."),
        FieldDefinition(key="profile_banner_url", label="Profile banner URL", description="Header/banner image URL."),
        FieldDefinition(key="followers_count", label="Followers", description="Follower count."),
        FieldDefinition(key="following_count", label="Following", description="Following count."),
        FieldDefinition(key="post_count", label="Posts", description="Post or status count."),
        FieldDefinition(key="listed_count", label="Listed", description="List membership count."),
        FieldDefinition(key="like_count", label="Likes", description="Like or favorite count."),
        FieldDefinition(key="media_count", label="Media", description="Media post count."),
        FieldDefinition(key="observed_at", label="Observed at", description="Timestamp when the source observed this record."),
        FieldDefinition(key="confidence", label="Confidence", description="Optional confidence score from 0 to 1."),
        FieldDefinition(key="source", label="Source", description="Original source name or URL."),
    ],
    sample={
        "username": "example",
        "platform": "X",
        "profile_url": "https://x.com/example",
        "display_name": "Example Person",
        "verified": False,
        "followers_count": 1250,
        "observed_at": "2026-07-17T12:00:00Z",
        "confidence": 0.9,
        "source": "Public research export",
    },
)

PHONE_SCHEMA = DatasetSchema(
    record_type=RecordType.phone,
    fields=[
        FieldDefinition(key="phone_number", label="Phone number", required=True, description="Number in E.164 format, for example +18135551212."),
        FieldDefinition(key="valid", label="Valid", description="Boolean validity status."),
        FieldDefinition(key="national_format", label="National format", description="Locally formatted phone number."),
        FieldDefinition(key="country_code", label="Country code", description="ISO country code."),
        FieldDefinition(key="caller_name", label="Caller name", description="Person or business caller name."),
        FieldDefinition(key="caller_type", label="Caller type", description="Caller-name classification."),
        FieldDefinition(key="carrier_name", label="Carrier", description="Network carrier name."),
        FieldDefinition(key="line_type", label="Line type", description="Mobile, landline, VoIP, or other classification."),
        FieldDefinition(key="location", label="Location", description="Source-provided phone location."),
        FieldDefinition(key="observed_at", label="Observed at", description="Timestamp when the source observed this record."),
        FieldDefinition(key="confidence", label="Confidence", description="Optional confidence score from 0 to 1."),
        FieldDefinition(key="source", label="Source", description="Original source name or URL."),
    ],
    sample={
        "phone_number": "+18135551212",
        "valid": True,
        "national_format": "(813) 555-1212",
        "country_code": "US",
        "caller_name": "Example Business",
        "line_type": "landline",
        "observed_at": "2026-07-17T12:00:00Z",
        "confidence": 0.85,
        "source": "Licensed directory",
    },
)

ENTITY_SCHEMA = DatasetSchema(
    record_type=RecordType.entity,
    identifier_fields=["username", "profile_url", "phone_number"],
    fields=[
        FieldDefinition(key="username", label="Username", description="Account handle, with or without @."),
        FieldDefinition(key="platform", label="Platform", description="Network or site name, for example X or GitHub."),
        FieldDefinition(key="profile_url", label="Profile URL", description="Canonical public profile URL; can identify a profile when username is absent."),
        FieldDefinition(key="phone_number", label="Phone number", description="Number in E.164 format, for example +12025550101."),
        FieldDefinition(key="display_name", label="Display name", description="Person, organization, or account name."),
        FieldDefinition(key="bio", label="Bio", description="Source-provided identity or profile description."),
        FieldDefinition(key="location", label="Location", description="Public or source-provided location."),
        FieldDefinition(key="website", label="Website", description="Website associated with the entity or profile."),
        FieldDefinition(key="verified", label="Verified", description="Boolean profile verification status."),
        FieldDefinition(key="protected", label="Protected", description="Boolean protected/private profile status."),
        FieldDefinition(key="created_at", label="Profile created at", description="Account creation timestamp."),
        FieldDefinition(key="profile_image_url", label="Profile image URL", description="Avatar URL."),
        FieldDefinition(key="profile_banner_url", label="Profile banner URL", description="Header/banner image URL."),
        FieldDefinition(key="followers_count", label="Followers", description="Follower count."),
        FieldDefinition(key="following_count", label="Following", description="Following count."),
        FieldDefinition(key="post_count", label="Posts", description="Post or status count."),
        FieldDefinition(key="listed_count", label="Listed", description="List membership count."),
        FieldDefinition(key="like_count", label="Likes", description="Like or favorite count."),
        FieldDefinition(key="media_count", label="Media", description="Media post count."),
        FieldDefinition(key="valid", label="Phone valid", description="Boolean phone validity status."),
        FieldDefinition(key="national_format", label="National phone format", description="Locally formatted phone number."),
        FieldDefinition(key="country_code", label="Country code", description="ISO country code."),
        FieldDefinition(key="caller_name", label="Caller name", description="Person or business caller name; used as the entity name when display name is absent."),
        FieldDefinition(key="caller_type", label="Caller type", description="Caller-name classification."),
        FieldDefinition(key="carrier_name", label="Carrier", description="Network carrier name."),
        FieldDefinition(key="line_type", label="Line type", description="Mobile, landline, VoIP, or other classification."),
        FieldDefinition(key="observed_at", label="Observed at", description="Timestamp when the source observed this record."),
        FieldDefinition(key="confidence", label="Confidence", description="Optional confidence score from 0 to 1."),
        FieldDefinition(key="source", label="Source", description="Original source name or URL."),
    ],
    sample={
        "username": "demo_ada_1843",
        "platform": "Example Network",
        "profile_url": "https://profiles.example/demo_ada_1843",
        "phone_number": "+12025550101",
        "display_name": "Ada Example",
        "carrier_name": "Example Wireless",
        "line_type": "mobile",
        "observed_at": "2026-07-17T12:00:00Z",
        "confidence": 0.9,
        "source": "Fictional research export",
    },
)


def create_app(database_path: str | Path | None = None) -> FastAPI:
    fallback = Path(tempfile.gettempdir()) / "whoisit-datasets.db"
    path = database_path or os.getenv("DATASET_DB_PATH", str(fallback))
    repository = DatasetRepository(path)
    app = FastAPI(title="OSINT Dataset Service")
    app.state.repository = repository

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/datasets/schema/{record_type}", response_model=DatasetSchema)
    def dataset_schema(record_type: RecordType) -> DatasetSchema:
        if record_type is RecordType.entity:
            return ENTITY_SCHEMA
        return PROFILE_SCHEMA if record_type is RecordType.profile else PHONE_SCHEMA

    @app.post(
        "/datasets/import",
        response_model=DatasetImportResult,
        status_code=status.HTTP_201_CREATED,
    )
    def import_dataset(request: DatasetImportRequest) -> DatasetImportResult:
        return repository.import_dataset(request)

    @app.get("/datasets", response_model=list[DatasetSummary])
    def list_datasets() -> list[dict]:
        return repository.list_datasets()

    @app.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_dataset(dataset_id: str) -> Response:
        if not repository.delete_dataset(dataset_id):
            raise HTTPException(status_code=404, detail="Dataset not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/datasets/{dataset_id}/records")
    def dataset_records(
        dataset_id: str,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> dict:
        result = repository.dataset_records(dataset_id, limit, offset)
        if result is None:
            raise HTTPException(status_code=404, detail="Dataset not found")
        record_type, records = result
        return {
            "dataset_id": dataset_id,
            "record_type": record_type,
            "records": records,
            "limit": limit,
            "offset": offset,
        }

    @app.get("/datasets/search/profiles")
    def search_profiles(
        query: str = Query(min_length=1),
        fuzzy: bool = False,
    ) -> dict:
        return {
            "query": query,
            "records": repository.search_profiles(query, fuzzy=fuzzy),
        }

    @app.get("/datasets/search/phones")
    def search_phones(phone_number: str = Query(min_length=1)) -> dict:
        try:
            records = repository.search_phones(phone_number)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"query": phone_number, "records": records}

    return app


app = create_app()
