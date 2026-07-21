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
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

from certificados import (
    BatchProcessor,
    ConcurrentBatchProcessor,
    CSVReader,
    ResultLogger,
    available_local_formats,
    build_default_validator,
    build_gateway,
    execute_and_log,
    load_catalog,
    load_settings,
    save_config,
)
from certificados.logs import list_runs, read_log_text, read_results
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


def _run_context(settings, origen: str) -> dict:
    """Contexto de la corrida que se guarda en los logs (para saber que se uso)."""
    return {
        "reporte": settings.report_key,
        "workers": settings.max_workers,
        "timeout": settings.timeout,
        "origen": origen,
    }


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
            "pdf_engine": get("pdf", "engine", "oracle"),
            "pdf_page_format": get("pdf", "page_format", "Letter"),
            "output_dir": get("output", "output_dir", "output"),
            "log_dir": get("logging", "log_dir", "logs"),
            "log_level": get("logging", "log_level", "INFO"),
            "user": env.get("CERT_USER", "") or "",
            "password": env.get("CERT_PASSWORD", "") or "",
        }

    def local_formats(self) -> list:
        """Formatos con plantilla local (para poblar el combo cuando engine=local)."""
        return available_local_formats()

    def run_health_checks(self, check_connectivity: bool = True):
        """Corre el test entero de la app (config, catalogos, carpetas, red...)."""
        from certificados.health import run_health_checks
        return run_health_checks(self.config_path, self.env_path, check_connectivity)

    def validate_catalogs(self):
        """Valida los catalogos configurados. Devuelve [(campo, [problemas])]."""
        from certificados.health import validate_configured_catalogs
        return validate_configured_catalogs(self.config_path)

    def list_docs(self):
        """Lista los documentos de ayuda (.md/.txt) para la pestana Info."""
        from certificados.runtime import docs_dir
        d = docs_dir()
        if not d.exists():
            return []
        return sorted(list(d.glob("*.md")) + list(d.glob("*.txt")))

    def read_doc(self, path) -> str:
        return Path(path).read_text(encoding="utf-8", errors="replace")

    # -- generacion de etiqueta PDF (3x2") ------------------------------------
    def generate_label(self, campos: dict) -> Path:
        """Genera el PDF de una etiqueta con los datos del formulario y lo guarda
        en la carpeta de salida. Devuelve la ruta del PDF creado."""
        from certificados.labels import LabelData, render_label_pdf

        data = LabelData(**campos)
        pdf = render_label_pdf(data)

        out_dir = Path(self.read_raw()["output_dir"] or "output")
        out_dir.mkdir(parents=True, exist_ok=True)
        lote = re.sub(r"[^A-Za-z0-9._-]", "_", data.lote.strip()) or "etiqueta"
        path = out_dir / f"etiqueta_{lote}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        path.write_bytes(pdf)
        return path

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

    # -- lectura de logs ------------------------------------------------------
    def read_runs(self):
        """Lista de ejecuciones previas (mas recientes primero)."""
        log_dir = self.read_raw()["log_dir"]
        return list_runs(log_dir)

    def read_run_results(self, results_path):
        return read_results(results_path)

    def read_run_log(self, log_path):
        return read_log_text(log_path)

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
    def run_async(self, csv_path: str, report: str, workers: int, out_queue: "queue.Queue",
                  engine: str | None = None) -> None:
        handler = self._make_handler(out_queue)
        self._cancel_event = threading.Event()
        cancel_event = self._cancel_event

        def task():
            try:
                settings = load_settings(
                    self.config_path, self.env_path, report=report or None,
                    workers=workers, pdf_engine=engine,
                )
                reader = CSVReader(csv_path)
                validator = build_default_validator()
                gateway = build_gateway(settings)
                context = _run_context(settings, origen=f"CSV:{csv_path}")
                with ResultLogger(settings.log_dir, settings.log_level,
                                  extra_handlers=[handler], context=context) as logger:
                    if settings.max_workers > 1:
                        processor = ConcurrentBatchProcessor(
                            reader, validator, gateway, logger, max_workers=settings.max_workers
                        )
                    else:
                        processor = BatchProcessor(reader, validator, gateway, logger)
                    on_progress = lambda done, total: out_queue.put(("progress", done, total))
                    summary = processor.run(cancel_event=cancel_event, on_progress=on_progress)
                out_queue.put(("done", summary))
            except Exception as exc:  # todo error va a la GUI, no revienta el hilo
                out_queue.put(("error", exc))

        threading.Thread(target=task, name="batch-run", daemon=True).start()

    # -- procesamiento de solicitudes individuales (pestana de 1 en 1) --------
    def process_requests_async(self, items, out_queue: "queue.Queue",
                               report: str | None = None, workers: int = 1,
                               engine: str | None = None) -> None:
        """Procesa una lista de (item_id, ReportRequest) reportando estado por item.

        Tiene paridad con el batch: elige ``report`` y ``workers``. Emite
        ("item", item_id, estado, detalle) por cada uno y ("done", summary) al
        final. Respeta la cancelacion y reutiliza el mismo validador/ejecutor que
        el batch para comportamiento identico. La unica diferencia con la
        ejecucion por CSV es el origen de los datos (formulario vs archivo).
        """
        handler = self._make_handler(out_queue)
        self._cancel_event = threading.Event()
        cancel_event = self._cancel_event

        def task():
            try:
                settings = load_settings(
                    self.config_path, self.env_path, report=report or None,
                    workers=workers, pdf_engine=engine,
                )
                validator = build_default_validator()
                gateway = build_gateway(settings)
                summary = BatchSummary(total=len(items))
                context = _run_context(settings, origen="Formulario individual")
                with ResultLogger(settings.log_dir, settings.log_level,
                                  extra_handlers=[handler], context=context) as logger:
                    total = len(items)
                    progress = {"done": 0}

                    def bump():
                        progress["done"] += 1
                        out_queue.put(("progress", progress["done"], total))

                    # Validacion secuencial (barata); las validas van al ejecutor.
                    valid = []
                    for item_id, request in items:
                        result = validator.validate(request)
                        if result.valid:
                            valid.append((item_id, request))
                        else:
                            detail = "; ".join(str(i) for i in result.issues)
                            logger.log_invalid(request, result.issues, 0.0)
                            out_queue.put(("item", item_id, "INVALIDO", detail))
                            summary.invalid += 1
                            bump()

                    def work(pair):
                        item_id, request = pair
                        if cancel_event.is_set():
                            return item_id, None
                        out_queue.put(("item", item_id, "Procesando", ""))
                        return item_id, execute_and_log(gateway, logger, request)

                    def account(item_id, outcome):
                        if outcome is None:
                            summary.cancelled = True
                        elif outcome:
                            out_queue.put(("item", item_id, "OK", ""))
                            summary.success += 1
                        else:
                            out_queue.put(("item", item_id, "ERROR", ""))
                            summary.failed += 1
                        bump()

                    if settings.max_workers > 1:
                        with ThreadPoolExecutor(max_workers=settings.max_workers) as pool:
                            for item_id, outcome in pool.map(work, valid):
                                account(item_id, outcome)
                    else:
                        for pair in valid:
                            item_id, outcome = work(pair)
                            account(item_id, outcome)

                    logger.summary(summary)
                out_queue.put(("done", summary))
            except Exception as exc:
                out_queue.put(("error", exc))

        threading.Thread(target=task, name="single-run", daemon=True).start()
