"""Bulk processing engine (Tarea 6).

Orchestrates the pipeline: read -> validate -> execute -> log. A failure on one
row (invalid data, auth, connection, save) is captured and logged; processing
continues with the next row. Returns a ``BatchSummary``.

Depends only on abstractions (reader/validator/gateway/logger duck types), so any
piece can be swapped without touching this class.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .csv_reader import CSVReader
from .exceptions import CertificadoError
from .models import BatchSummary
from .result_logger import ResultLogger
from .validators import RequestValidator


def execute_and_log(gateway, logger: ResultLogger, request) -> bool:
    """Ejecuta una solicitud ya validada y registra el resultado.

    Compartido por el procesador secuencial, el concurrente y el procesamiento
    individual de la GUI, para que todos tengan EXACTAMENTE el mismo
    comportamiento por fila. Devuelve True si OK.
    """
    start = time.perf_counter()
    try:
        report = gateway.run_report(request)
        logger.log_success(report, time.perf_counter() - start)
        return True
    except CertificadoError as exc:
        logger.log_failure(request, exc, time.perf_counter() - start)
        return False
    except Exception as exc:  # inesperado: registrar y continuar
        logger.log_failure(request, exc, time.perf_counter() - start)
        return False


def _cancelled(cancel_event) -> bool:
    return cancel_event is not None and cancel_event.is_set()


class BatchProcessor:
    def __init__(self, reader, validator: RequestValidator, gateway, logger: ResultLogger):
        self._reader = reader
        self._validator = validator
        self._gateway = gateway
        self._logger = logger

    def run(self, cancel_event=None, on_progress=None) -> BatchSummary:
        # A read error is fatal (no rows to process) and propagates to caller.
        requests = self._reader.read()
        total = len(requests)
        summary = BatchSummary(total=total)
        done = 0

        for request in requests:
            # Cancelacion cooperativa: se detiene antes de lanzar la siguiente fila.
            if _cancelled(cancel_event):
                summary.cancelled = True
                break

            start = time.perf_counter()
            result = self._validator.validate(request)
            if not result.valid:
                self._logger.log_invalid(request, result.issues, time.perf_counter() - start)
                summary.invalid += 1
            elif execute_and_log(self._gateway, self._logger, request):
                summary.success += 1
            else:
                summary.failed += 1

            done += 1
            if on_progress:
                on_progress(done, total)

        self._logger.summary(summary)
        return summary


class ConcurrentBatchProcessor:
    """Igual que ``BatchProcessor`` pero ejecuta N solicitudes en paralelo con
    hilos (Tarea 6, variante concurrente).

    Mismo contrato y mismo resultado por fila; solo cambia que varias peticiones
    a Oracle corren a la vez (ideal para reportes que tardan mucho). La validacion
    se hace primero de forma secuencial (barata) y solo las solicitudes validas
    se envian al pool. ``max_workers=1`` equivale al comportamiento secuencial.
    """

    def __init__(self, reader, validator: RequestValidator, gateway, logger: ResultLogger, max_workers: int = 4):
        self._reader = reader
        self._validator = validator
        self._gateway = gateway
        self._logger = logger
        self._max_workers = max(1, max_workers)

    def run(self, cancel_event=None, on_progress=None) -> BatchSummary:
        requests = self._reader.read()
        total = len(requests)
        summary = BatchSummary(total=total)
        done = 0

        valid = []
        for request in requests:
            result = self._validator.validate(request)
            if result.valid:
                valid.append(request)
            else:
                self._logger.log_invalid(request, result.issues, 0.0)
                summary.invalid += 1
                done += 1
                if on_progress:
                    on_progress(done, total)

        def guarded(req):
            # Tareas aun no iniciadas se saltan si ya se cancelo; las en vuelo terminan.
            if _cancelled(cancel_event):
                return None
            return execute_and_log(self._gateway, self._logger, req)

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {pool.submit(guarded, req): req for req in valid}
            for future in as_completed(futures):
                outcome = future.result()
                if outcome is None:
                    summary.cancelled = True
                elif outcome:
                    summary.success += 1
                else:
                    summary.failed += 1
                done += 1
                if on_progress:
                    on_progress(done, total)

        self._logger.summary(summary)
        return summary
