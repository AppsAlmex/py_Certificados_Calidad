"""Health checks generales de la app (un 'test entero' en caliente).

Cada chequeo devuelve un ``HealthResult(nombre, ok, detalle)``. Es solo lectura
salvo la prueba de carpeta escribible (crea/borra un archivo temporal). No lanza:
todo problema se reporta como un resultado con ok=False.
"""
from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .catalogs import validate_catalog
from .config import load_settings
from .exceptions import CertificadoError
from .pdf_renderer import available_local_formats

CATALOG_FIELDS = ("formato", "inspector", "planta_prod")


@dataclass
class HealthResult:
    nombre: str
    ok: bool
    detalle: str = ""


def run_health_checks(config_path="config.ini", env_path=".env",
                      check_connectivity: bool = True) -> List[HealthResult]:
    results: List[HealthResult] = []

    settings = None
    try:
        settings = load_settings(config_path, env_path)
        results.append(HealthResult(
            "Configuracion", True,
            f"reporte={settings.report_key}, motor={settings.pdf_engine}, workers={settings.max_workers}",
        ))
    except CertificadoError as exc:
        results.append(HealthResult("Configuracion", False, str(exc)))
    except Exception as exc:  # pragma: no cover - defensivo
        results.append(HealthResult("Configuracion", False, f"error inesperado: {exc}"))

    if settings is not None:
        ok = bool(settings.reports) and settings.report_key in settings.reports
        results.append(HealthResult(
            "Catalogo de reportes", ok,
            f"{len(settings.reports)} reporte(s); default={settings.report_key}",
        ))

    # Validacion de catalogos valor/descripcion (formato/inspector/planta).
    for nombre, issues in validate_configured_catalogs(config_path):
        results.append(HealthResult(f"Catalogo {nombre}", not issues,
                                    "; ".join(issues) if issues else "OK"))

    if settings is not None:
        for etiqueta, carpeta in (("salida", settings.output_dir), ("logs", settings.log_dir)):
            ok, detalle = _check_writable(carpeta)
            results.append(HealthResult(f"Carpeta {etiqueta}", ok, detalle))

        if settings.pdf_engine == "local":
            fmts = available_local_formats()
            results.append(HealthResult("Plantillas locales", bool(fmts),
                                        f"formatos: {', '.join(fmts) or 'ninguno'}"))
            results.append(_check_chromium())

        if check_connectivity:
            results.append(_check_connectivity(settings))

    return results


def validate_configured_catalogs(config_path="config.ini"):
    """Valida los catalogos definidos en [catalogs]. Devuelve [(campo, [issues])]."""
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(config_path, encoding="utf-8")
    base = parser.get("catalogs", "dir", fallback="catalogos") if parser.has_section("catalogs") else "catalogos"
    out = []
    for field in CATALOG_FIELDS:
        filename = (parser.get("catalogs", field, fallback=f"{field}.csv")
                    if parser.has_section("catalogs") else f"{field}.csv")
        out.append((field, validate_catalog(Path(base) / filename)))
    return out


def _check_writable(carpeta) -> tuple[bool, str]:
    try:
        d = Path(carpeta)
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".health_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True, f"escribible: {d}"
    except OSError as exc:
        return False, f"no escribible: {exc}"


def _check_chromium() -> HealthResult:
    import os

    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    candidatos = []
    if base:
        candidatos.append(Path(base))
    candidatos.append(Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright")
    for c in candidatos:
        try:
            if c and c.exists() and any(c.glob("chromium*")):
                return HealthResult("Chromium (motor local)", True, f"encontrado en {c}")
        except OSError:
            continue
    return HealthResult("Chromium (motor local)", False,
                        "no encontrado; corre 'playwright install chromium' o compila con -Chromium")


def _check_connectivity(settings) -> HealthResult:
    try:
        import requests

        connect = min(getattr(settings, "connect_timeout", 5) or 5, 5)
        resp = requests.get(settings.service_url, timeout=(connect, 10),
                            verify=settings.verify_ssl)
        ok = resp.status_code < 500
        return HealthResult("Conectividad servicio", ok, f"HTTP {resp.status_code} -> {settings.host}")
    except Exception as exc:
        return HealthResult("Conectividad servicio", False, f"{type(exc).__name__}: {exc}")
