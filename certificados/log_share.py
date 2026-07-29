"""Empaqueta los artefactos de una ejecución en un ZIP para compartir por correo.

Incluye los logs del run, el diagnóstico JSONL, el contexto y una copia de la
config SIN credenciales. El .env nunca se incluye.
"""
from __future__ import annotations

import configparser
import io
import zipfile
from pathlib import Path

from .logs import LogRun

_README = """Diagnostico de ejecucion - Certificados de Calidad
=====================================================

Archivos incluidos:
- resultados.csv      Una fila por solicitud (estado, formato, duracion, params, mensaje).
- ejecucion.log       Log de texto legible de la corrida.
- diagnostico.jsonl   Una linea JSON por fila con el detalle para analizar issues:
                        fila, estado, params, params_legibles, soap_request (SIN
                        credenciales), http_status, respuesta (fault/cuerpo solo en
                        error), respuesta_size, mensaje.
- contexto.txt        Version de la app, host, reporte, timeout, motor, workers, SO.
- config_saneado.ini  Copia de config.ini SIN usuario ni contrasena.

Como leer el JSONL: cada linea es un objeto JSON independiente. En Python:
    import json
    with open("diagnostico.jsonl", encoding="utf-8") as fh:
        filas = [json.loads(l) for l in fh]
"""


def _sanitize_config(config_path: str | Path) -> str:
    """Devuelve el texto de config.ini sin las claves user/password de [service]."""
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(config_path, encoding="utf-8")
    if parser.has_section("service"):
        for key in ("user", "password"):
            if parser.has_option("service", key):
                parser.remove_option("service", key)
    buf = io.StringIO()
    parser.write(buf)
    return buf.getvalue()


def build_share_zip(run: LogRun, dest_zip: str | Path, config_path: str | Path) -> Path:
    """Crea el ZIP con los artefactos del run + config saneada + LEEME.

    Los archivos ausentes del run se omiten y se anotan en el LEEME.
    """
    dest = Path(dest_zip)
    dest.parent.mkdir(parents=True, exist_ok=True)
    members = {
        "ejecucion.log": run.log_path,
        "resultados.csv": run.results_path,
        "diagnostico.jsonl": run.diagnostics_path,
        "contexto.txt": run.context_path,
    }
    faltantes: list[str] = []
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, path in members.items():
            if Path(path).exists():
                zf.write(path, arcname=arcname)
            else:
                faltantes.append(arcname)
        try:
            zf.writestr("config_saneado.ini", _sanitize_config(config_path))
        except OSError:
            faltantes.append("config_saneado.ini")
        readme = _README
        if faltantes:
            readme += "\nArchivos no encontrados en este run: " + ", ".join(faltantes) + "\n"
        zf.writestr("LEEME.txt", readme)
    return dest
