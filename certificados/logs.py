"""Lectura de logs de ejecuciones previas (reporting).

Cada corrida deja dos archivos en la carpeta de logs:
  * ``resultados_<stamp>.csv`` — una fila por solicitud (estructurado).
  * ``ejecucion_<stamp>.log``  — log de texto legible.

Este modulo solo LEE esos archivos y los resume; mostrarlos es tarea de la GUI.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

RESULT_PREFIX = "resultados_"
LOG_PREFIX = "ejecucion_"


@dataclass
class LogRun:
    """Resumen de una ejecucion (un par resultados/ejecucion)."""

    results_path: Path
    fecha: str
    total: int = 0
    ok: int = 0
    error: int = 0
    invalido: int = 0

    @property
    def log_path(self) -> Path:
        stamp = self.results_path.stem[len(RESULT_PREFIX):]
        return self.results_path.parent / f"{LOG_PREFIX}{stamp}.log"


def _format_stamp(results_path: Path) -> str:
    stamp = results_path.stem[len(RESULT_PREFIX):]
    try:
        return datetime.strptime(stamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return stamp


def read_results(path: str | Path) -> List[dict]:
    """Devuelve las filas del CSV de resultados como lista de dicts."""
    file = Path(path)
    if not file.exists():
        return []
    with file.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_log_text(path: str | Path) -> str:
    """Devuelve el contenido del log de texto (o cadena vacia si no existe)."""
    file = Path(path)
    if not file.exists():
        return ""
    return file.read_text(encoding="utf-8", errors="replace")


def list_runs(log_dir: str | Path) -> List[LogRun]:
    """Lista las ejecuciones (mas recientes primero) con sus conteos por estado."""
    directory = Path(log_dir)
    if not directory.exists():
        return []
    runs: List[LogRun] = []
    for results_file in sorted(directory.glob(f"{RESULT_PREFIX}*.csv"), reverse=True):
        rows = read_results(results_file)
        counts = {"OK": 0, "ERROR": 0, "INVALIDO": 0}
        for row in rows:
            estado = (row.get("estado") or "").strip().upper()
            if estado in counts:
                counts[estado] += 1
        runs.append(
            LogRun(
                results_path=results_file,
                fecha=_format_stamp(results_file),
                total=len(rows),
                ok=counts["OK"],
                error=counts["ERROR"],
                invalido=counts["INVALIDO"],
            )
        )
    return runs
