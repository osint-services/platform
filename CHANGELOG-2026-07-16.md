# Changelog for 2026-07-16

## Added
- Added `/healthz` endpoints to the profile checker, profile search, and phone lookup services.
- Added a smoke test covering the health endpoints for the platform services.

## Changed
- Parallelized the username scan flow in the profile checker with a bounded semaphore to reduce overall request latency.
- Removed the obsolete `version` field from the Compose file and kept the deployment configuration in sync with newer Docker Compose behavior.

## Documentation
- Expanded the root README with notes about health checks and the recent hardening work.
- Documented the new UI submodule and the bootstrap behavior that checks or starts the platform services.

## Added
- Added an Electron-based UI submodule, [whoisit](whoisit), that can probe the platform status and attempt to start the Docker-based stack when services are not yet reachable.
