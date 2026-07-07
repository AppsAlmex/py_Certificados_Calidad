"""Entry point: bulk-run report requests from a CSV.

Usage:
    python main.py --csv templates/solicitudes_template.csv
    python main.py --csv datos.csv --config config.ini --env .env
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):  # compilado: trabajar junto al .exe
    _base = Path(sys.executable).resolve().parent
    os.chdir(_base)
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(_base / "ms-playwright"))

from certificados import (
    BatchProcessor,
    ConcurrentBatchProcessor,
    CSVReader,
    ResultLogger,
    build_default_validator,
    build_gateway,
    load_settings,
)
from certificados.exceptions import CertificadoError


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecucion masiva de Certificados de Calidad")
    parser.add_argument("--csv", required=True, help="Ruta del archivo CSV de solicitudes")
    parser.add_argument("--config", default="config.ini", help="Ruta de config.ini")
    parser.add_argument("--env", default=".env", help="Ruta del archivo .env")
    parser.add_argument("--delimiter", default=",", help="Delimitador del CSV")
    parser.add_argument("--report", default=None, help="Clave del reporte a consumir (override de CERT_REPORT)")
    parser.add_argument("--timeout", type=int, default=None, help="Read timeout en segundos (override de CERT_TIMEOUT)")
    parser.add_argument("--workers", type=int, default=None, help="Hilos concurrentes (override de CERT_WORKERS; 1 = secuencial)")
    parser.add_argument("--engine", choices=["oracle", "local"], default=None,
                        help="Motor de PDF (override de config): oracle = BI Publisher, local = plantilla HTML")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        settings = load_settings(
            args.config, args.env, report=args.report, timeout=args.timeout,
            workers=args.workers, pdf_engine=args.engine,
        )
    except CertificadoError as exc:
        print(f"[CONFIG] {exc}", file=sys.stderr)
        return 2

    print(f"Reporte: {settings.report_key} -> {settings.report_path}")
    print(f"Timeout: connect={settings.connect_timeout}s read={settings.timeout}s")
    print(f"Workers: {settings.max_workers} | Motor PDF: {settings.pdf_engine}")

    reader = CSVReader(args.csv, delimiter=args.delimiter)
    validator = build_default_validator()
    gateway = build_gateway(settings)

    context = {
        "reporte": settings.report_key,
        "workers": settings.max_workers,
        "timeout": settings.timeout,
        "origen": f"CSV:{args.csv}",
    }
    with ResultLogger(settings.log_dir, settings.log_level, context=context) as logger:
        # 1 worker = secuencial (comportamiento original); >1 = concurrente.
        if settings.max_workers > 1:
            processor = ConcurrentBatchProcessor(
                reader, validator, gateway, logger, max_workers=settings.max_workers
            )
        else:
            processor = BatchProcessor(reader, validator, gateway, logger)
        try:
            summary = processor.run()
        except CertificadoError as exc:
            print(f"[FATAL] {exc}", file=sys.stderr)
            return 1

    print(f"Proceso terminado. {summary}")
    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
