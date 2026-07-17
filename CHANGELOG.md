# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Added a sparse entity model that associates optional profile and phone identifiers while preserving their type-specific metadata.
- Added a persistent SQLite dataset service for mapped profile and phone imports.
- Added CSV, JSON, JSONL, and NDJSON parsing, previews, automatic field suggestions, per-row validation, provenance, and raw-record retention.
- Added combined live and imported-source searching, local search history, raw JSON inspection, and dataset management to the Electron UI.
- Added an Integrations workspace for X/Tweepy, Twilio Lookup, and local dataset connection status with protected credential replacement.
- Expanded username result cards with public validation evidence, direct profile links, dataset provenance, observation time, and confidence.
- Added fictional profile CSV and phone JSONL datasets for testing imports, mapping, local search, and rich result rendering.
- Expanded regression coverage for dataset import, fuzzy profile search, normalized phone search, deletion, health endpoints, and client-side parsers.

### Changed
- Replaced separate profile and phone dataset ingestion with one entity mapping pipeline; legacy API imports remain compatible and existing SQLite databases migrate in place.
- Unified username and phone lookup into one Search workspace with conservative auto-detection, explicit Profile and Phone modes, and source filters that control which APIs and datasets are queried.
- Reworked the Electron interface into cohesive Search, Datasets, Integrations, and History workspaces with type-specific master/detail results.
- Isolated live-provider failures so other sources can still return results and errors remain in the correct search workspace.
- Expanded profile and phone detail views with provider metadata, provenance, freshness, confidence, metrics, and raw source records.
- Added the dataset service to Docker Compose, nginx routing, persistent storage, and desktop readiness probes.
- Increased the desktop window size and stopped opening DevTools in normal runs.
- Kept stored provider secrets out of the renderer and applied credential changes through atomic, owner-only `.env` updates.
- Fixed packaged Electron builds so they locate the parent platform configuration and report the real integration state.
- Replaced opaque profile-inspection 500 errors with actionable X provider responses for depleted credits, rate limits, invalid access, and missing profiles.
- Switched nginx service routing to Docker's runtime DNS resolver so container recreation cannot silently send requests to reassigned service IPs.

### Documentation
- Updated the platform, environment, desktop UI, dataset service, and organization profile documentation for the current architecture.
- Added [2026-07-17 release notes](CHANGELOG-2026-07-17.md).
