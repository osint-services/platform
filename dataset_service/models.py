from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RecordType(str, Enum):
    profile = "profile"
    phone = "phone"


class DatasetImportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    record_type: RecordType
    filename: str | None = Field(default=None, max_length=255)
    mapping: dict[str, str] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(min_items=1, max_items=10_000)


class RejectedRow(BaseModel):
    row_number: int
    reason: str


class DatasetImportResult(BaseModel):
    dataset_id: str
    imported: int
    rejected: int
    rejected_rows: list[RejectedRow]


class DatasetSummary(BaseModel):
    id: str
    name: str
    record_type: RecordType
    filename: str | None
    imported_at: str
    row_count: int
    rejected_count: int


class FieldDefinition(BaseModel):
    key: str
    label: str
    required: bool = False
    description: str


class DatasetSchema(BaseModel):
    record_type: RecordType
    fields: list[FieldDefinition]
    sample: dict[str, Any]
