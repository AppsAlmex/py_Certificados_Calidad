"""Bulk processing engine (Tarea 6).

Orchestrates the pipeline: read -> validate -> execute -> log. A failure on one
row (invalid data, auth, connection, save) is captured and logged; processing
continues with the next row. Returns a ``BatchSummary``.

Depends only on abstractions (reader/validator/gateway/logger duck types), so any
piece can be swapped without touching this class.
"""
from __future__ import annotations

import time

from .csv_reader import CSVReader
from .exceptions import CertificadoError
from .models import BatchSummary
from .result_logger import ResultLogger
from .validators import RequestValidator


class BatchProcessor:
    def __init__(self, reader, validator: RequestValidator, gateway, logger: ResultLogger):
        self._reader = reader
        self._validator = validator
        self._gateway = gateway
        self._logger = logger

    def run(self) -> BatchSummary:
        # A read error is fatal (no rows to process) and propagates to caller.
        requests = self._reader.read()
        summary = BatchSummary(total=len(requests))

        for request in requests:
            start = time.perf_counter()
            result = self._validator.validate(request)
            if not result.valid:
                self._logger.log_invalid(request, result.issues, time.perf_counter() - start)
                summary.invalid += 1
                continue

            try:
                report = self._gateway.run_report(request)
                self._logger.log_success(report, time.perf_counter() - start)
                summary.success += 1
            except CertificadoError as exc:
                self._logger.log_failure(request, exc, time.perf_counter() - start)
                summary.failed += 1
            except Exception as exc:  # unexpected: log, keep going
                self._logger.log_failure(request, exc, time.perf_counter() - start)
                summary.failed += 1

        self._logger.summary(summary)
        return summary
