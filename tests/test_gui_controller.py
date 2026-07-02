"""Pruebas de la capa de presentacion que NO requieren abrir ventana.

Cubren el controlador (puente GUI<->core) y el handler de log a cola. La vista
Tkinter en si no se testea aqui (requiere display); su logica esta en el
controlador, que si es testeable.
"""
import logging
import queue

import pytest

from certificados.config import load_settings, save_config
from certificados.exceptions import ConfigError
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
