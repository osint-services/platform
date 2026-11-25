#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

engine_version=$(docker info --format '{{.ServerVersion}}')
if [[ ! "$engine_version" =~ ^v?([0-9]+)\. ]] || (( BASH_REMATCH[1] < 28 )); then
  echo "Docker Engine 28 or newer is required to keep the gateway local." >&2
  exit 1
fi

docker compose up --build -d

echo "Docker Compose stack started. Use ./scripts/logs.sh to stream logs or ./scripts/stop.sh to stop."
