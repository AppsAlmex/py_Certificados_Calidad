from certificados.logs import LogRun, list_runs, read_log_text, read_results

HEADER = "timestamp,reporte,fila,estado,formato,duracion_seg,archivo,parametros,mensaje\n"


def _write_run(log_dir, stamp, rows, reporte="REP_A"):
    results = log_dir / f"resultados_{stamp}.csv"
    body = HEADER + "".join(
        f"2026-01-01T00:00:00,{reporte},{fila},{estado},pdf,1.0,x.pdf,{{}},{msg}\n"
        for fila, estado, msg in rows
    )
    results.write_text(body, encoding="utf-8")
    (log_dir / f"ejecucion_{stamp}.log").write_text(f"log de {stamp}\n", encoding="utf-8")
    return results


def test_list_runs_counts_and_order(tmp_path):
    _write_run(tmp_path, "20260101_100000", [(2, "OK", ""), (3, "ERROR", "boom")])
    _write_run(tmp_path, "20260102_120000", [(2, "OK", ""), (3, "OK", ""), (4, "INVALIDO", "malo")])

    runs = list_runs(tmp_path)
    assert [r.fecha for r in runs] == ["2026-01-02 12:00:00", "2026-01-01 10:00:00"]  # recientes primero
    newest = runs[0]
    assert newest.total == 3
    assert newest.ok == 2
    assert newest.invalido == 1
    assert newest.error == 0
    assert newest.reporte == "REP_A"  # reporte usado, leido del CSV


def test_log_path_derived(tmp_path):
    results = _write_run(tmp_path, "20260101_100000", [(2, "OK", "")])
    run = list_runs(tmp_path)[0]
    assert run.results_path == results
    assert run.log_path.name == "ejecucion_20260101_100000.log"
    assert run.log_path.exists()


def test_read_results_and_log(tmp_path):
    results = _write_run(tmp_path, "20260101_100000", [(2, "OK", ""), (3, "ERROR", "x")])
    rows = read_results(results)
    assert len(rows) == 2
    assert rows[0]["estado"] == "OK"
    assert "log de" in read_log_text(tmp_path / "ejecucion_20260101_100000.log")


def test_missing_dir_and_files(tmp_path):
    assert list_runs(tmp_path / "nope") == []
    assert read_results(tmp_path / "nope.csv") == []
    assert read_log_text(tmp_path / "nope.log") == ""
