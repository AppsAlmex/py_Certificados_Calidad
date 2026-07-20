"""Tests de la logica de autoactualizacion (sin red real).

Cubre comparacion de versiones, resolucion de token y ``check_for_update`` con
respuestas HTTP simuladas (monkeypatch sobre requests.get).
"""
import pytest

from certificados import updater


# --- Comparacion de versiones ----------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("v1.2.0", (1, 2, 0)),
    ("1.0", (1, 0, 0)),
    ("v2.10.3", (2, 10, 3)),
    ("v1.2.0-beta", (1, 2, 0)),
    ("bad", (0, 0, 0)),
])
def test_parse(raw, expected):
    assert updater._parse(raw) == expected


@pytest.mark.parametrize("remote,local,newer", [
    ("v1.1.0", "1.0.0", True),
    ("v1.0.0", "1.0.0", False),
    ("v1.0.0", "1.2.0", False),
    ("v2.0.0", "1.9.9", True),
    ("v1.0.10", "1.0.9", True),
])
def test_is_newer(remote, local, newer):
    assert updater.is_newer(remote, local) is newer


# --- Token ------------------------------------------------------------------
def test_token_from_env(monkeypatch):
    monkeypatch.setenv("CERT_UPDATE_TOKEN", "  tok123  ")
    assert updater._get_token() == "tok123"


def test_token_absent(monkeypatch):
    monkeypatch.delenv("CERT_UPDATE_TOKEN", raising=False)
    # Sin env ni modulo bundleado -> None (el import interno falla y se ignora).
    assert updater._get_token() is None


def test_headers_with_and_without_token():
    with_tok = updater._headers("abc", "application/json")
    assert with_tok["Authorization"] == "Bearer abc"
    without = updater._headers(None, "application/json")
    assert "Authorization" not in without


# --- check_for_update (requests simulado) ----------------------------------
class _FakeResp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise updater.requests.HTTPError(f"HTTP {self.status_code}")


def _patch_get(monkeypatch, resp):
    monkeypatch.setattr(updater.requests, "get", lambda *a, **k: resp)


def test_check_no_update(monkeypatch):
    _patch_get(monkeypatch, _FakeResp(payload={"tag_name": "v0.0.1", "assets": []}))
    assert updater.check_for_update() is None


def test_check_new_version(monkeypatch):
    payload = {
        "tag_name": "v999.0.0",
        "body": "notas",
        "assets": [
            {"name": "otro.txt", "url": "u1", "size": 1},
            {"name": "CertificadosCalidad-abc.zip", "url": "u2", "size": 123},
        ],
    }
    _patch_get(monkeypatch, _FakeResp(payload=payload))
    info = updater.check_for_update()
    assert info is not None
    assert info.version == "999.0.0"
    assert info.asset_url == "u2"
    assert info.asset_size == 123


def test_check_new_version_but_no_zip(monkeypatch):
    payload = {"tag_name": "v999.0.0", "assets": [{"name": "app.exe", "url": "u", "size": 1}]}
    _patch_get(monkeypatch, _FakeResp(payload=payload))
    assert updater.check_for_update() is None


def test_check_401_raises(monkeypatch):
    _patch_get(monkeypatch, _FakeResp(status=401))
    with pytest.raises(RuntimeError, match="401"):
        updater.check_for_update()


def test_check_404_raises(monkeypatch):
    _patch_get(monkeypatch, _FakeResp(status=404))
    with pytest.raises(RuntimeError, match="404"):
        updater.check_for_update()


# --- Guardas de aplicacion en modo dev (no frozen) -------------------------
def test_download_and_apply_requires_frozen(monkeypatch):
    info = updater.UpdateInfo("1.0.0", "v1.0.0", "", "u", "a.zip", 1)
    monkeypatch.setattr(updater.sys, "frozen", False, raising=False)
    with pytest.raises(RuntimeError, match="compilado"):
        updater.download_and_apply(info)
