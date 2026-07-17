# Changelog for 2026-07-17

## Added

- Persistent SQLite-backed profile and phone datasets with mapped imports and local search.
- CSV, JSON, JSONL, and NDJSON parsing with automatic field suggestions and previews.
- Per-row validation, rejected-row reporting, provenance, observation time, confidence, and raw source retention.
- Search history and combined live/local results in the Electron application.
- Integration status and credential management for X/Tweepy and Twilio Lookup.
- Backend and renderer parser regression tests.

## Changed

- Reorganized the desktop application into Username, Phone, Datasets, and History workspaces.
- Expanded profile and caller details and made source provenance visible throughout the UI.
- Kept API failures scoped to their own source and search workflow.
- Added dataset routing, persistence, and readiness checks to the deployed architecture.
- Restricted saved provider credentials to the operating-system user and prevented existing secrets from being returned to the UI.
- Fixed platform-root discovery in packaged Electron layouts so integration settings use the correct `.env` file.
- Mapped X API failures to explicit profile-inspection responses, including `402` for depleted credits and `429` for rate limits.

## Documentation

- Rewrote the root architecture and setup guide.
- Expanded environment-variable guidance.
- Rewrote the desktop UI guide and added a dataset service guide.
- Updated the OSINT Services organization profile README.
