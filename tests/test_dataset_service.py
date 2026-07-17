import csv
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataset_service.server import create_app


def make_client(tmp_path):
    return TestClient(create_app(tmp_path / "datasets.db"))


def test_health_and_schema_are_available(tmp_path):
    client = make_client(tmp_path)

    assert client.get("/healthz").json() == {"status": "ok"}
    schema = client.get("/datasets/schema/profile")
    assert schema.status_code == 200
    assert schema.json()["record_type"] == "profile"
    assert any(field["key"] == "username" for field in schema.json()["fields"])


def test_profile_import_preserves_provenance_and_supports_fuzzy_search(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/datasets/import",
        json={
            "name": "Conference profiles",
            "record_type": "profile",
            "filename": "profiles.csv",
            "mapping": {
                "username": "handle",
                "platform": "network",
                "display_name": "full_name",
                "bio": "description",
                "followers_count": "followers",
                "verified": "is_verified",
                "confidence": "score",
            },
            "rows": [
                {
                    "handle": "@AdaLovelace",
                    "network": "X",
                    "full_name": "Ada Lovelace",
                    "description": "Computing pioneer",
                    "followers": "1200",
                    "is_verified": "yes",
                    "score": "0.92",
                    "unmapped_note": "preserve me",
                },
                {
                    "handle": "",
                    "network": "X",
                    "full_name": "No identifier",
                },
            ],
        },
    )

    assert response.status_code == 201
    result = response.json()
    assert result["imported"] == 1
    assert result["rejected"] == 1
    assert result["rejected_rows"][0]["row_number"] == 2

    exact = client.get(
        "/datasets/search/profiles", params={"query": "adalovelace"}
    ).json()["records"]
    assert len(exact) == 1
    record = exact[0]
    assert record["username"] == "AdaLovelace"
    assert record["verified"] is True
    assert record["metrics"]["followers_count"] == 1200
    assert record["dataset_name"] == "Conference profiles"
    assert record["confidence"] == 0.92
    assert record["raw"]["unmapped_note"] == "preserve me"

    fuzzy = client.get(
        "/datasets/search/profiles",
        params={"query": "lovelac", "fuzzy": "true"},
    ).json()["records"]
    assert len(fuzzy) == 1

    datasets = client.get("/datasets").json()
    assert datasets[0]["row_count"] == 1
    assert datasets[0]["rejected_count"] == 1


def test_phone_import_search_records_and_delete(tmp_path):
    client = make_client(tmp_path)
    imported = client.post(
        "/datasets/import",
        json={
            "name": "Subscriber export",
            "record_type": "phone",
            "filename": "subscribers.jsonl",
            "mapping": {
                "phone_number": "number",
                "caller_name": "name",
                "country_code": "country",
                "carrier_name": "carrier",
                "line_type": "kind",
            },
            "rows": [
                {
                    "number": "+1 (813) 555-1212",
                    "name": "Example Subscriber",
                    "country": "US",
                    "carrier": "Example Wireless",
                    "kind": "mobile",
                },
                {"number": "not-a-number", "name": "Invalid"},
            ],
        },
    )

    assert imported.status_code == 201
    result = imported.json()
    assert result["imported"] == 1
    dataset_id = result["dataset_id"]

    matches = client.get(
        "/datasets/search/phones", params={"phone_number": "+18135551212"}
    ).json()["records"]
    assert len(matches) == 1
    assert matches[0]["phone_number"] == "+18135551212"
    assert matches[0]["caller_name"] == "Example Subscriber"
    assert matches[0]["carrier_name"] == "Example Wireless"

    records = client.get(f"/datasets/{dataset_id}/records")
    assert records.status_code == 200
    assert len(records.json()["records"]) == 1

    assert client.delete(f"/datasets/{dataset_id}").status_code == 204
    assert client.get("/datasets").json() == []
    assert (
        client.get(
            "/datasets/search/phones", params={"phone_number": "+18135551212"}
        ).json()["records"]
        == []
    )


def test_documented_sample_files_import_and_search(tmp_path):
    client = make_client(tmp_path)
    samples = ROOT / "examples" / "datasets"

    with (samples / "sample_profiles.csv").open(newline="", encoding="utf-8") as file:
        profile_rows = list(csv.DictReader(file))
    profile_import = client.post(
        "/datasets/import",
        json={
            "name": "Fictional profile samples",
            "record_type": "profile",
            "filename": "sample_profiles.csv",
            "rows": profile_rows,
        },
    )
    assert profile_import.status_code == 201
    assert profile_import.json()["imported"] == 4
    assert profile_import.json()["rejected"] == 0

    profiles = client.get(
        "/datasets/search/profiles", params={"query": "demo_ada_1843"}
    ).json()["records"]
    assert len(profiles) == 1
    assert profiles[0]["name"] == "Ada Example"
    assert profiles[0]["metrics"]["followers_count"] == 12450

    with (samples / "sample_phone_records.jsonl").open(encoding="utf-8") as file:
        phone_rows = [json.loads(line) for line in file if line.strip()]
    phone_import = client.post(
        "/datasets/import",
        json={
            "name": "Fictional phone samples",
            "record_type": "phone",
            "filename": "sample_phone_records.jsonl",
            "rows": phone_rows,
        },
    )
    assert phone_import.status_code == 201
    assert phone_import.json()["imported"] == 4
    assert phone_import.json()["rejected"] == 0

    phones = client.get(
        "/datasets/search/phones", params={"phone_number": "+12025550104"}
    ).json()["records"]
    assert len(phones) == 1
    assert phones[0]["valid"] is False
    assert phones[0]["raw"]["case_note"].endswith(
        "used to exercise false and null values."
    )
