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
    execute_and_log,
    load_catalog,
    load_settings,
    save_config,
)
from certificados.models import BatchSummary

# Campos del formulario que se alimentan de un catalogo valor/descripcion.
CATALOG_FIELDS = ("formato", "inspector", "planta_prod")


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
        self._cancel_event: threading.Event | None = None

    # -- cancelacion ----------------------------------------------------------
    def cancel(self) -> None:
        """Solicita detener el proceso en curso (cancelacion cooperativa).

        No lanza nada si no hay proceso. La peticion en vuelo termina; no se
        lanzan mas. Un unico reporte muy largo NO se aborta a la fuerza.
        """
        if self._cancel_event is not None:
            self._cancel_event.set()

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

    def read_catalogs(self) -> dict:
        """Carga los catalogos valor/descripcion definidos en [catalogs].

        Devuelve {campo: [CatalogEntry, ...]}. Archivos ausentes -> lista vacia.
        """
        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read(self.config_path, encoding="utf-8")
        base = parser.get("catalogs", "dir", fallback="catalogos") if parser.has_section("catalogs") else "catalogos"
        result = {}
        for field in CATALOG_FIELDS:
            filename = parser.get("catalogs", field, fallback=f"{field}.csv") if parser.has_section("catalogs") else f"{field}.csv"
            result[field] = load_catalog(Path(base) / filename)
        return result

    # -- persistencia (delegada al core) --------------------------------------
    def save(self, **values) -> None:
        save_config(self.config_path, self.env_path, **values)

    def validate_settings(self):
        """Carga Settings reales para confirmar que la config es usable."""
        return load_settings(self.config_path, self.env_path)

    def _make_handler(self, out_queue: "queue.Queue") -> QueueLogHandler:
        handler = QueueLogHandler(out_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        return handler

    # -- ejecucion masiva desde CSV, en hilo ----------------------------------
    def run_async(self, csv_path: str, report: str, workers: int, out_queue: "queue.Queue") -> None:
        handler = self._make_handler(out_queue)
        self._cancel_event = threading.Event()
        cancel_event = self._cancel_event

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
                    summary = processor.run(cancel_event=cancel_event)
                out_queue.put(("done", summary))
            except Exception as exc:  # todo error va a la GUI, no revienta el hilo
                out_queue.put(("error", exc))

        threading.Thread(target=task, name="batch-run", daemon=True).start()

    # -- procesamiento de solicitudes individuales (pestana de 1 en 1) --------
    def process_requests_async(self, items, out_queue: "queue.Queue") -> None:
        """Procesa una lista de (item_id, ReportRequest) reportando estado por item.

        Emite ("item", item_id, estado, detalle) por cada uno y ("done", summary)
        al final. Respeta la cancelacion. Reutiliza el mismo validador/ejecutor
        que el batch para comportamiento identico.
        """
        handler = self._make_handler(out_queue)
        self._cancel_event = threading.Event()
        cancel_event = self._cancel_event

        def task():
            try:
                settings = load_settings(self.config_path, self.env_path)
                validator = build_default_validator()
                gateway = OracleReportClient(settings)
                summary = BatchSummary(total=len(items))
                with ResultLogger(settings.log_dir, settings.log_level, extra_handlers=[handler]) as logger:
                    for item_id, request in items:
                        if cancel_event.is_set():
                            summary.cancelled = True
                            break
                        out_queue.put(("item", item_id, "Procesando", ""))
                        result = validator.validate(request)
                        if not result.valid:
                            detail = "; ".join(str(i) for i in result.issues)
                            logger.log_invalid(request, result.issues, 0.0)
                            out_queue.put(("item", item_id, "INVALIDO", detail))
                            summary.invalid += 1
                            continue
                        if execute_and_log(gateway, logger, request):
                            out_queue.put(("item", item_id, "OK", ""))
                            summary.success += 1
                        else:
                            out_queue.put(("item", item_id, "ERROR", ""))
                            summary.failed += 1
                    logger.summary(summary)
                out_queue.put(("done", summary))
            except Exception as exc:
                out_queue.put(("error", exc))

        threading.Thread(target=task, name="single-run", daemon=True).start()
