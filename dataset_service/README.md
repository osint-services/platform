# Dataset service

The dataset service provides normalized, persistent identity sources for the platform's profile and phone searches. It uses SQLite and has no external provider dependency.

## Supported input

The Electron UI parses `.csv`, `.json`, `.jsonl`, and `.ndjson` files, then maps every import through the entity schema returned by:

```http
GET /datasets/schema/entity
```

Each sparse entity row requires at least one searchable identifier: a username, profile URL, or E.164 phone number such as `+12025550101`. All other fields are optional. When both profile and phone fields exist, the service stores typed identifiers under one entity so a match for either identifier exposes the association. Invalid booleans, negative metrics, confidence outside `0..1`, and malformed identifiers are rejected per row without discarding valid rows.

The legacy `profile` and `phone` schemas and import values remain accepted for API compatibility, but the desktop application uses only the entity pipeline. Existing SQLite databases are migrated in place when the service starts.

Each accepted entity includes:

- its dataset and source;
- an observation timestamp;
- optional confidence;
- normalized searchable identifiers; and
- the complete original source row for audit.

## Storage and limits

Compose stores `/data/datasets.db` in the named `dataset_data` volume. Deleting a dataset cascades to its entities and typed identifiers. Each import accepts 1–10,000 JSON object rows; the desktop UI additionally enforces a 10 MB file limit.

The API is intentionally local and currently has no authentication layer. Do not expose the nginx proxy to an untrusted network without adding access control.

## Sample data

The platform repository includes a combined fictional entity dataset plus separate fixtures for exercising compatibility and source-specific fields:

- [`examples/datasets/sample_entities.csv`](../examples/datasets/sample_entities.csv)
- [`examples/datasets/sample_profiles.csv`](../examples/datasets/sample_profiles.csv)
- [`examples/datasets/sample_phone_records.jsonl`](../examples/datasets/sample_phone_records.jsonl)

Import any of them from the same desktop Datasets workflow; canonical headers are auto-mapped. The combined file demonstrates a username and phone on one entity, a profile-only entity, and a phone-only entity. Search for `demo_ada_1843` or `+12025550101` to see the association in both directions. The phone values use the reserved North American `555-01xx` fictional range and do not identify real subscribers.

## Development

```bash
uvicorn dataset_service.server:app --reload --port 8000
.venv/bin/pytest -q tests/test_dataset_service.py
```
