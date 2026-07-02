"""CSV reader (Tarea 3, Single Responsibility Principle).

This component does ONE thing: turn a CSV file into a list of ``ReportRequest``.
It does NOT validate business rules (that is the Validator's job) and it does NOT
execute anything. It only fails on problems that stop reading: file missing or
headers wrong.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from .exceptions import CSVReadError
from .models import ReportRequest

# CSV column -> Oracle report parameter. Add a row here to expose a new column.
PARAM_COLUMNS = {
    "embarque": "P_EMBARQUE",
    "formato": "P_FORMATO",
    "inspector": "P_INSPECTOR",
    "observaciones": "P_OBSERVACIONES",
    "planta_prod": "P_PLANTA_PROD",
    "tanque": "P_TANQUE",
    "sello1": "P_SELLO1",
    "cantidad1": "P_CANTIDAD1",
    "sello2": "P_SELLO2",
    "cantidad2": "P_CANTIDAD2",
    "sello3": "P_SELLO3",
    "cantidad3": "P_CANTIDAD3",
    "sello4": "P_SELLO4",
    "cantidad4": "P_CANTIDAD4",
}
FORMAT_COLUMN = "formato_salida"
NAME_COLUMN = "nombre_archivo"

# Columns that must exist in the header. Optional data (empty cells) is allowed;
# a missing *column* is a structural error.
REQUIRED_HEADERS = set(PARAM_COLUMNS) | {FORMAT_COLUMN}


class CSVReader:
    """Reads a delimited file and yields one ``ReportRequest`` per data row."""

    def __init__(self, path: str | Path, delimiter: str = ",", encoding: str = "utf-8-sig"):
        self.path = Path(path)
        self.delimiter = delimiter
        self.encoding = encoding

    def read(self) -> List[ReportRequest]:
        try:
            with self.path.open("r", encoding=self.encoding, newline="") as fh:
                reader = csv.DictReader(fh, delimiter=self.delimiter)
                headers = reader.fieldnames
                self._check_headers(headers)
                requests = [
                    self._to_request(row, index)
                    # header is line 1; first data row is line 2
                    for index, row in enumerate(reader, start=2)
                ]
        except FileNotFoundError as exc:
            raise CSVReadError(f"Archivo CSV no encontrado: {self.path}") from exc
        except UnicodeDecodeError as exc:
            raise CSVReadError(f"Codificacion invalida en {self.path}: {exc}") from exc
        except OSError as exc:
            raise CSVReadError(f"No se pudo leer {self.path}: {exc}") from exc

        if not requests:
            raise CSVReadError("El CSV no contiene filas de datos")
        return requests

    def _check_headers(self, headers) -> None:
        if not headers:
            raise CSVReadError("El CSV no tiene encabezados")
        present = {h.strip() for h in headers if h}
        missing = REQUIRED_HEADERS - present
        if missing:
            raise CSVReadError(
                "Faltan columnas obligatorias: " + ", ".join(sorted(missing))
            )

    def _to_request(self, row: dict, row_number: int) -> ReportRequest:
        params = {
            param: (row.get(col) or "").strip()
            for col, param in PARAM_COLUMNS.items()
        }
        output_format = (row.get(FORMAT_COLUMN) or "pdf").strip().lower() or "pdf"
        output_name = (row.get(NAME_COLUMN) or "").strip() or None
        return ReportRequest(
            row_number=row_number,
            params=params,
            output_format=output_format,
            output_name=output_name,
        )
