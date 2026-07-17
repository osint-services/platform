# OSINT Services Platform

The platform combines live public-data APIs with user-supplied datasets behind one nginx endpoint and one Electron investigation workspace.

## Architecture

```text
whoisit desktop app
        |
        v
nginx :80
  |-- /scan/*          -> profile_checker  (public username availability)
  |-- /focus*          -> profile_search   (X profile metadata via Tweepy)
  |-- /phone_search*   -> phone_search     (caller-name data via Twilio)
  `-- /datasets*       -> dataset_service  (SQLite imports and local search)
```

Docker Compose runs the four FastAPI services, nginx, and a persistent `dataset_data` volume. The Electron UI queries live and local sources independently and combines successful results, so one unavailable provider does not prevent other sources from being searched.

## Requirements

- Docker with `docker compose`
- Node.js 18 or newer to build or run the Electron UI
- An X API bearer token for profile inspection
- Twilio Account SID and Auth Token for live phone lookup

## Setup

```bash
git submodule update --init --recursive
cp .env.example .env
```

Add your provider credentials to `.env`, then start the API stack:

```bash
./scripts/start.sh
```

Run the desktop UI from a second terminal:

```bash
cd whoisit
npm install
npm start
```

The UI checks service readiness on launch and can attempt to start the Compose stack when Docker is available. Packaged builds are created with `npm run package`.

## Environment values

| Variable | Required | Used by | Meaning |
| --- | --- | --- | --- |
| `TWEEPY_BEARER_TOKEN` | For live profile inspection | `profile_search` | X API v2 application bearer token. Despite the variable name, the credential is issued by X; Tweepy is the Python client. |
| `TWILIO_ACCOUNT_SID` | For live phone lookup | `phone_search` | Twilio account identifier, normally beginning with `AC`. |
| `TWILIO_AUTH_TOKEN` | For live phone lookup | `phone_search` | Secret used with the Account SID to authenticate Twilio API calls. |
| `DATASET_DB_PATH` | No | `dataset_service` | SQLite file location. Compose sets this to `/data/datasets.db` inside its persistent volume. |

Do not commit `.env`. Imported datasets may contain sensitive or licensed information; only import data you are authorized to retain and use.

## API routes

| Route | Purpose |
| --- | --- |
| `GET /scan/{username}` | Check supported sites for a public username |
| `GET /focus?url=https://x.com/{username}` | Retrieve expanded X profile metadata |
| `GET /phone_search?phone_number=+18135551212` | Retrieve live caller-name metadata |
| `GET /datasets` | List imported datasets |
| `GET /datasets/schema/{profile\|phone}` | Get canonical import fields and a sample |
| `POST /datasets/import` | Import mapped profile or phone rows |
| `GET /datasets/search/profiles?query=...&fuzzy=true` | Search imported profiles |
| `GET /datasets/search/phones?phone_number=...` | Search imported phone records |
| `DELETE /datasets/{dataset_id}` | Delete a dataset and its records |

The import API accepts JSON rows after the UI parses CSV, JSON, JSONL, or NDJSON. A single import is limited to 10,000 records and the UI limits files to 10 MB. Canonical records preserve their source row, dataset provenance, observation time, and optional confidence score. Phone search uses normalized E.164 values; profile search supports exact or fuzzy matching.

## Operations and tests

```bash
./scripts/build.sh      # rebuild images
./scripts/logs.sh       # stream Compose logs
./scripts/stop.sh       # stop the stack
.venv/bin/pytest -q     # backend tests
cd whoisit && npm test  # importer parser tests
```

Liveness endpoints are available at `/scan/healthz`, `/phone_search/healthz`, and `/datasets/healthz`. Profile inspection also exposes `/focus/readyz`, which verifies that its X credential is configured.

## Documentation

- [Desktop UI guide](whoisit/README.md)
- [Dataset service guide](dataset_service/README.md)
- [Changelog](CHANGELOG.md)
- [2026-07-17 release notes](CHANGELOG-2026-07-17.md)
