from pathlib import Path

from certificados.models import BatchSummary, ReportRequest, ReportResult
from certificados.result_logger import ResultLogger
from certificados.validators import ValidationIssue


def make_req(row=2):
    return ReportRequest(row_number=row, params={"P_EMBARQUE": "256436"}, output_format="pdf")


def test_success_row_written(tmp_path):
    with ResultLogger(tmp_path) as logger:
        result = ReportResult(make_req(), Path("out/x.pdf"), 123)
        logger.log_success(result, 1.5)
        path = logger.results_path
    content = path.read_text(encoding="utf-8")
    assert "OK" in content
    assert "256436" in content
    assert "1.50" in content


def test_failure_row_written(tmp_path):
    with ResultLogger(tmp_path) as logger:
        logger.log_failure(make_req(3), ValueError("boom"), 0.2)
        path = logger.results_path
    content = path.read_text(encoding="utf-8")
    assert "ERROR" in content
    assert "boom" in content


def test_invalid_row_written(tmp_path):
    with ResultLogger(tmp_path) as logger:
        issues = [ValidationIssue(4, "P_EMBARQUE", "campo obligatorio vacio")]
        logger.log_invalid(make_req(4), issues, 0.0)
        path = logger.results_path
    content = path.read_text(encoding="utf-8")
    assert "INVALIDO" in content
    assert "P_EMBARQUE" in content


def test_summary_logged(tmp_path):
    with ResultLogger(tmp_path) as logger:
        logger.summary(BatchSummary(total=3, success=2, failed=1))
    assert list(tmp_path.glob("ejecucion_*.log"))


def test_context_recorded_in_results_and_log(tmp_path):
    context = {"reporte": "REP_X", "workers": 4, "timeout": 300}
    with ResultLogger(tmp_path, context=context) as logger:
        logger.log_success(ReportResult(make_req(), Path("x.pdf"), 1), 0.1)
    results = list(tmp_path.glob("resultados_*.csv"))[0].read_text(encoding="utf-8")
    assert "reporte" in results.splitlines()[0]  # columna en header
    assert "REP_X" in results                     # valor en la fila
    log_text = list(tmp_path.glob("ejecucion_*.log"))[0].read_text(encoding="utf-8")
    assert "Inicio de ejecucion" in log_text
    assert "reporte=REP_X" in log_text


def test_extra_handler_receives_records_and_is_not_closed(tmp_path):
    import logging

    class Capture(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []
            self.closed = False

        def emit(self, record):
            self.records.append(record.getMessage())

        def close(self):
            self.closed = True
            super().close()

    handler = Capture()
    with ResultLogger(tmp_path, extra_handlers=[handler]) as logger:
        logger.log_success(ReportResult(make_req(), Path("x.pdf"), 1), 0.1)
    assert any("OK" in m for m in handler.records)
    assert handler.closed is False  # handler externo no debe cerrarse
