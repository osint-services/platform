import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataset_service.certificate_inventory import inventory_router


def test_refresh_retains_last_success(tmp_path):
    row = {"id": 42, "name_value": "APP.example.test\napp.example.test\n*.example.test\nother.test"}
    responses = iter([[row], [row], [row, {}], httpx.ReadTimeout("offline"), []])

    def fetch(domain):
        assert domain == "example.test"
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    app = FastAPI()
    app.include_router(inventory_router(tmp_path / "inventory.db", "example.test", fetch))
    client = TestClient(app)
    root = "/datasets/certificate-inventory"
    assert client.post(root + "/other.test/refresh").status_code == 404
    refresh = root + "/example.test/refresh"
    for _ in range(2):
        good = client.post(refresh).json()
        assert good["last_outcome"] == "success"
        assert [r["name"] for r in good["observations"]] == ["app.example.test", "*.example.test"]
    for outcome in ("invalid_response", "provider_failure"):
        stale = client.post(refresh).json()
        assert stale["last_outcome"] == outcome
        assert stale["observations"] == good["observations"]
        assert stale["completed_at"] == good["completed_at"]
    empty = client.post(refresh).json()
    assert empty["completed_at"] and empty["observations"] == []
