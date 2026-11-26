#!/usr/bin/env bash
set -euo pipefail

package=$(realpath "${1:?Usage: scripts/scan-installer-images.sh PACKAGE REPORT_DIRECTORY}")
reports=${2:?Specify the report directory}
version=$(dpkg-deb -f "$package" Version)
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$reports"

assets=./usr/lib/whoisit/resources/osint-platform
dpkg-deb --fsys-tarfile "$package" | tar --extract --directory "$scratch" \
  "$assets/compose.yaml" "$assets/images.tar.gz"
images=$(docker compose --env-file /dev/null --file "$scratch/$assets/compose.yaml" config --images)
if [[ -z "$images" ]]; then
  echo 'No images to scan in the installer Compose configuration.' >&2
  exit 1
fi
archive="$scratch/$assets/images.tar.gz"
tar -xOf "$archive" manifest.json | python3 -c '
import json
import sys

bundled = {tag for image in json.load(sys.stdin) for tag in image.get("RepoTags") or []}
configured = set(sys.argv[1].splitlines())
if bundled != configured:
    sys.exit(f"Image archive and Compose differ: {sorted(bundled ^ configured)}")
' "$images"
docker image load --input "$archive"
trivy image --download-db-only --no-progress

blocked=0
while IFS= read -r image; do
  if [[ ! "$image" =~ ^osint-services/([a-z][a-z0-9_]*):([0-9]+\.[0-9]+\.[0-9]+)$ || "${BASH_REMATCH[2]}" != "$version" ]]; then
    printf 'Unexpected bundled image reference: %s\n' "$image" >&2
    exit 1
  fi
  service=${BASH_REMATCH[1]}
  report="$reports/$service.trivy.json"
  trivy image --image-src docker --skip-db-update --offline-scan --no-progress \
    --scanners vuln --pkg-types os,library --format json --output "$report" "$image"
  if ! python3 - "$report" <<'PYTHON'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
results = report.get("Results", [])
classes = {result.get("Class") for result in results}
if "os-pkgs" not in classes or (
    Path(sys.argv[1]).name != "proxy.trivy.json"
    and not any(result.get("Type") == "python-pkg" for result in results)
):
    sys.exit(f"{report['ArtifactName']}: expected package inventory is missing")

findings = [entry for result in results for entry in result.get("Vulnerabilities") or []]
blocking = [entry for entry in findings if entry.get("FixedVersion")
            and entry["Severity"] in {"HIGH", "CRITICAL"}]
print(f"{report['ArtifactName']}: {len(findings)} findings, {len(blocking)} with fixes that block release")
for entry in blocking:
    print(f"{entry['VulnerabilityID']} {entry['PkgName']} {entry['InstalledVersion']}"
          f" -> {entry['FixedVersion']} ({entry['Severity']})")
sys.exit(bool(blocking))
PYTHON
  then
    blocked=1
  fi
done <<< "$images"
exit "$blocked"
