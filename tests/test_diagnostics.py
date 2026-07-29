import threading

from certificados.diagnostics import (
    InMemoryTransportCapture,
    NullTransportCapture,
    expand_params,
    redact_soap,
)

SOAP = (
    "<v2:runReport><v2:userID>admin</v2:userID>"
    "<v2:password>s3cr3t</v2:password></v2:runReport>"
)


def test_redact_soap_oculta_credenciales():
    out = redact_soap(SOAP)
    assert "admin" not in out
    assert "s3cr3t" not in out
    assert "<v2:userID>***</v2:userID>" in out
    assert "<v2:password>***</v2:password>" in out


def test_redact_soap_multilinea_y_sin_prefijo():
    soap = "<userID>\n  admin\n</userID><password>p</password>"
    out = redact_soap(soap)
    assert "admin" not in out
    assert "<userID>***</userID>" in out
    assert "<password>***</password>" in out


def test_null_capture_no_guarda_nada():
    cap = NullTransportCapture()
    cap.record(2, soap="x", status=200)
    assert cap.get(2) is None


def test_inmemory_capture_guarda_y_recupera():
    cap = InMemoryTransportCapture()
    cap.record(2, soap="redacted", status=200, is_report=True, size=10)
    rec = cap.get(2)
    assert rec.status == 200
    assert rec.is_report is True
    assert rec.size == 10
    assert cap.get(99) is None


def test_inmemory_capture_thread_safe():
    cap = InMemoryTransportCapture()

    def worker(n):
        cap.record(n, soap=f"s{n}", status=200)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(cap.get(i).soap == f"s{i}" for i in range(50))


def test_expand_params_traduce_con_catalogos():
    maps = {
        "inspector": {"003": "Hector Correa"},
        "formato": {"1": "Estandar"},
    }
    out = expand_params({"P_INSPECTOR": "003", "P_FORMATO": "1"}, maps)
    assert out["P_INSPECTOR"] == "003 - Hector Correa"
    assert out["P_FORMATO"] == "1 - Estandar"


def test_expand_params_sin_match_deja_codigo():
    out = expand_params({"P_INSPECTOR": "999", "P_SELLO1": "951"}, {"inspector": {}})
    assert out["P_INSPECTOR"] == "999"
    assert out["P_SELLO1"] == "951"
