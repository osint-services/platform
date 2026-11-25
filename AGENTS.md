# Platform contributor guide

## Ownership

This repository owns `dataset_service/` (imports, SQLite storage and geo search), `docker-compose.yml`, the shared `Dockerfile`, `nginx.conf`, platform scripts, CI, integration tests, and platform docs and fixtures. Keep the local nginx gateway bound to IPv4 loopback. See the [platform README](README.md) for setup and routing.

## Submodules

Initialize the pinned checkouts with `git submodule update --init --recursive`.

| Path | Owns |
| --- | --- |
| `profile_checker/` | Public username availability |
| `profile_search/` | X profile metadata |
| `phone_search/` | Caller-name lookup |
| `social_mapping/` | GeoJSON API, origin geocoding, and standalone map client |
| `whoisit/` | Electron desktop app and native Map workspace |

Make service or desktop changes on a branch in the owning submodule repository. Open a PR there and run its checks. Once it merges, check out the intended merged commit in the submodule, stage the submodule path from the platform root, and open a platform PR for the pin and any dependent integration changes. Link the upstream PR and review the staged revision with `git diff --cached --submodule=log`.

## Platform checks

Run from the platform root. With Python 3.12 in a virtual environment, use the dependencies and checks from [platform CI](.github/workflows/integration.yml).

```sh
python -m pip install -c runtime-constraints.txt pytest pytest-asyncio \
  -r dataset_service/requirements.txt -r profile_checker/requirements.txt \
  -r profile_search/requirements.txt -r phone_search/requirements.txt
pytest -q tests
docker compose config --quiet
```

Use a clean local Compose project for the credential-free London check. Start the services, wait for the map readiness request to succeed, then run the smoke script. It imports the synthetic fixture and checks the dataset-backed GeoJSON through nginx.

```sh
docker compose up --build -d dataset_service social_mapping proxy
curl --fail --silent --show-error http://localhost/map/readyz
python3 scripts/test_social_mapping_e2e.py
```

## Evidence contracts

- Follow the [map evidence rules](https://github.com/osint-services/social_mapping/blob/main/README.md#accuracy-and-responsible-use). Preserve the source, accuracy, and provenance of map evidence. Accept dataset coordinates only as an explicit valid pair, geocode only the search origin, and treat associated phone records as metadata.
- Follow the [certificate inventory evidence contract](docs/certificate-inventory.md) and its [synthetic fixtures](examples/certificate-inventory/contract.json) when changing certificate inventory behavior.
