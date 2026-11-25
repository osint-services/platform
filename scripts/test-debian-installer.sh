#!/usr/bin/env bash
# Run on a disposable amd64 desktop test machine with Docker Compose v2 and Xvfb.
set -euo pipefail

package=$(realpath "${1:?Usage: scripts/test-debian-installer.sh PACKAGE [fresh|upgrade]}")
mode=${2:-fresh}
root=$(cd "$(dirname "$0")/.." && pwd)
scratch=$(mktemp -d)
export XDG_CONFIG_HOME="$scratch/config"
export XDG_CACHE_HOME="$scratch/cache"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"

app_pid=
cleanup() {
  if [[ -n "$app_pid" ]]; then kill -- "-$app_pid" 2>/dev/null || true; fi
  rm -rf -- "$scratch"
}
trap cleanup EXIT

base=http://127.0.0.1
settings="$XDG_CONFIG_HOME/whoisit/platform/.env"
if [[ "$mode" == upgrade ]]; then
  git clone --quiet --branch v1.1.0 --recurse-submodules https://github.com/osint-services/platform.git "$scratch/platform"
  legacy=(docker compose --project-name platform --file "$scratch/platform/docker-compose.yml")
  curl -fsSL --retry 3 -o "$scratch/whoisit_1.0.0_amd64.deb" \
    https://github.com/osint-services/whoisit/releases/download/v1.0.0/whoisit_1.0.0_amd64.deb
  chmod 755 "$scratch"
  sudo apt-get install -y "$scratch/whoisit_1.0.0_amd64.deb"
  "${legacy[@]}" up --build --detach
  curl -fsS --retry 30 --retry-delay 2 --retry-all-errors "$base/map/readyz" >/dev/null
  (cd "$root" && python3 scripts/test_social_mapping_e2e.py "$base")
  curl -fsS "$base/datasets" > "$scratch/legacy-datasets.json"
  "${legacy[@]}" exec -T social_mapping sh -c 'printf retained > /data/installer-smoke'
  # Simulate moving settings from the old checkout before the first unified launch.
  install -d -m 700 "$(dirname "$settings")"
  printf 'CERTIFICATE_INVENTORY_DOMAINS=example.test\n' > "$scratch/legacy.env"
  install -m 600 "$scratch/legacy.env" "$settings"
elif [[ "$mode" != fresh ]]; then
  echo "Expected fresh or upgrade." >&2
  exit 2
fi

version=$(dpkg-deb --field "$package" Version)
if docker image inspect "osint-services/dataset_service:$version" >/dev/null 2>&1; then
  echo "Candidate images are already loaded. Use a clean daemon for this test." >&2
  exit 1
fi
sudo apt-get install -y "$package"
test "$(dpkg-query -W -f='${Version}' whoisit)" = "$version"

# Launch through the installed executable as a regular user and read its readiness indicator.
setsid xvfb-run -a whoisit --remote-debugging-port=9222 > "$scratch/whoisit.log" 2>&1 &
app_pid=$!
if ! node "$root/scripts/wait-for-desktop.mjs"; then
  cat "$scratch/whoisit.log"
  docker ps -a --filter label=com.docker.compose.project=platform
  exit 1
fi

assets=/usr/lib/whoisit/resources/osint-platform
compose=(docker compose --project-name platform --env-file "$settings" --file "$assets/compose.yaml")
test "$("${compose[@]}" port proxy 80)" = '127.0.0.1:80'
test "$(stat -c %a "$settings")" = 600
docker image inspect "osint-services/dataset_service:$version" >/dev/null

if [[ "$mode" == upgrade ]]; then
  cmp "$settings" "$scratch/legacy.env"
  curl -fsS "$base/datasets" | cmp "$scratch/legacy-datasets.json" -
  test "$("${compose[@]}" exec -T social_mapping cat /data/installer-smoke)" = retained
  curl -fsS "$base/datasets/certificate-inventory" | python3 -c \
    'import json, sys; assert json.load(sys.stdin)["domains"] == ["example.test"]'
else
  (cd "$root" && python3 scripts/test_social_mapping_e2e.py "$base")
fi

echo "Verified $mode installation of Whoisit $version and the loopback gateway."
