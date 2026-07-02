"""Result logging / traceability (Tarea 7).

Writes two things per run:
  * a human-readable ``.log`` (standard ``logging``),
  * a machine-readable ``resultados_*.csv`` with one row per request.

Each entry records timestamp, row, params, status, duration and error message.
"""
from __future__ import annotations

import csv
import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import ReportRequest, ReportResult
from .validators import ValidationIssue

_CSV_HEADER = [
    "timestamp",
    "fila",
    "estado",
    "formato",
    "duracion_seg",
    "archivo",
    "parametros",
    "mensaje",
]


class ResultLogger:
    """Records the outcome of each request. One instance per batch run."""

    def __init__(self, log_dir: str | Path, level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        # Protege la escritura del CSV cuando varios hilos registran a la vez.
        self._lock = threading.Lock()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.results_path = self.log_dir / f"resultados_{stamp}.csv"
        self._results_file = self.results_path.open("w", encoding="utf-8", newline="")
        self._writer = csv.writer(self._results_file)
        self._writer.writerow(_CSV_HEADER)

        # Unique name so concurrent/consecutive runs never share handlers.
        self._logger = logging.getLogger(f"certificados.{stamp}.{uuid.uuid4().hex[:8]}")
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._logger.propagate = False
        if not self._logger.handlers:
            fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            file_handler = logging.FileHandler(self.log_dir / f"ejecucion_{stamp}.log", encoding="utf-8")
            file_handler.setFormatter(fmt)
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(fmt)
            self._logger.addHandler(file_handler)
            self._logger.addHandler(stream_handler)

    # -- events -------------------------------------------------------------
    def log_success(self, result: ReportResult, duration: float) -> None:
        req = result.request
        self._row(req, "OK", duration, str(result.file_path), "")
        self._logger.info(
            "Fila %s OK -> %s (%s bytes, %.2fs)",
            req.row_number, result.file_path.name, result.size_bytes, duration,
        )

    def log_failure(self, request: ReportRequest, error: Exception, duration: float) -> None:
        self._row(request, "ERROR", duration, "", str(error))
        self._logger.error("Fila %s ERROR (%.2fs): %s", request.row_number, duration, error)

    def log_invalid(self, request: ReportRequest, issues: Iterable[ValidationIssue], duration: float) -> None:
        message = "; ".join(str(i) for i in issues)
        self._row(request, "INVALIDO", duration, "", message)
        self._logger.warning("Fila %s INVALIDO: %s", request.row_number, message)

    def summary(self, summary) -> None:
        self._logger.info("Resumen: %s", summary)

    # -- infra --------------------------------------------------------------
    def _row(self, request: ReportRequest, status: str, duration: float, archivo: str, message: str) -> None:
        with self._lock:
            self._writer.writerow(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    request.row_number,
                    status,
                    request.output_format,
                    f"{duration:.2f}",
                    archivo,
                    json.dumps(request.params, ensure_ascii=False),
                    message,
                ]
            )
            self._results_file.flush()

    def close(self) -> None:
        if not self._results_file.closed:
            self._results_file.close()
        for handler in list(self._logger.handlers):
            handler.close()
            self._logger.removeHandler(handler)

    def __enter__(self) -> "ResultLogger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
