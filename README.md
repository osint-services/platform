# platform

Stands up multiple microservices so they can be contacted using a single URI with `nginx` and `docker compose`.
Each service is stored as a git submodule; see each service directory for service-specific details.

## Requirements

- [`docker`](https://www.docker.com/)
- Docker Compose support (`docker compose`)

## Setup

1. Initialize submodules if needed:

```bash
git submodule update --init --recursive
```

2. Build and start all services:

```bash
./scripts/start.sh
```

3. Stop the stack:

```bash
./scripts/stop.sh
```

4. Rebuild the services:

```bash
./scripts/build.sh
```

5. Stream logs:

```bash
./scripts/logs.sh
```

## Notes

- The proxy listens on port `80` and routes `/scan/...` to `profile_checker`, `/focus` to `profile_search`, and `/phone_search` to `phone_search`.
- `profile_search` requires `TWEEPY_BEARER_TOKEN` to be available in the environment when running the Compose stack.
- `phone_search` requires `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` to be set.
- Copy `.env.example` to `.env` and fill in the required values before starting Compose.
- Each service now exposes a lightweight `/healthz` endpoint for smoke checks and container health probes.
- The new [whoisit](whoisit) submodule is intended to act as the UI layer that consumes the platform services under the hood.

## Changelog

- See [CHANGELOG.md](CHANGELOG.md) for the current release notes.
- See [CHANGELOG-2026-07-16.md](CHANGELOG-2026-07-16.md) for the latest dated entry.

## UI component

The [whoisit](whoisit) submodule is now included as the Electron-based UI layer for the platform. It can:
- probe the platform services over HTTP,
- attempt to start the Docker-based platform stack when needed, and
- call the scan, profile, and phone-lookup endpoints from the main UI.

If you want to add a screenshot later, place a file such as [whoisit/docs/ui-screenshot.png](whoisit/docs/ui-screenshot.png) and reference it from this section.
