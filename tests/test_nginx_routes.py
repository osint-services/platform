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
        "social_mapping",
    ):
        assert f"set ${service}_upstream {service}:8000;" in config
        assert f"proxy_pass http://${service}_upstream" in config


def test_nginx_keeps_health_and_application_routes_separate():
    config = (ROOT / "nginx.conf").read_text(encoding="utf-8")

    assert "location = /scan/healthz" in config
    assert "location /scan/" in config
    assert "location = /focus/healthz" in config
    assert "location = /focus/readyz" in config
    assert "location /focus" in config
    assert "location = /phone_search/healthz" in config
    assert "location /phone_search" in config
    assert "proxy_pass http://$phone_search_upstream/lookup/caller-name$is_args$args;" in config
    assert "location = /datasets/healthz" in config
    assert "location /datasets" in config
    assert "location /map/" in config
    assert "location = /search/tweets" in config
    assert "proxy_pass http://$social_mapping_upstream/search/tweets$is_args$args;" in config


def test_larger_request_limit_is_scoped_to_dataset_imports():
    config = (ROOT / "nginx.conf").read_text(encoding="utf-8")
    import_location = config.split("location = /datasets/import {", 1)[1].split("}", 1)[0]
    assert "client_max_body_size 16m;" in import_location
    assert config.count("client_max_body_size") == 1
