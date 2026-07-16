import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def apps(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret")
    monkeypatch.setenv("TWEEPY_BEARER_TOKEN", "token")

    phone_server = importlib.import_module("phone_search.server")
    profile_search_server = importlib.import_module("profile_search.server")
    profile_checker_main = importlib.import_module("profile_checker.main")

    return {
        "phone": phone_server.app,
        "profile_search": profile_search_server.app,
        "profile_checker": profile_checker_main.app,
    }


def test_health_endpoint_is_available(apps):
    for app_name, app in apps.items():
        with TestClient(app) as client:
            response = client.get("/healthz")
            assert response.status_code == 200, f"{app_name} did not expose /healthz"
            assert response.json() == {"status": "ok"}
