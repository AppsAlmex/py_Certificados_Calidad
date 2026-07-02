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
