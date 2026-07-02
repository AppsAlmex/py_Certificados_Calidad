"""Entry point: bulk-run report requests from a CSV.

Usage:
    python main.py --csv templates/solicitudes_template.csv
    python main.py --csv datos.csv --config config.ini --env .env
"""
from __future__ import annotations

import argparse
import sys

from certificados import (
    BatchProcessor,
    CSVReader,
    OracleReportClient,
    ResultLogger,
    build_default_validator,
    load_settings,
)
from certificados.exceptions import CertificadoError


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecucion masiva de Certificados de Calidad")
    parser.add_argument("--csv", required=True, help="Ruta del archivo CSV de solicitudes")
    parser.add_argument("--config", default="config.ini", help="Ruta de config.ini")
    parser.add_argument("--env", default=".env", help="Ruta del archivo .env")
    parser.add_argument("--delimiter", default=",", help="Delimitador del CSV")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        settings = load_settings(args.config, args.env)
    except CertificadoError as exc:
        print(f"[CONFIG] {exc}", file=sys.stderr)
        return 2

    reader = CSVReader(args.csv, delimiter=args.delimiter)
    validator = build_default_validator()
    gateway = OracleReportClient(settings)

    with ResultLogger(settings.log_dir, settings.log_level) as logger:
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
