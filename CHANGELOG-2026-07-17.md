# Changelog for 2026-07-17

## Added

- Sparse entities that can contain a profile identifier, a phone identifier, or both, with associations visible from either search.
- Persistent SQLite-backed profile and phone datasets with mapped imports and local search.
- CSV, JSON, JSONL, and NDJSON parsing with automatic field suggestions and previews.
- Per-row validation, rejected-row reporting, provenance, observation time, confidence, and raw source retention.
- Search history and combined live/local results in the Electron application.
- Integration status and credential management for X/Tweepy and Twilio Lookup.
- Rich username result cards that remain informative when paid X profile inspection is unavailable.
- Fictional sample profile and phone files for testing the dataset workflow without real personal data.
- Backend and renderer parser regression tests.

## Changed

- Replaced the desktop record-type selector with one entity ingestion and field-mapping pipeline.
- Added an in-place SQLite schema migration while retaining legacy profile and phone import compatibility.
- Unified username and phone lookup into a Search workspace with Auto, Profile, and Phone modes plus source filters that avoid unnecessary provider calls.
- Reorganized the desktop application into Search, Datasets, Integrations, and History workspaces.
- Expanded profile and caller details and made source provenance visible throughout the UI.
- Kept API failures scoped to their own source and search workflow.
- Added dataset routing, persistence, and readiness checks to the deployed architecture.
- Restricted saved provider credentials to the operating-system user and prevented existing secrets from being returned to the UI.
- Fixed platform-root discovery in packaged Electron layouts so integration settings use the correct `.env` file.
- Mapped X API failures to explicit profile-inspection responses, including `402` for depleted credits and `429` for rate limits.
- Made nginx resolve Compose service names at request time, preventing cross-service 404s after containers receive new IP addresses.

## Documentation

- Rewrote the root architecture and setup guide.
- Expanded environment-variable guidance.
- Rewrote the desktop UI guide and added a dataset service guide.
- Updated the OSINT Services organization profile README.
