"""Ejecucion de UN solo reporte (refactor - Tarea 5).

Antes este archivo tenia credenciales, parametros y endpoint codificados.
Ahora:
  * la configuracion viene de config.ini + .env (no hay secretos en el codigo),
  * los parametros se pasan como un objeto ``ReportRequest`` (no dependen de CSV),
  * la ejecucion/guardado la hace ``OracleReportClient`` (reutilizable).

Sirve como ejemplo de uso del nucleo para una sola solicitud. Para carga masiva
usar ``main.py``.
"""
from __future__ import annotations

from certificados import OracleReportClient, ReportRequest, load_settings


def build_sample_request() -> ReportRequest:
    return ReportRequest(
        row_number=1,
        params={
            "P_EMBARQUE": "256436",
            "P_FORMATO": "1",
            "P_INSPECTOR": "003",
            "P_OBSERVACIONES": "",
            "P_PLANTA_PROD": "MARSHALL, MN",
            "P_TANQUE": "ADMX0106215_221209",
            "P_SELLO1": "951",
            "P_CANTIDAD1": "2",
            "P_SELLO2": "",
            "P_CANTIDAD2": "",
            "P_SELLO3": "",
            "P_CANTIDAD3": "",
            "P_SELLO4": "",
            "P_CANTIDAD4": "",
        },
        output_format="pdf",
    )


def run_single(request: ReportRequest, config_path: str = "config.ini", env_path: str = ".env"):
    """Reusable helper: run one request and return the ReportResult."""
    settings = load_settings(config_path, env_path)
    client = OracleReportClient(settings)
    return client.run_report(request)


if __name__ == "__main__":
    print("Ejecutando reporte...")
    result = run_single(build_sample_request())
    print(f"Archivo generado: {result.file_path} ({result.size_bytes} bytes)")
    print("Proceso terminado.")
