from certificados.config import save_config
from certificados.health import run_health_checks


def _setup(tmp_path):
    cfg, env = tmp_path / "config.ini", tmp_path / ".env"
    catdir = tmp_path / "catalogos"
    catdir.mkdir()
    (catdir / "formato.csv").write_text("valor,descripcion\n1,General\n", encoding="utf-8")
    # inspector con duplicado -> debe fallar
    (catdir / "inspector.csv").write_text("valor,descripcion\n1,A\n1,B\n", encoding="utf-8")
    # planta_prod ausente -> debe fallar
    save_config(
        cfg, env, host="https://h.test", service_path="/s", timeout=30, connect_timeout=5,
        verify_ssl=False, default_report="a", reports={"a": "/A.xdo"}, max_workers=1,
        output_dir=str(tmp_path / "out"), log_dir=str(tmp_path / "logs"),
        log_level="INFO", user="u", password="p",
    )
    cfg.write_text(
        cfg.read_text(encoding="utf-8")
        + f"\n[catalogs]\ndir = {catdir.as_posix()}\nformato = formato.csv\n"
          f"inspector = inspector.csv\nplanta_prod = planta.csv\n",
        encoding="utf-8",
    )
    return cfg, env


def test_health_checks_report_problems(tmp_path):
    cfg, env = _setup(tmp_path)
    results = {r.nombre: r for r in run_health_checks(cfg, env, check_connectivity=False)}

    assert results["Configuracion"].ok
    assert results["Catalogo de reportes"].ok
    assert results["Catalogo formato"].ok
    assert not results["Catalogo inspector"].ok       # valor duplicado
    assert not results["Catalogo planta_prod"].ok     # archivo ausente
    assert results["Carpeta salida"].ok               # se crea y es escribible
    assert results["Carpeta logs"].ok


def test_health_checks_bad_config(tmp_path):
    # sin config valido -> Configuracion falla, pero no revienta
    results = run_health_checks(tmp_path / "nope.ini", tmp_path / ".env", check_connectivity=False)
    cfg_res = [r for r in results if r.nombre == "Configuracion"][0]
    assert cfg_res.ok is False
