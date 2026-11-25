#!/usr/bin/env bash
# Run on a disposable amd64 desktop test machine with Docker Compose v2 or v5 and Xvfb.
set -euo pipefail

package=$(realpath "${1:?Usage: scripts/test-debian-installer.sh PACKAGE [fresh|upgrade]}")
mode=${2:-fresh}
root=$(cd "$(dirname "$0")/.." && pwd)
scratch=$(mktemp -d)
export XDG_CONFIG_HOME="$scratch/config"
export XDG_CACHE_HOME="$scratch/cache"
unset TWEEPY_BEARER_TOKEN TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN
mkdir -p "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"

app_pid=
cleanup() {
  if [[ -n "$app_pid" ]]; then kill -- "-$app_pid" 2>/dev/null || true; fi
  rm -rf -- "$scratch"
}
trap cleanup EXIT

base=http://127.0.0.1
settings="$XDG_CONFIG_HOME/whoisit/platform/.env"
assets=/usr/lib/whoisit/resources/osint-platform
compose=(docker compose --project-name platform --env-file "$settings" --file "$assets/compose.yaml")

launch_whoisit() {
  setsid xvfb-run -a whoisit --remote-debugging-port=9222 > "$scratch/whoisit.log" 2>&1 &
  app_pid=$!
  if ! node "$root/scripts/wait-for-desktop.mjs"; then
    cat "$scratch/whoisit.log"
    docker ps -a --filter label=com.docker.compose.project=platform
    return 1
  fi
}

if [[ "$mode" == upgrade ]]; then
  previous=1.2.1
  previous_package="whoisit_${previous}_amd64.deb"
  previous_release="https://github.com/osint-services/platform/releases/download/v$previous"
  curl -fsSL --retry 3 -o "$scratch/$previous_package" "$previous_release/$previous_package"
  curl -fsSL --retry 3 -o "$scratch/$previous_package.sha256" "$previous_release/$previous_package.sha256"
  (cd "$scratch" && sha256sum -c "$previous_package.sha256")
  chmod 755 "$scratch"
  sudo apt-get install -y "$scratch/$previous_package"
  test "$(dpkg-query -W -f='${Version}' whoisit)" = "$previous"
  install -d -m 700 "$(dirname "$settings")"
  printf 'CERTIFICATE_INVENTORY_DOMAINS=example.test\n' > "$scratch/previous.env"
  install -m 600 "$scratch/previous.env" "$settings"
  launch_whoisit
  (cd "$root" && python3 scripts/test_social_mapping_e2e.py "$base")
  curl -fsS "$base/datasets" > "$scratch/previous-datasets.json"
  "${compose[@]}" exec -T social_mapping sh -c 'printf retained > /data/installer-smoke'
  kill -- "-$app_pid"
  wait "$app_pid" || true
  app_pid=
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
launch_whoisit

test "$("${compose[@]}" port proxy 80)" = '127.0.0.1:80'
test "$(stat -c %a "$settings")" = 600
docker image inspect "osint-services/dataset_service:$version" >/dev/null
test "$(curl -sS -o "$scratch/phone-response.json" -w '%{http_code}' \
  "$base/phone_search?phone_number=%2B12025550101")" = 503
python3 -c 'import json, sys; assert json.load(sys.stdin)["detail"] == "Twilio Lookup is not configured."' \
  < "$scratch/phone-response.json"

test "$(curl -sS -G -o "$scratch/map-response.json" -w '%{http_code}' \
  --data-urlencode 'place=London' --data-urlencode 'sources=unsupported' "$base/map/search")" = 422
python3 -c 'import json, sys; assert json.load(sys.stdin)["detail"] == "unsupported sources: unsupported"' \
  < "$scratch/map-response.json"

if [[ "$mode" == upgrade ]]; then
  cmp "$settings" "$scratch/previous.env"
  curl -fsS "$base/datasets" | cmp "$scratch/previous-datasets.json" -
  test "$("${compose[@]}" exec -T social_mapping cat /data/installer-smoke)" = retained
  curl -fsS "$base/datasets/certificate-inventory" | python3 -c \
    'import json, sys; assert json.load(sys.stdin)["domains"] == ["example.test"]'
else
  (cd "$root" && python3 scripts/test_social_mapping_e2e.py "$base")
  python3 - "$base" <<'PYTHON'
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

base = sys.argv[1]
body = json.dumps({
    "name": "Large synthetic import",
    "record_type": "entity",
    "rows": [{"username": f"synthetic_{i}", "bio": "sample " * 300} for i in range(600)],
}).encode()
assert 1024 * 1024 < len(body) < 16 * 1024 * 1024
with urlopen(Request(
    f"{base}/datasets/import", data=body, headers={"Content-Type": "application/json"}
), timeout=20) as response:
    assert response.status == 201
    assert json.load(response)["imported"] == 600

# An invalid radius prevents calls to external providers while testing query forwarding.
try:
    urlopen(f"{base}/search/tweets?city=London&distance=-1", timeout=10)
except HTTPError as error:
    assert error.code == 422
    assert [item["loc"] for item in json.load(error)["detail"]] == [["query", "distance"]]
else:
    raise AssertionError("The legacy map route accepted an invalid distance.")
PYTHON
fi

echo "Verified $mode installation of Whoisit $version and the loopback gateway."
