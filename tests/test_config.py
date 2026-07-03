import pytest

from certificados.config import load_settings
from certificados.exceptions import ConfigError

CONFIG = """[service]
host = https://example.test
service_path = /svc
timeout = 45
verify_ssl = true
default_report = alpha

[reports]
alpha = /Reports/Alpha.xdo
beta = /Reports/Beta.xdo

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


def test_default_report_selected(tmp_path, monkeypatch):
    cfg = write(tmp_path, "config.ini", CONFIG)
    env = write(tmp_path, ".env", "CERT_USER=u\nCERT_PASSWORD=p\n")
    monkeypatch.delenv("CERT_REPORT", raising=False)
    monkeypatch.delenv("CERT_TIMEOUT", raising=False)
    s = load_settings(cfg, env)
    assert s.report_key == "alpha"
    assert s.report_path == "/Reports/Alpha.xdo"
    assert set(s.reports) == {"alpha", "beta"}


def test_env_selects_report_and_timeout(tmp_path, monkeypatch):
    cfg = write(tmp_path, "config.ini", CONFIG)
    env = write(tmp_path, ".env", "CERT_USER=u\nCERT_PASSWORD=p\nCERT_REPORT=beta\nCERT_TIMEOUT=90\n")
    s = load_settings(cfg, env)
    assert s.report_key == "beta"
    assert s.report_path == "/Reports/Beta.xdo"
    assert s.timeout == 90


def test_arg_overrides_env(tmp_path, monkeypatch):
    cfg = write(tmp_path, "config.ini", CONFIG)
    env = write(tmp_path, ".env", "CERT_USER=u\nCERT_PASSWORD=p\nCERT_REPORT=beta\n")
    s = load_settings(cfg, env, report="alpha", timeout=15)
    assert s.report_key == "alpha"
    assert s.timeout == 15


def test_unknown_report_raises(tmp_path, monkeypatch):
    cfg = write(tmp_path, "config.ini", CONFIG)
    env = write(tmp_path, ".env", "CERT_USER=u\nCERT_PASSWORD=p\n")
    monkeypatch.delenv("CERT_REPORT", raising=False)
    with pytest.raises(ConfigError, match="no existe"):
        load_settings(cfg, env, report="zeta")


def test_invalid_timeout_raises(tmp_path, monkeypatch):
    cfg = write(tmp_path, "config.ini", CONFIG)
    env = write(tmp_path, ".env", "CERT_USER=u\nCERT_PASSWORD=p\n")
    monkeypatch.delenv("CERT_TIMEOUT", raising=False)
    with pytest.raises(ConfigError, match="timeout"):
        load_settings(cfg, env, timeout=0)


def _env(tmp_path):
    return write(tmp_path, "config.ini", CONFIG), write(tmp_path, ".env", "CERT_USER=u\nCERT_PASSWORD=p\n")


def test_workers_zero_or_negative_rejected(tmp_path):
    cfg, env = _env(tmp_path)
    with pytest.raises(ConfigError, match="workers"):
        load_settings(cfg, env, workers=0)
    with pytest.raises(ConfigError, match="workers"):
        load_settings(cfg, env, workers=-3)


def test_workers_max_boundary_ok(tmp_path):
    from certificados.config import MAX_WORKERS
    cfg, env = _env(tmp_path)
    assert load_settings(cfg, env, workers=MAX_WORKERS).max_workers == MAX_WORKERS


def test_workers_above_cap_rejected(tmp_path):
    from certificados.config import MAX_WORKERS
    cfg, env = _env(tmp_path)
    with pytest.raises(ConfigError, match="100"):
        load_settings(cfg, env, workers=MAX_WORKERS + 1)


def test_workers_cap_from_env_and_config(tmp_path, monkeypatch):
    # el tope tambien aplica si se intenta poner por env o config.ini
    cfg, env = write(tmp_path, "config.ini", CONFIG), write(
        tmp_path, ".env", "CERT_USER=u\nCERT_PASSWORD=p\nCERT_WORKERS=500\n"
    )
    with pytest.raises(ConfigError, match="100"):
        load_settings(cfg, env)


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
