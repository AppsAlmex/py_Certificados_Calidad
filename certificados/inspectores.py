"""Sincroniza el catalogo de inspectores desde el reporte Oracle (SRP).

El reporte ``XXALM_INSPECTORES_CALIDAD_RP`` devuelve (formato xml) una fila por
inspector:

    <G_XXALM_INSPECTORES_CALIDAD>
        <DESCRIPTION>Ricardo Campos</DESCRIPTION>
        <LOOKUP_CODE>001</LOOKUP_CODE>
    </G_XXALM_INSPECTORES_CALIDAD>

Mapeo:  ``LOOKUP_CODE`` -> valor (codigo) ,  ``DESCRIPTION`` -> descripcion (nombre).

Reglas del update (acordadas con el negocio):
  * El reporte es la FUENTE DE VERDAD: si un codigo ya existe y cambio el nombre,
    se toma el del reporte.
  * NUNCA se borran inspectores: un codigo que esta en el csv local pero no viene
    en el reporte se CONSERVA tal cual.
  * El csv se escribe en UTF-8, encabezado ``valor,descripcion``, ordenado por codigo.

Este modulo solo maneja data (parseo/fusion/escritura). Quien consulta a Oracle
(``OracleReportClient``) se inyecta ya configurado; la GUI/controlador orquestan.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from lxml import etree

from .catalogs import _read_text  # lectura tolerante a encoding (utf-8/cp1252)
from .executor import OracleReportClient
from .models import ReportRequest

# Clave del reporte en [reports] de config.ini. El reporte no lleva parametros.
INSPECTOR_REPORT_KEY = "XXALM_INSPECTORES_CALIDAD_RP"

_GROUP = "G_XXALM_INSPECTORES_CALIDAD"
_CODE = "LOOKUP_CODE"
_DESC = "DESCRIPTION"
CSV_HEADER = ("valor", "descripcion")

# Fila del catalogo: (codigo, nombre).
Row = Tuple[str, str]


@dataclass
class SyncResult:
    """Resumen de una sincronizacion (para mostrar en la GUI y decidir escritura)."""

    nuevos: List[Row] = field(default_factory=list)              # (codigo, nombre)
    cambiados: List[Tuple[str, str, str]] = field(default_factory=list)  # (codigo, antes, despues)
    conservados: List[Row] = field(default_factory=list)        # locales ausentes del reporte
    filas: List[Row] = field(default_factory=list)              # resultado final ya fusionado
    remoto_total: int = 0
    csv_path: Path | None = None

    @property
    def total(self) -> int:
        return len(self.filas)

    @property
    def cambios(self) -> int:
        """Cuantas filas realmente cambian (nuevas + modificadas)."""
        return len(self.nuevos) + len(self.cambiados)

    @property
    def sin_cambios(self) -> bool:
        return self.cambios == 0


def parse_inspectores(xml: bytes | str) -> List[Row]:
    """Extrae ``[(codigo, nombre), ...]`` del XML del reporte, ordenado por codigo.

    Si el reporte duplica un codigo, gana la ultima aparicion.
    """
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    root = etree.fromstring(xml)
    filas: Dict[str, str] = {}
    for g in root.iter(_GROUP):
        code = (g.findtext(_CODE) or "").strip()
        desc = (g.findtext(_DESC) or "").strip()
        if code:
            filas[code] = desc
    return sorted(filas.items(), key=lambda r: r[0])


def read_csv(csv_path: str | Path) -> List[Row]:
    """Lee el csv de inspectores como ``[(codigo, nombre), ...]``. Ausente -> []."""
    file = Path(csv_path)
    if not file.exists():
        return []
    reader = csv.DictReader(io.StringIO(_read_text(file)))
    out: List[Row] = []
    for row in reader:
        norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        valor = norm.get("valor", "")
        if valor:
            out.append((valor, norm.get("descripcion", "")))
    return out


def merge(local: List[Row], remoto: List[Row]) -> SyncResult:
    """Funde ``local`` + ``remoto`` segun las reglas del negocio.

    Reporte manda en conflictos; los codigos solo-locales se conservan; nada se
    borra. El resultado (``result.filas``) queda ordenado por codigo.
    """
    local_map = dict(local)
    remoto_map = dict(remoto)
    result = SyncResult(remoto_total=len(remoto_map))
    final: Dict[str, str] = dict(local_map)  # arranca de lo local (no se pierde nada)

    for code, nombre in remoto:
        if code not in local_map:
            result.nuevos.append((code, nombre))
        elif local_map[code] != nombre:
            result.cambiados.append((code, local_map[code], nombre))
        final[code] = nombre  # el reporte es la fuente de verdad

    for code, nombre in local:
        if code not in remoto_map:
            result.conservados.append((code, nombre))  # ya presente en final

    result.filas = sorted(final.items(), key=lambda r: r[0])
    return result


def write_csv(csv_path: str | Path, filas: List[Row]) -> None:
    """Escribe el csv en UTF-8 con encabezado ``valor,descripcion``."""
    file = Path(csv_path)
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_HEADER)
        writer.writerows(filas)


def create_default_csv(csv_path: str | Path, overwrite: bool = False) -> bool:
    """Crea el csv por defecto (solo encabezado, SIN datos).

    Pensado para cuando el usuario borra el archivo. Si ya existe y
    ``overwrite=False`` no hace nada y devuelve ``False``; si lo crea, ``True``.
    """
    file = Path(csv_path)
    if file.exists() and not overwrite:
        return False
    write_csv(file, [])
    return True


def fetch_inspectores(settings) -> List[Row]:
    """Consulta el reporte (xml) y devuelve ``[(codigo, nombre), ...]``.

    ``settings`` debe venir cargado con ``report=INSPECTOR_REPORT_KEY``.
    """
    client = OracleReportClient(settings)
    request = ReportRequest(row_number=1, params={}, output_format="xml")
    xml = client.fetch_bytes(request)
    return parse_inspectores(xml)


def sync_inspectores(settings, csv_path: str | Path, apply: bool = False) -> SyncResult:
    """Consulta el reporte, fusiona con el csv local y (si ``apply``) lo escribe.

    Con ``apply=False`` solo calcula el resultado (para previsualizar/confirmar en
    la GUI) sin tocar el disco.
    """
    remoto = fetch_inspectores(settings)
    local = read_csv(csv_path)
    result = merge(local, remoto)
    result.csv_path = Path(csv_path)
    if apply:
        write_csv(csv_path, result.filas)
    return result
