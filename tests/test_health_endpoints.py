import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def apps(monkeypatch, tmp_path):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret")
    monkeypatch.setenv("TWEEPY_BEARER_TOKEN", "token")

    phone_server = importlib.import_module("phone_search.server")
    profile_search_server = importlib.import_module("profile_search.server")
    profile_checker_main = importlib.import_module("profile_checker.main")
    from dataset_service.server import create_app as create_dataset_app

    return {
        "phone": phone_server.app,
        "profile_search": profile_search_server.app,
        "profile_checker": profile_checker_main.app,
        "dataset": create_dataset_app(tmp_path / "health-datasets.db"),
    }


def test_health_endpoint_is_available(apps):
    for app_name, app in apps.items():
        with TestClient(app) as client:
            response = client.get("/healthz")
            assert response.status_code == 200, f"{app_name} did not expose /healthz"
            assert response.json() == {"status": "ok"}


def test_profile_search_readiness_requires_bearer_token(apps, monkeypatch):
    with TestClient(apps["profile_search"]) as client:
        monkeypatch.delenv("TWEEPY_BEARER_TOKEN", raising=False)
        monkeypatch.delenv("BEARER_TOKEN", raising=False)

        response = client.get("/readyz")

        assert response.status_code == 503
        assert "TWEEPY_BEARER_TOKEN is missing" in response.json()["detail"]


def test_profile_search_returns_configuration_error(apps, monkeypatch):
    with TestClient(apps["profile_search"]) as client:
        monkeypatch.delenv("TWEEPY_BEARER_TOKEN", raising=False)
        monkeypatch.delenv("BEARER_TOKEN", raising=False)

        response = client.get(
            "/focus",
            params={"url": "https://x.com/example"},
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.status_code == 503
        assert "Missing TWEEPY_BEARER_TOKEN" in response.json()["detail"]
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
