import json
from pathlib import Path

from certificados.diagnostics import InMemoryTransportCapture
from certificados.models import BatchSummary, ReportRequest, ReportResult
from certificados.result_logger import ResultLogger
from certificados.validators import ValidationIssue


def _req(fila=2):
    return ReportRequest(row_number=fila, params={"P_INSPECTOR": "003"}, output_format="pdf")


def test_jsonl_ok_lleva_transporte_y_params_legibles(tmp_path):
    cap = InMemoryTransportCapture()
    cap.record(2, soap="<v2:password>***</v2:password>", status=200, is_report=True, size=123)
    expander = lambda params: {"P_INSPECTOR": "003 - Hector Correa"}
    with ResultLogger(tmp_path, transport=cap, param_expander=expander,
                      context={"reporte": "R"}) as logger:
        req = _req()
        result = ReportResult(request=req, file_path=tmp_path / "c.pdf", size_bytes=123)
        logger.log_success(result, 1.5)
        jsonl_path = logger.diagnostics_path
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    assert entry["estado"] == "OK"
    assert entry["http_status"] == 200
    assert entry["respuesta"] is None
    assert entry["respuesta_size"] == 123
    assert entry["params_legibles"]["P_INSPECTOR"] == "003 - Hector Correa"
    assert entry["soap_request"] == "<v2:password>***</v2:password>"


def test_jsonl_error_lleva_cuerpo(tmp_path):
    cap = InMemoryTransportCapture()
    cap.record(2, soap="s", status=None, response_body="Respuesta HTTP 500: boom",
               is_report=False, size=None)
    with ResultLogger(tmp_path, transport=cap) as logger:
        logger.log_failure(_req(), RuntimeError("boom"), 0.4)
        jsonl_path = logger.diagnostics_path
    entry = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["estado"] == "ERROR"
    assert "500" in entry["respuesta"]
    assert entry["respuesta_size"] is None


def test_jsonl_invalido_sin_transporte(tmp_path):
    with ResultLogger(tmp_path) as logger:  # sin capturador
        logger.log_invalid(_req(), ["campo X requerido"], 0.0)
        jsonl_path = logger.diagnostics_path
    entry = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["estado"] == "INVALIDO"
    assert entry["soap_request"] is None
    assert "campo X requerido" in entry["mensaje"]


def test_contexto_txt_se_escribe(tmp_path):
    with ResultLogger(tmp_path, context={"reporte": "R", "workers": 4}) as logger:
        ctx_path = logger.context_path
    text = ctx_path.read_text(encoding="utf-8")
    assert "reporte: R" in text
    assert "workers: 4" in text


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


def test_jsonl_ok_nunca_guarda_cuerpo_aunque_se_registre(tmp_path):
    cap = InMemoryTransportCapture()
    cap.record(2, soap="s", status=200, response_body="NO DEBERIA APARECER",
               is_report=True, size=50)
    with ResultLogger(tmp_path, transport=cap) as logger:
        req = _req()
        result = ReportResult(request=req, file_path=tmp_path / "c.pdf", size_bytes=50)
        logger.log_success(result, 1.0)
        jsonl_path = logger.diagnostics_path
    entry = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["respuesta"] is None
    assert entry["respuesta_size"] == 50


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
