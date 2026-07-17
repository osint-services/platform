# Dataset service

The dataset service provides normalized, persistent local sources for the platform's profile and phone searches. It uses SQLite and has no external provider dependency.

## Supported input

The Electron UI parses `.csv`, `.json`, `.jsonl`, and `.ndjson` files, then maps source columns to the canonical fields returned by:

```http
GET /datasets/schema/profile
GET /datasets/schema/phone
```

Profile records require either a username or profile URL. Phone records require an E.164 number such as `+18135551212`. Invalid booleans, negative metrics, confidence outside `0..1`, and malformed identifiers are rejected per row without discarding valid rows.

Each accepted record includes:

- its dataset and source;
- an observation timestamp;
- optional confidence;
- normalized searchable identifiers; and
- the complete original source row for audit.

## Storage and limits

Compose stores `/data/datasets.db` in the named `dataset_data` volume. Deleting a dataset cascades to its records. Each import accepts 1–10,000 JSON object rows; the desktop UI additionally enforces a 10 MB file limit.

The API is intentionally local and currently has no authentication layer. Do not expose the nginx proxy to an untrusted network without adding access control.

## Development

```bash
uvicorn dataset_service.server:app --reload --port 8000
.venv/bin/pytest -q tests/test_dataset_service.py
```
