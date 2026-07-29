import zipfile
from pathlib import Path

from certificados.log_share import build_share_zip
from certificados.logs import LogRun


def _make_run(tmp_path) -> LogRun:
    stamp = "20260101_101010"
    (tmp_path / f"resultados_{stamp}.csv").write_text("timestamp,estado\n", encoding="utf-8")
    (tmp_path / f"ejecucion_{stamp}.log").write_text("log\n", encoding="utf-8")
    (tmp_path / f"diagnostico_{stamp}.jsonl").write_text('{"fila":2}\n', encoding="utf-8")
    (tmp_path / f"contexto_{stamp}.txt").write_text("reporte: R\n", encoding="utf-8")
    return LogRun(results_path=tmp_path / f"resultados_{stamp}.csv", fecha="x")


def _make_config(tmp_path) -> Path:
    cfg = tmp_path / "config.ini"
    cfg.write_text(
        "[service]\nhost = h\nuser = admin\npassword = s3cr3t\n\n"
        "[reports]\nR = /Custom/R.xdo\n",
        encoding="utf-8",
    )
    return cfg


def test_zip_contiene_miembros_esperados(tmp_path):
    run = _make_run(tmp_path)
    cfg = _make_config(tmp_path)
    dest = tmp_path / "salida" / "diag.zip"
    build_share_zip(run, dest, cfg)
    assert dest.exists()
    with zipfile.ZipFile(dest) as zf:
        names = set(zf.namelist())
    assert {"ejecucion.log", "resultados.csv", "diagnostico.jsonl",
            "contexto.txt", "config_saneado.ini", "LEEME.txt"} <= names


def test_zip_config_saneada_sin_credenciales(tmp_path):
    run = _make_run(tmp_path)
    cfg = _make_config(tmp_path)
    dest = tmp_path / "diag.zip"
    build_share_zip(run, dest, cfg)
    with zipfile.ZipFile(dest) as zf:
        saneada = zf.read("config_saneado.ini").decode("utf-8")
    assert "admin" not in saneada
    assert "s3cr3t" not in saneada
    assert "host = h" in saneada


def test_zip_nota_archivos_faltantes(tmp_path):
    run = _make_run(tmp_path)
    run.diagnostics_path.unlink()  # borra el jsonl
    cfg = _make_config(tmp_path)
    dest = tmp_path / "diag.zip"
    build_share_zip(run, dest, cfg)
    with zipfile.ZipFile(dest) as zf:
        names = set(zf.namelist())
        leeme = zf.read("LEEME.txt").decode("utf-8")
    assert "diagnostico.jsonl" not in names
    assert "diagnostico.jsonl" in leeme  # anotado como faltante
