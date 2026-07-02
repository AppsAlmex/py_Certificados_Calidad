import pytest

from certificados.config import load_settings
from certificados.exceptions import ConfigError

CONFIG = """[service]
host = https://example.test
service_path = /svc
report_path = /Report.xdo
timeout = 45
verify_ssl = true

[output]
output_dir = out

[logging]
log_dir = logs
log_level = DEBUG
"""


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_env_overrides_credentials(tmp_path, monkeypatch):
    cfg = write(tmp_path, "config.ini", CONFIG)
    env = write(tmp_path, ".env", "CERT_USER=u\nCERT_PASSWORD=p\n")
    monkeypatch.delenv("CERT_USER", raising=False)
    monkeypatch.delenv("CERT_PASSWORD", raising=False)
    s = load_settings(cfg, env)
    assert s.user == "u"
    assert s.password == "p"
    assert s.service_url == "https://example.test/svc"
    assert s.timeout == 45
    assert s.verify_ssl is True
    assert s.log_level == "DEBUG"


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="No se encontro"):
        load_settings(tmp_path / "nope.ini", tmp_path / ".env")


def test_missing_credentials_raises(tmp_path, monkeypatch):
    cfg = write(tmp_path, "config.ini", CONFIG)
    env = write(tmp_path, ".env", "")
    monkeypatch.delenv("CERT_USER", raising=False)
    monkeypatch.delenv("CERT_PASSWORD", raising=False)
    with pytest.raises(ConfigError, match="Credenciales"):
        load_settings(cfg, env)
