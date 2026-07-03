"""Pruebas de la capa de presentacion que NO requieren abrir ventana.

Cubren el controlador (puente GUI<->core) y el handler de log a cola. La vista
Tkinter en si no se testea aqui (requiere display); su logica esta en el
controlador, que si es testeable.
"""
import logging
import queue
import time
from pathlib import Path

import pytest

import gui.controller as ctrl_mod
from certificados.config import load_settings, save_config
from certificados.exceptions import ConfigError
from certificados.models import ReportRequest, ReportResult
from gui.controller import BatchController, QueueLogHandler


def _write(tmp_path):
    cfg = tmp_path / "config.ini"
    env = tmp_path / ".env"
    save_config(
        cfg, env,
        host="https://h.test", service_path="/svc",
        timeout=5400, connect_timeout=20, verify_ssl=True,
        default_report="alpha", reports={"alpha": "/A.xdo", "beta": "/B.xdo"},
        max_workers=3, output_dir="out", log_dir="lg", log_level="INFO",
        user="u", password="p",
    )
    return cfg, env


def test_save_config_round_trip(tmp_path):
    cfg, env = _write(tmp_path)
    s = load_settings(cfg, env)
    assert s.host == "https://h.test"
    assert s.timeout == 5400
    assert s.connect_timeout == 20
    assert s.max_workers == 3
    assert s.verify_ssl is True
    assert s.report_key == "alpha"
    assert s.reports == {"alpha": "/A.xdo", "beta": "/B.xdo"}
    assert s.user == "u"
    assert s.password == "p"


def test_save_config_bad_default_report(tmp_path):
    cfg, env = tmp_path / "c.ini", tmp_path / ".env"
    with pytest.raises(ConfigError, match="default_report"):
        save_config(
            cfg, env, host="h", service_path="/s", timeout=1, connect_timeout=1,
            verify_ssl=False, default_report="zzz", reports={"a": "/A.xdo"},
            max_workers=1, output_dir="o", log_dir="l", log_level="INFO",
        )


def test_read_raw_populates_form(tmp_path):
    cfg, env = _write(tmp_path)
    ctrl = BatchController(str(cfg), str(env))
    raw = ctrl.read_raw()
    assert raw["host"] == "https://h.test"
    assert raw["verify_ssl"] is True
    assert set(raw["reports"]) == {"alpha", "beta"}
    assert raw["default_report"] == "alpha"
    assert raw["user"] == "u"


def test_queue_log_handler_pushes_formatted():
    q: "queue.Queue" = queue.Queue()
    handler = QueueLogHandler(q)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hola", None, None)
    handler.emit(record)
    kind, payload = q.get_nowait()
    assert kind == "log"
    assert payload == "INFO hola"


def _drain_until_done(q, timeout=5):
    messages = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            msg = q.get(timeout=0.5)
        except queue.Empty:
            continue
        messages.append(msg)
        if msg[0] in ("done", "error"):
            break
    return messages


def test_process_requests_async(tmp_path, monkeypatch, settings):
    # Aisla del núcleo real: settings de prueba y cliente falso (sin red).
    monkeypatch.setattr(ctrl_mod, "load_settings", lambda *a, **k: settings)

    class FakeClient:
        def __init__(self, _settings):
            pass

        def run_report(self, request):
            return ReportResult(request, Path("x.pdf"), 5)

    monkeypatch.setattr(ctrl_mod, "build_gateway", lambda settings: FakeClient(settings))

    valid = ReportRequest(
        1,
        {"P_EMBARQUE": "100", "P_FORMATO": "1", "P_INSPECTOR": "3",
         "P_PLANTA_PROD": "P", "P_TANQUE": "T", "P_CANTIDAD1": "1"},
        output_format="pdf",
    )
    invalid = ReportRequest(2, {"P_EMBARQUE": ""}, output_format="pdf")

    q: "queue.Queue" = queue.Queue()
    BatchController().process_requests_async([("1", valid), ("2", invalid)], q)
    messages = _drain_until_done(q)

    assert ("item", "1", "OK", "") in messages
    assert any(m[0] == "item" and m[1] == "2" and m[2] == "INVALIDO" for m in messages)
    done = [m for m in messages if m[0] == "done"][0]
    summary = done[1]
    assert summary.success == 1
    assert summary.invalid == 1


def test_process_requests_concurrent(tmp_path, monkeypatch, settings):
    import dataclasses
    import threading

    # load_settings respeta el workers pedido (paridad con el batch).
    monkeypatch.setattr(
        ctrl_mod, "load_settings",
        lambda *a, **k: dataclasses.replace(settings, max_workers=k.get("workers") or 1),
    )

    lock = threading.Lock()
    state = {"active": 0, "max": 0}

    class FakeClient:
        def __init__(self, _settings):
            pass

        def run_report(self, request):
            with lock:
                state["active"] += 1
                state["max"] = max(state["max"], state["active"])
            time.sleep(0.1)
            with lock:
                state["active"] -= 1
            return ReportResult(request, Path("x.pdf"), 5)

    monkeypatch.setattr(ctrl_mod, "build_gateway", lambda settings: FakeClient(settings))

    def make(n):
        return ReportRequest(
            n, {"P_EMBARQUE": str(n), "P_FORMATO": "1", "P_INSPECTOR": "3",
                "P_PLANTA_PROD": "P", "P_TANQUE": "T", "P_CANTIDAD1": "1"},
            output_format="pdf",
        )

    items = [(str(n), make(n)) for n in range(1, 5)]
    q: "queue.Queue" = queue.Queue()
    BatchController().process_requests_async(items, q, report="alpha", workers=4)
    messages = _drain_until_done(q)

    done = [m for m in messages if m[0] == "done"][0]
    assert done[1].success == 4
    assert state["max"] >= 2  # corrieron en paralelo


def test_cancel_before_run_is_noop():
    # cancel() sin proceso activo no debe fallar.
    BatchController().cancel()


def test_read_catalogs(tmp_path):
    cfg, env = _write(tmp_path)
    # agrega seccion [catalogs] apuntando a un dir con un csv
    catdir = tmp_path / "cat"
    catdir.mkdir()
    (catdir / "inspector.csv").write_text("valor,descripcion\n003,Insp 003\n", encoding="utf-8")
    cfg.write_text(
        cfg.read_text(encoding="utf-8")
        + f"\n[catalogs]\ndir = {catdir.as_posix()}\ninspector = inspector.csv\n",
        encoding="utf-8",
    )
    cats = BatchController(str(cfg), str(env)).read_catalogs()
    assert [e.valor for e in cats["inspector"]] == ["003"]
    assert cats["formato"] == []  # archivo ausente -> vacio


def test_save_config_preserves_catalogs_section(tmp_path):
    cfg, env = _write(tmp_path)
    cfg.write_text(
        cfg.read_text(encoding="utf-8") + "\n[catalogs]\ndir = catalogos\nformato = formato.csv\n",
        encoding="utf-8",
    )
    # guardar de nuevo (como haria la GUI) no debe borrar [catalogs]
    save_config(
        cfg, env, host="h2", service_path="/s", timeout=10, connect_timeout=5,
        verify_ssl=True, default_report="alpha", reports={"alpha": "/A.xdo"},
        max_workers=2, output_dir="o", log_dir="l", log_level="INFO",
    )
    import configparser
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(cfg, encoding="utf-8")
    assert parser.has_section("catalogs")
    assert parser.get("catalogs", "formato") == "formato.csv"
    assert parser.get("service", "host") == "h2"  # sí actualizo lo editado
