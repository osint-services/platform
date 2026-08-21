#!/usr/bin/env python3
import json
import subprocess
import sys
from urllib import parse, request


def main() -> int:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost").rstrip("/")
    subprocess.run([sys.executable, "scripts/import_geospatial_demo.py", base_url], check=True)
    query = parse.urlencode(
        {"latitude": 51.5074, "longitude": -0.1278, "radius_miles": 5, "sources": "datasets"}
    )
    with request.urlopen(f"{base_url}/map/search?{query}", timeout=20) as response:
        payload = json.load(response)
    matches = [feature for feature in payload["features"] if feature["properties"]["title"] == "London Map Demo"]
    if len(matches) != 1:
        raise RuntimeError("London synthetic marker was not returned")
    properties = matches[0]["properties"]
    if properties["source"] != "datasets" or properties["location_accuracy"] != "exact":
        raise RuntimeError("London marker is missing source or accuracy metadata")
    if not properties["associated_phones"]:
        raise RuntimeError("Associated phone metadata was not returned")
    print("Social Mapping end-to-end check passed with the synthetic London marker.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
