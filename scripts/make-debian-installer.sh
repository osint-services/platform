#!/usr/bin/env bash
set -euo pipefail

version=${1:?Usage: scripts/make-debian-installer.sh MAJOR.MINOR.PATCH OUTPUT_DIRECTORY}
output=${2:?Specify an output directory}
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Expected a platform version in MAJOR.MINOR.PATCH format." >&2
  exit 2
fi

mkdir -p "$output"
output=$(cd "$output" && pwd)
cd "$(dirname "$0")/.."
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
assets="$stage/osint-platform"
mkdir "$assets"
cp nginx.conf "$assets/"

export DOCKER_DEFAULT_PLATFORM=linux/amd64
compose=(docker compose --project-name platform --file docker-compose.yml)
proxy_image=$(
  "${compose[@]}" config --no-interpolate --no-path-resolution --no-normalize --format json |
    python3 scripts/render-installer-compose.py "$version" "$assets/compose.yaml" "$stage/build.yaml"
)
"${compose[@]}" --file "$stage/build.yaml" build --pull
docker pull --platform linux/amd64 "$proxy_image"
docker image tag "$proxy_image" "osint-services/proxy:$version"

bundle=(docker compose --project-name platform --env-file /dev/null --file "$assets/compose.yaml")
"${bundle[@]}" config --quiet
image_list=$("${bundle[@]}" config --images)
mapfile -t images <<< "$image_list"
docker image save "${images[@]}" | gzip -1 > "$assets/images.tar.gz"

# Build the pinned desktop in a temporary copy, with the platform release as its package version.
mkdir "$stage/desktop"
git -C whoisit archive "$(git rev-parse HEAD:whoisit)" | tar -x -C "$stage/desktop"
(
  cd "$stage/desktop"
  npm version "$version" --no-git-tag-version --allow-same-version
  npm ci
  npm test
  WHOISIT_PLATFORM_RESOURCES="$assets" npm run make -- --platform linux --arch x64 --targets @electron-forge/maker-deb
  package="out/make/deb/x64/whoisit_${version}_amd64.deb"
  dpkg-deb --fsys-tarfile "$package" | tar --list --file - > "$stage/package-files"
  for asset in compose.yaml nginx.conf images.tar.gz; do
    if ! grep -Fxq "./usr/lib/whoisit/resources/osint-platform/$asset" "$stage/package-files"; then
      echo "Whoisit did not package $asset. Check the pinned desktop revision." >&2
      exit 1
    fi
  done
  cp "$package" "$output/"
)
(
  cd "$output"
  sha256sum "whoisit_${version}_amd64.deb" > "whoisit_${version}_amd64.deb.sha256"
)
