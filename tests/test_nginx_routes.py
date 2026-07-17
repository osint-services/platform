from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nginx_uses_docker_dns_for_runtime_service_resolution():
    config = (ROOT / "nginx.conf").read_text(encoding="utf-8")

    assert "resolver 127.0.0.11" in config
    for service in (
        "profile_checker",
        "profile_search",
        "phone_search",
        "dataset_service",
    ):
        assert f"set ${service}_upstream {service}:8000;" in config
        assert f"proxy_pass http://${service}_upstream" in config


def test_nginx_keeps_health_and_application_routes_separate():
    config = (ROOT / "nginx.conf").read_text(encoding="utf-8")

    assert "location = /scan/healthz" in config
    assert "location /scan/" in config
    assert "location = /focus/readyz" in config
    assert "location /focus" in config
    assert "location = /phone_search/healthz" in config
    assert "location /phone_search" in config
    assert "location = /datasets/healthz" in config
    assert "location /datasets" in config
