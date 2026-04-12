#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose up --build -d

echo "Docker Compose stack started. Use ./scripts/logs.sh to stream logs or ./scripts/stop.sh to stop."