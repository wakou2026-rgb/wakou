from pathlib import Path


def test_nginx_has_uploads_proxy_location():
    config_path = Path(__file__).resolve().parents[2] / "infra" / "nginx" / "default.conf"
    config = config_path.read_text(encoding="utf-8")

    assert "location ^~ /uploads/" in config
    assert "proxy_pass http://backend:8000" in config
