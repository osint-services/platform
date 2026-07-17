# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Added a persistent SQLite dataset service for mapped profile and phone imports.
- Added CSV, JSON, JSONL, and NDJSON parsing, previews, automatic field suggestions, per-row validation, provenance, and raw-record retention.
- Added combined live and imported-source searching, local search history, raw JSON inspection, and dataset management to the Electron UI.
- Added an Integrations workspace for X/Tweepy, Twilio Lookup, and local dataset connection status with protected credential replacement.
- Expanded regression coverage for dataset import, fuzzy profile search, normalized phone search, deletion, health endpoints, and client-side parsers.

### Changed
- Reworked the Electron interface into cohesive Username, Phone, Datasets, and History workspaces with master/detail results.
- Isolated live-provider failures so other sources can still return results and errors remain in the correct search workspace.
- Expanded profile and phone detail views with provider metadata, provenance, freshness, confidence, metrics, and raw source records.
- Added the dataset service to Docker Compose, nginx routing, persistent storage, and desktop readiness probes.
- Increased the desktop window size and stopped opening DevTools in normal runs.
- Kept stored provider secrets out of the renderer and applied credential changes through atomic, owner-only `.env` updates.

### Documentation
- Updated the platform, environment, desktop UI, dataset service, and organization profile documentation for the current architecture.
- Added [2026-07-17 release notes](CHANGELOG-2026-07-17.md).
