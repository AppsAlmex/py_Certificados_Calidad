"""Catalogos valor/descripcion configurables por CSV (SRP).

Cada campo con lista fija (formato, inspector, planta...) se alimenta de un CSV
con columnas ``valor`` y ``descripcion``. Este modulo solo lee esos CSV; quien
los muestra (la GUI) o los usa es responsabilidad de otra capa.

Formato del CSV:
    valor,descripcion
    1,Formato estandar
    2,Formato exportacion
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .exceptions import CatalogError


@dataclass(frozen=True)
class CatalogEntry:
    valor: str
    descripcion: str = ""

    @property
    def display(self) -> str:
        """Texto para mostrar en el combo: 'valor - descripcion'."""
        return f"{self.valor} - {self.descripcion}" if self.descripcion else self.valor


def load_catalog(path: str | Path) -> List[CatalogEntry]:
    """Lee un CSV valor/descripcion. Si el archivo no existe, devuelve [].

    Un archivo ausente no es error (el campo simplemente queda sin lista); un
    archivo presente pero sin columna ``valor`` si lo es.
    """
    file = Path(path)
    if not file.exists():
        return []
    try:
        with file.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            headers = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
            if "valor" not in headers:
                raise CatalogError(f"El catalogo {file} debe tener columna 'valor'")
            entries: List[CatalogEntry] = []
            for row in reader:
                norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
                valor = norm.get("valor", "")
                if not valor:
                    continue
                entries.append(CatalogEntry(valor, norm.get("descripcion", "")))
            return entries
    except OSError as exc:
        raise CatalogError(f"No se pudo leer el catalogo {file}: {exc}") from exc


def parse_valor(text: str) -> str:
    """Extrae el 'valor' de un texto 'valor - descripcion' (o lo devuelve tal cual)."""
    if not text:
        return ""
    return text.split(" - ", 1)[0].strip()


def validate_catalog(path: str | Path) -> List[str]:
    """Valida un CSV de catalogo y devuelve la lista de problemas (vacia = OK).

    Revisa: existe el archivo, tiene columna 'valor', sin valores vacios, sin
    valores duplicados, y al menos una fila valida.
    """
    file = Path(path)
    if not file.exists():
        return [f"{file.name}: no existe"]
    issues: List[str] = []
    try:
        with file.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            headers = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
            if "valor" not in headers:
                return [f"{file.name}: falta la columna 'valor'"]
            vistos: set = set()
            validas = 0
            for i, row in enumerate(reader, start=2):
                norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
                valor = norm.get("valor", "")
                if not valor:
                    issues.append(f"{file.name} fila {i}: valor vacio")
                    continue
                if valor in vistos:
                    issues.append(f"{file.name} fila {i}: valor duplicado '{valor}'")
                vistos.add(valor)
                validas += 1
            if validas == 0:
                issues.append(f"{file.name}: sin filas validas")
    except OSError as exc:
        issues.append(f"{file.name}: no se pudo leer ({exc})")
    return issues
