import csv
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SOCIAL_MAPPING_ROOT = ROOT / "social_mapping"
for path in (ROOT, SOCIAL_MAPPING_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dataset_service.server import create_app as create_dataset_app
from social_mapping import server as map_server


class FixedGeocoder:
    async def resolve(self, query):
        assert query == "London"
        return {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "label": "London, United Kingdom",
            "provider": "nominatim",
            "cached": True,
        }


class LocalDatasetProvider:
    def __init__(self, repository):
        self.repository = repository

    async def search(self, **parameters):
        return self.repository.search_geo(**parameters)


def test_import_and_london_map_search_without_live_credentials(tmp_path, monkeypatch):
    dataset_app = create_dataset_app(tmp_path / "e2e.db")
    dataset_client = TestClient(dataset_app)
    with (ROOT / "examples" / "datasets" / "geospatial_entities.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    imported = dataset_client.post(
        "/datasets/import",
        json={"name": "Synthetic geospatial entities", "record_type": "entity", "rows": rows},
    )
    assert imported.status_code == 201

    monkeypatch.setattr(map_server, "get_geocoder", lambda: FixedGeocoder())
    monkeypatch.setattr(
        map_server,
        "get_providers",
        lambda: {
            "datasets": LocalDatasetProvider(dataset_app.state.repository),
            "x": LocalDatasetProvider(dataset_app.state.repository),
        },
    )
    map_client = TestClient(map_server.app)
    response = map_client.get(
        "/map/search",
        params={"place": "London", "radius_miles": 5, "sources": "datasets"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["providers"]["datasets"]["status"] == "ok"
    marker = payload["features"][0]
    assert marker["properties"]["title"] == "London Map Demo"
    assert marker["properties"]["source"] == "datasets"
    assert marker["properties"]["location_accuracy"] == "exact"
    assert marker["properties"]["associated_phones"][0]["phone_number"] == "+12025550111"
