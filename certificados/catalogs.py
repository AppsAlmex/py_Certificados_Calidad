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
import io
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .exceptions import CatalogError


def _read_text(file: Path) -> str:
    """Lee el CSV tolerando codificacion: UTF-8 (con/sin BOM) o Windows-1252
    (cp1252, el default de Excel en espanol). Asi no se pierden acentos ni enes."""
    raw = file.read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


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
        reader = csv.DictReader(io.StringIO(_read_text(file)))
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
        text = _read_text(file)
    except OSError as exc:
        return [f"{file.name}: no se pudo leer ({exc})"]
    if "�" in text:
        issues.append(f"{file.name}: contiene caracteres perdidos (guardalo en UTF-8)")
    reader = csv.DictReader(io.StringIO(text))
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
    return issues
