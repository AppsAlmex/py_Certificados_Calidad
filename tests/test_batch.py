import threading
import time

from certificados.batch import BatchProcessor, ConcurrentBatchProcessor
from certificados.exceptions import ReportConnectionError
from certificados.models import ReportRequest, ReportResult
from certificados.result_logger import ResultLogger
from certificados.validators import build_default_validator


class FakeReader:
    def __init__(self, requests):
        self._requests = requests

    def read(self):
        return self._requests


class FakeGateway:
    def __init__(self, fail_rows=()):
        self.fail_rows = set(fail_rows)
        self.calls = []

    def run_report(self, request):
        self.calls.append(request.row_number)
        if request.row_number in self.fail_rows:
            raise ReportConnectionError("no network")
        from pathlib import Path
        return ReportResult(request, Path("fake.pdf"), 10)


def make_req(row, **override):
    params = {"P_EMBARQUE": str(row), "P_FORMATO": "1", "P_INSPECTOR": "3",
              "P_PLANTA_PROD": "P", "P_TANQUE": "T", "P_CANTIDAD1": "1"}
    params.update(override)
    return ReportRequest(row_number=row, params=params, output_format="pdf")


def test_all_valid(tmp_path):
    reader = FakeReader([make_req(2), make_req(3)])
    gateway = FakeGateway()
    with ResultLogger(tmp_path) as logger:
        summary = BatchProcessor(reader, build_default_validator(), gateway, logger).run()
    assert summary.total == 2
    assert summary.success == 2
    assert summary.failed == 0


def test_invalid_row_skipped_others_run(tmp_path):
    bad = make_req(2, P_EMBARQUE="")  # required field empty
    reader = FakeReader([bad, make_req(3)])
    gateway = FakeGateway()
    with ResultLogger(tmp_path) as logger:
        summary = BatchProcessor(reader, build_default_validator(), gateway, logger).run()
    assert summary.invalid == 1
    assert summary.success == 1
    assert gateway.calls == [3]  # invalid row never reached the gateway


def test_execution_error_does_not_stop_batch(tmp_path):
    reader = FakeReader([make_req(2), make_req(3), make_req(4)])
    gateway = FakeGateway(fail_rows={3})
    with ResultLogger(tmp_path) as logger:
        summary = BatchProcessor(reader, build_default_validator(), gateway, logger).run()
    assert summary.total == 3
    assert summary.success == 2
    assert summary.failed == 1
    assert gateway.calls == [2, 3, 4]  # all rows attempted


def test_results_csv_written(tmp_path):
    reader = FakeReader([make_req(2)])
    with ResultLogger(tmp_path) as logger:
        BatchProcessor(reader, build_default_validator(), FakeGateway(), logger).run()
        results_path = logger.results_path
    content = results_path.read_text(encoding="utf-8")
    assert "estado" in content
    assert "OK" in content


# --------------------------- concurrent processor ---------------------------

class SlowGateway:
    """Simula peticiones lentas y mide concurrencia real."""

    def __init__(self, delay=0.2, fail_rows=()):
        self.delay = delay
        self.fail_rows = set(fail_rows)
        self._lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.calls = []

    def run_report(self, request):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.calls.append(request.row_number)
        try:
            time.sleep(self.delay)
            if request.row_number in self.fail_rows:
                raise ReportConnectionError("no network")
            from pathlib import Path
            return ReportResult(request, Path("fake.pdf"), 10)
        finally:
            with self._lock:
                self.active -= 1


def test_concurrent_same_result_as_sequential(tmp_path):
    reqs = [make_req(r) for r in range(2, 7)]
    gateway = SlowGateway(delay=0.05, fail_rows={4})
    with ResultLogger(tmp_path) as logger:
        summary = ConcurrentBatchProcessor(
            FakeReader(reqs), build_default_validator(), gateway, logger, max_workers=4
        ).run()
    assert summary.total == 5
    assert summary.success == 4
    assert summary.failed == 1
    assert sorted(gateway.calls) == [2, 3, 4, 5, 6]  # all attempted


def test_concurrent_runs_in_parallel(tmp_path):
    reqs = [make_req(r) for r in range(2, 6)]  # 4 requests
    gateway = SlowGateway(delay=0.3)
    with ResultLogger(tmp_path) as logger:
        start = time.perf_counter()
        ConcurrentBatchProcessor(
            FakeReader(reqs), build_default_validator(), gateway, logger, max_workers=4
        ).run()
        elapsed = time.perf_counter() - start
    # 4 x 0.3s secuencial = 1.2s; en paralelo debe rondar 0.3s.
    assert gateway.max_active >= 2
    assert elapsed < 0.9


def test_concurrent_invalid_skipped(tmp_path):
    bad = make_req(2, P_EMBARQUE="")
    reqs = [bad, make_req(3), make_req(4)]
    gateway = SlowGateway(delay=0.01)
    with ResultLogger(tmp_path) as logger:
        summary = ConcurrentBatchProcessor(
            FakeReader(reqs), build_default_validator(), gateway, logger, max_workers=3
        ).run()
    assert summary.invalid == 1
    assert summary.success == 2
    assert 2 not in gateway.calls  # invalida nunca llega al gateway


class CancelAfterGateway:
    """Marca el evento de cancelacion tras N llamadas."""

    def __init__(self, event, after=1):
        self.event = event
        self.after = after
        self.calls = []

    def run_report(self, request):
        self.calls.append(request.row_number)
        if len(self.calls) >= self.after:
            self.event.set()
        from pathlib import Path
        return ReportResult(request, Path("x.pdf"), 1)


def test_sequential_cancellation(tmp_path):
    ev = threading.Event()
    reqs = [make_req(r) for r in range(2, 7)]
    gateway = CancelAfterGateway(ev, after=2)
    with ResultLogger(tmp_path) as logger:
        summary = BatchProcessor(
            FakeReader(reqs), build_default_validator(), gateway, logger
        ).run(cancel_event=ev)
    assert summary.cancelled is True
    assert summary.success == 2  # procesa 2, cancela antes de la 3a
    assert len(gateway.calls) == 2


def test_concurrent_cancellation_pre_set(tmp_path):
    ev = threading.Event()
    ev.set()
    reqs = [make_req(r) for r in range(2, 6)]
    gateway = FakeGateway()
    with ResultLogger(tmp_path) as logger:
        summary = ConcurrentBatchProcessor(
            FakeReader(reqs), build_default_validator(), gateway, logger, max_workers=2
        ).run(cancel_event=ev)
    assert summary.cancelled is True
    assert summary.success == 0
    assert gateway.calls == []  # ninguna llega a ejecutarse


def test_concurrent_logs_all_rows(tmp_path):
    reqs = [make_req(r) for r in range(2, 12)]  # 10 filas
    gateway = SlowGateway(delay=0.01)
    with ResultLogger(tmp_path) as logger:
        ConcurrentBatchProcessor(
            FakeReader(reqs), build_default_validator(), gateway, logger, max_workers=5
        ).run()
        results_path = logger.results_path
    lines = results_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 11  # header + 10 filas, sin perdidas por race
