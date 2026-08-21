# OSINT Services Platform

The platform combines public-data services, user-supplied datasets, and evidence-oriented mapping behind one nginx endpoint and the [`whoisit`](https://github.com/osint-services/whoisit) desktop workspace.

## Architecture

```text
whoisit desktop app and standalone Social Mapping client
                            |
                            v
                         nginx :80
  |-- /scan/*          -> profile_checker  (public username availability)
  |-- /focus*          -> profile_search   (X profile metadata)
  |-- /phone_search*   -> phone_search     (caller-name data)
  |-- /datasets*       -> dataset_service  (SQLite imports and geo search)
  `-- /map/*           -> social_mapping   (GeoJSON aggregation, X posts, origin geocoding)
```

Docker Compose runs the five FastAPI services, nginx, a persistent `dataset_data` volume, and a separate durable `social_mapping_cache` volume. The map service queries datasets internally and can use the same X bearer-token configuration as profile search. `whoisit` calls `/map/search` natively; it does not embed the standalone client.

## Requirements and setup

- Docker with Compose v2
- Node.js 22 or newer to build the current desktop UI
- Optional X bearer token for profile inspection and X map posts
- Optional Twilio credentials for live phone lookup

```bash
git submodule update --init --recursive
cp .env.example .env
./scripts/start.sh
```

Run the desktop UI from another terminal:

```bash
cd whoisit
npm install
npm start
```

The imported-dataset map works without live credentials. Load the synthetic fixture and verify London end to end:

```bash
python3 scripts/import_geospatial_demo.py
python3 scripts/test_social_mapping_e2e.py
```

## Environment values

| Variable | Required | Used by | Meaning |
| --- | --- | --- | --- |
| `TWEEPY_BEARER_TOKEN` | No | `profile_search`, `social_mapping` | X API v2 bearer token; map searches degrade to datasets when absent |
| `TWILIO_ACCOUNT_SID` | No | `phone_search` | Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | No | `phone_search` | Twilio API secret |
| `DATASET_DB_PATH` | No | `dataset_service` | Compose uses `/data/datasets.db` in persistent storage |
| `NOMINATIM_BASE_URL` | No | `social_mapping` | Server-side search-origin geocoder |
| `NOMINATIM_USER_AGENT` | Recommended | `social_mapping` | Identifying User-Agent and contact/project URL |
| `GEOCODER_CACHE_DAYS` | No | `social_mapping` | Durable normalized place-cache refresh interval; default 30 |
| `GEOCODER_MIN_INTERVAL_SECONDS` | No | `social_mapping` | Process-wide Nominatim request spacing; default 1 |

Do not commit `.env`. Imported datasets may contain sensitive or licensed information; import only data you are authorized to retain and use.

## API routes

| Route | Purpose |
| --- | --- |
| `GET /scan/{username}` | Check supported sites for a public username |
| `GET /focus?url=https://x.com/{username}` | Retrieve expanded X profile metadata |
| `GET /phone_search?phone_number=...` | Retrieve live caller-name metadata |
| `GET /datasets` | List imported datasets |
| `POST /datasets/import` | Import sparse entities, profiles, or phone records |
| `GET /datasets/search/geo` | Radius-search only records with explicit coordinate pairs |
| `GET /map/search` | Return combined GeoJSON for a place or coordinate origin |
| `GET /map/healthz` | Map process liveness |
| `GET /map/readyz` | Map cache and configuration readiness |

Dataset imports accept nullable `latitude`, `longitude`, `location_accuracy`, and `location_source` fields. Latitude and longitude must be supplied as a valid pair. The migration is additive for existing SQLite databases. Free-text record locations are not geocoded into evidence coordinates. Associated phone records can appear in marker details but never produce or imply phone/device locations.

`/search/tweets?city=&distance=` remains a deprecated compatibility alias until the next major Social Mapping release.

## Operations and tests

```bash
./scripts/build.sh
./scripts/logs.sh
./scripts/stop.sh
.venv/bin/pytest -q tests
docker compose config --quiet
```

CI mocks external X and Nominatim behavior, runs platform tests, validates Compose, and starts the dataset/map/proxy path for a credential-free synthetic London test. Live X testing is optional and deliberately separate so routine CI never spends X credits.

## Documentation

- [Social Mapping](social_mapping/README.md)
- [Desktop UI guide](whoisit/README.md)
- [Dataset service guide](dataset_service/README.md)
- [Synthetic geospatial fixture](examples/datasets/geospatial_entities.csv)
- [Changelog](CHANGELOG.md)
