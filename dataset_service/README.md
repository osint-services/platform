# Dataset service

The dataset service stores normalized identity evidence for profile, phone, and geospatial searches. It uses SQLite and has no external provider dependency.

## Imports and coordinates

The desktop UI parses CSV, JSON, JSONL, and NDJSON and maps rows through `GET /datasets/schema/entity`. Each sparse entity needs a username, profile URL, or E.164 phone number. Optional explicit geospatial fields are:

- `latitude` and `longitude`, supplied together and within valid ranges;
- `location_accuracy`, such as `exact`, `place`, or `approximate`; and
- `location_source`, describing where the coordinate evidence came from.

Free-text `location` remains descriptive text. The service never geocodes it. Existing databases receive these nullable columns through an additive startup migration.

Associated profile and phone identifiers remain attached to the entity. Phone information may be returned as marker metadata, but a phone row never creates or implies a device location.

## Geospatial search

```http
GET /datasets/search/geo?latitude=51.5074&longitude=-0.1278&radius_miles=5&query=demo&limit=100
```

The route returns a GeoJSON `FeatureCollection` containing radius-filtered entity and standalone profile records with source, accuracy, confidence, timestamp, distance, provenance, and associated identifiers.

## Storage and limits

Compose stores `/data/datasets.db` in `dataset_data`. Deleting a dataset cascades to its entities and typed identifiers. Imports accept 1 to 10,000 JSON object rows; the desktop UI also limits files to 10 MB. The API is local and has no authentication layer, so do not expose nginx to an untrusted network without access control.

## Sample data

- [`geospatial_entities.csv`](../examples/datasets/geospatial_entities.csv): synthetic London, Arlington, and Portland entities with explicit coordinates and reserved fictional phone numbers.
- [`sample_entities.csv`](../examples/datasets/sample_entities.csv): combined identities.
- [`sample_profiles.csv`](../examples/datasets/sample_profiles.csv): profile compatibility import.
- [`sample_phone_records.jsonl`](../examples/datasets/sample_phone_records.jsonl): phone compatibility import.

```bash
python3 scripts/import_geospatial_demo.py
```

## Development

```bash
uvicorn dataset_service.server:app --reload --port 8000
.venv/bin/pytest -q tests/test_dataset_service.py
```
