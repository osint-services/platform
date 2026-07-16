# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Added lightweight `/healthz` endpoints to the FastAPI services for smoke checks and container health probes.
- Added an initial regression test suite covering the new health endpoints.

### Changed
- Parallelized profile checker requests with bounded concurrency to reduce scan latency across site checks.
- Removed the obsolete Compose `version` field from the deployment configuration to avoid startup warnings.

### Documentation
- Updated the platform README to describe the new health checks and operational improvements.
- Documented the new Electron UI submodule and its startup/bootstrap behavior.

### Added
- Added a new Electron-based UI submodule, [whoisit](whoisit), that can inspect the platform status and attempt to start the stack when needed.
