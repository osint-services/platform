# Changelog for 2026-07-16

## Added
- Added `/healthz` endpoints to the profile checker, profile search, and phone lookup services.
- Added a smoke test covering the health endpoints for the platform services.

## Changed
- Parallelized the username scan flow in the profile checker with a bounded semaphore to reduce overall request latency.
- Removed the obsolete `version` field from the Compose file and kept the deployment configuration in sync with newer Docker Compose behavior.

## Documentation
- Expanded the root README with notes about health checks and the recent hardening work.
