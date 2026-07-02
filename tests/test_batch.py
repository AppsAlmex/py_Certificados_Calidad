from certificados.batch import BatchProcessor
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
