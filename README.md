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
