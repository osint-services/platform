# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Required Docker Engine 28 or newer for desktop-managed and source-script startup, with support for Compose v2 and v5.
- Allowed dataset import requests up to 16 MiB and restored query parameters on the deprecated map route.
- Updated the Python base image and backend dependencies.
- Ran installer checks on gateway, dependency, and packaging changes and exercised both supported Compose versions.

## [1.2.0]

- Added a single Debian/Ubuntu amd64 installer for Whoisit and the platform backend.
- Started the bundled Compose stack from Whoisit and showed service readiness in the desktop UI.
- Kept desktop settings per user and reused the platform dataset and geocoder volumes during upgrades.
- Kept the phone service available when Twilio credentials are unset.

## [1.1.0]

### Added
- Added passive certificate inventory for configured domains with persistent snapshots and a desktop Certificates workspace.
- Integrated `social_mapping` as a pinned submodule and Compose service with `/map/*` nginx routing, readiness checks, and persistent geocoder cache storage.
- Added explicit geospatial dataset fields, additive migration, radius search, GeoJSON provenance, and associated phone metadata.
- Added synthetic London, Arlington, and Portland entities plus credential-free import and end-to-end helper scripts.
- Added a platform CI path that validates tests, Compose configuration, and the complete synthetic London map flow.
- Added search-result **Go to map** handoffs for records with explicit coordinates, including safe phone-to-associated-entity navigation.

### Changed
- Bound the default desktop gateway to IPv4 loopback.
- Routed the native whoisit Map workspace and standalone Social Mapping client through the same canonical `/map/search` API.
- Coordinate handoffs now bypass text geocoding, center the Map workspace on the evidence, and select the matching record when available.
- Switched public submodule URLs to HTTPS so recursive clones do not require organization SSH keys.

## 2026-07-17

### Added

- Sparse entities that can contain a profile identifier, a phone identifier, or both, with associations visible from either search.
- Persistent SQLite-backed profile and phone datasets with mapped imports and local search.
- CSV, JSON, JSONL, and NDJSON parsing with automatic field suggestions and previews.
- Per-row validation, rejected-row reporting, provenance, observation time, confidence, and raw source retention.
- Search history and combined live/local results in the Electron application.
- Integration status and credential management for X/Tweepy and Twilio Lookup.
- Rich username result cards that remain informative when paid X profile inspection is unavailable.
- Fictional sample profile and phone files for testing the dataset workflow without real personal data.
- Regression coverage for dataset imports and deletion, fuzzy profile and normalized phone search, health endpoints, and renderer parsers.

### Changed

- Replaced the desktop record-type selector with one entity ingestion and field-mapping pipeline.
- Added an in-place SQLite schema migration while retaining legacy profile and phone import compatibility.
- Unified username and phone lookup into a Search workspace with Auto, Profile, and Phone modes plus source filters that avoid unnecessary provider calls.
- Reorganized the desktop application into Search, Datasets, Integrations, and History workspaces.
- Expanded profile and caller details with provider metadata, provenance, freshness, confidence, metrics, and raw JSON inspection.
- Increased the desktop window size and stopped opening DevTools in normal runs.
- Kept API failures scoped to their own source and search workflow.
- Added dataset routing, persistence, and readiness checks to the deployed architecture.
- Restricted saved provider credentials to the operating-system user and prevented existing secrets from being returned to the UI.
- Fixed platform-root discovery in packaged Electron layouts so integration settings use the correct `.env` file.
- Mapped X API failures to explicit profile-inspection responses, including `402` for depleted credits and `429` for rate limits.
- Made nginx resolve Compose service names at request time, preventing cross-service 404s after containers receive new IP addresses.

### Documentation

- Rewrote the root architecture and setup guide.
- Expanded environment-variable guidance.
- Rewrote the desktop UI guide and added a dataset service guide.
- Updated the OSINT Services organization profile README.

## 2026-07-16

### Added
- Added `/healthz` endpoints to the profile checker, profile search, and phone lookup services.
- Added a smoke test covering the health endpoints for the platform services.

### Changed
- Parallelized the username scan flow in the profile checker with a bounded semaphore to reduce overall request latency.
- Removed the obsolete `version` field from the Compose file and kept the deployment configuration in sync with newer Docker Compose behavior.

### Documentation
- Expanded the root README with notes about health checks and the recent hardening work.
