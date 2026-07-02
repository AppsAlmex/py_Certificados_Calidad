"""Controlador: media entre la GUI y el nucleo de negocio.

La GUI nunca toca directamente el core; llama a este controlador. El
procesamiento corre en un hilo aparte para no congelar la ventana (los reportes
pueden tardar mucho) y los mensajes de log se envian a una ``queue`` que la GUI
consume de forma segura.
"""
from __future__ import annotations

import configparser
import logging
import queue
import threading
from pathlib import Path

from dotenv import dotenv_values

from certificados import (
    BatchProcessor,
    ConcurrentBatchProcessor,
    CSVReader,
    OracleReportClient,
    ResultLogger,
    build_default_validator,
    load_settings,
    save_config,
)


class QueueLogHandler(logging.Handler):
    """Handler de logging que empuja cada linea formateada a una cola."""

    def __init__(self, out_queue: "queue.Queue"):
        super().__init__()
        self._queue = out_queue

    def emit(self, record: logging.LogRecord) -> None:
        self._queue.put(("log", self.format(record)))


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class BatchController:
    """Fachada del nucleo para la GUI."""

    def __init__(self, config_path: str = "config.ini", env_path: str = ".env"):
        self.config_path = config_path
        self.env_path = env_path

    # -- lectura para poblar formularios (tolerante, sin exigir credenciales) --
    def read_raw(self) -> dict:
        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read(self.config_path, encoding="utf-8")
        env = dotenv_values(self.env_path)

        def get(section, option, fallback=""):
            return parser.get(section, option, fallback=fallback) if parser.has_section(section) else fallback

        reports = dict(parser.items("reports")) if parser.has_section("reports") else {}
        return {
            "host": get("service", "host"),
            "service_path": get("service", "service_path", "/xmlpserver/services/v2/ReportService"),
            "timeout": get("service", "timeout", "300"),
            "connect_timeout": get("service", "connect_timeout", "30"),
            "verify_ssl": _as_bool(get("service", "verify_ssl", "true")),
            "default_report": get("service", "default_report", next(iter(reports), "")),
            "reports": reports,
            "max_workers": get("batch", "max_workers", "1"),
            "output_dir": get("output", "output_dir", "output"),
            "log_dir": get("logging", "log_dir", "logs"),
            "log_level": get("logging", "log_level", "INFO"),
            "user": env.get("CERT_USER", "") or "",
            "password": env.get("CERT_PASSWORD", "") or "",
        }

    # -- persistencia (delegada al core) --------------------------------------
    def save(self, **values) -> None:
        save_config(self.config_path, self.env_path, **values)

    def validate_settings(self):
        """Carga Settings reales para confirmar que la config es usable."""
        return load_settings(self.config_path, self.env_path)

    # -- ejecucion en hilo ----------------------------------------------------
    def run_async(self, csv_path: str, report: str, workers: int, out_queue: "queue.Queue") -> None:
        handler = QueueLogHandler(out_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

        def task():
            try:
                settings = load_settings(
                    self.config_path, self.env_path, report=report or None, workers=workers
                )
                reader = CSVReader(csv_path)
                validator = build_default_validator()
                gateway = OracleReportClient(settings)
                with ResultLogger(settings.log_dir, settings.log_level, extra_handlers=[handler]) as logger:
                    if settings.max_workers > 1:
                        processor = ConcurrentBatchProcessor(
                            reader, validator, gateway, logger, max_workers=settings.max_workers
                        )
                    else:
                        processor = BatchProcessor(reader, validator, gateway, logger)
                    summary = processor.run()
                out_queue.put(("done", summary))
            except Exception as exc:  # todo error va a la GUI, no revienta el hilo
                out_queue.put(("error", exc))

        threading.Thread(target=task, name="batch-run", daemon=True).start()
