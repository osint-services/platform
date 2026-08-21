#!/usr/bin/env python3
import csv
import json
from pathlib import Path
import sys
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "datasets" / "geospatial_entities.csv"


def main() -> int:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost").rstrip("/")
    with SAMPLE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    payload = json.dumps(
        {
            "name": "Synthetic geospatial entities",
            "filename": SAMPLE.name,
            "record_type": "entity",
            "rows": rows,
        }
    ).encode("utf-8")
    import_request = request.Request(
        f"{base_url}/datasets/import",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(import_request, timeout=20) as response:
            result = json.load(response)
    except error.HTTPError as exc:
        print(exc.read().decode("utf-8"), file=sys.stderr)
        return 1
    print(f"Imported {result['imported']} synthetic geospatial entities into dataset {result['dataset_id']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
