"""Vista Tkinter. Solo widgets y eventos; toda la logica vive en el controlador.

Dos pestanas:
  * Ejecucion — configuraciones "al momento": CSV, reporte, workers, correr.
  * Settings  — configuraciones internas persistentes (host, timeouts, TLS,
                carpetas, credenciales, catalogo de reportes).
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from certificados import MAX_WORKERS, MIN_WORKERS, __version__
from certificados.catalogs import parse_valor
from certificados.csv_reader import FORMAT_COLUMN, NAME_COLUMN, PARAM_COLUMNS
from certificados.models import ReportRequest

from .controller import CATALOG_FIELDS, BatchController

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
FORMATOS_SALIDA = ["pdf","xml"]
CANTIDAD_FIELDS = ("cantidad1", "cantidad2", "cantidad3", "cantidad4")
CANTIDAD_VALUES = [""] + [str(i) for i in range(1, 11)]

# Etiquetas legibles para el formulario individual (columna CSV -> label).
FIELD_LABELS = {
    "embarque": "Embarque",
    "formato": "Formato (P_FORMATO)",
    "inspector": "Inspector",
    "observaciones": "Observaciones",
    "planta_prod": "Planta produccion",
    "tanque": "Tanque",
    "sello1": "Sello 1", "cantidad1": "Cantidad 1",
    "sello2": "Sello 2", "cantidad2": "Cantidad 2",
    "sello3": "Sello 3", "cantidad3": "Cantidad 3",
    "sello4": "Sello 4", "cantidad4": "Cantidad 4",
}


class CertificadosApp(tk.Tk):
    def __init__(self, config_path: str = "config.ini", env_path: str = ".env"):
        super().__init__()
        self.title("Certificados de Calidad")
        self.geometry("820x620")
        self.minsize(720, 660)
        self._set_icon()

        self.controller = BatchController(config_path, env_path)
        self._queue: "queue.Queue" = queue.Queue()
        self._running = False
        self._active = None  # "batch" | "single" | None

        # estado de la pestana individual
        self._single_vars: dict[str, tk.StringVar] = {}
        self._catalog_combos: dict[str, ttk.Combobox] = {}
        self._queued: dict[str, ReportRequest] = {}
        self._single_next_id = 1
        try:
            self._catalogs = self.controller.read_catalogs()
        except Exception:
            self._catalogs = {}

        self._vars: dict[str, tk.Variable] = {}

        # Barra de herramientas: Settings (ventana aparte con sus pestanas internas).
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Button(toolbar, text="Configuracion (Settings)", command=self._open_settings).pack(side="left")
        ttk.Label(toolbar, text=f"v{__version__}").pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self._exec_tab = ttk.Frame(notebook)
        self._single_tab = ttk.Frame(notebook)
        self._logs_tab = ttk.Frame(notebook)
        notebook.add(self._exec_tab, text="  Ejecucion (CSV)  ")
        notebook.add(self._single_tab, text="  Certificado individual  ")
        notebook.add(self._logs_tab, text="  Logs  ")

        self._build_exec_tab(self._exec_tab)
        self._build_single_tab(self._single_tab)
        self._build_logs_tab(self._logs_tab)

        self._load_into_forms()
        self.after(100, self._poll_queue)
        # Chequeo de actualizaciones en segundo plano al arrancar (silencioso si no hay).
        self.after(1500, lambda: self._check_updates_async(silent=True))

    # ------------------------------------------------------------------ EXEC
    def _build_exec_tab(self, parent: ttk.Frame) -> None:
        top = ttk.LabelFrame(parent, text="Parametros de ejecucion")
        top.pack(fill="x", padx=8, pady=8)
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Archivo CSV:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self._vars["csv"] = tk.StringVar()
        ttk.Entry(top, textvariable=self._vars["csv"]).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(top, text="Examinar...", command=self._pick_csv).grid(row=0, column=2, padx=6)

        ttk.Label(top, text="Reporte:").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self._vars["report"] = tk.StringVar()
        self._report_combo = ttk.Combobox(top, textvariable=self._vars["report"], state="readonly")
        self._report_combo.grid(row=1, column=1, sticky="ew", padx=6)

        ttk.Label(top, text="Workers (hilos):").grid(row=2, column=0, sticky="w", padx=6, pady=6)
        self._vars["workers"] = tk.IntVar(value=1)
        ttk.Spinbox(top, from_=MIN_WORKERS, to=MAX_WORKERS, textvariable=self._vars["workers"],
                    width=6).grid(row=2, column=1, sticky="w", padx=6)

        ttk.Label(top, text="Motor de PDF:").grid(row=3, column=0, sticky="w", padx=6, pady=6)
        self._exec_engine_var = tk.StringVar(value="oracle")
        ttk.Combobox(top, textvariable=self._exec_engine_var, values=["oracle", "local"],
                     state="readonly", width=10).grid(row=3, column=1, sticky="w", padx=6)

        actions = ttk.Frame(parent)
        actions.pack(fill="x", padx=8)
        self._run_btn = ttk.Button(actions, text="Ejecutar", command=self._on_run)
        self._run_btn.pack(side="left")
        self._stop_btn = ttk.Button(actions, text="Detener", command=self._on_stop, state="disabled")
        self._stop_btn.pack(side="left", padx=(6, 0))
        self._progress = ttk.Progressbar(actions, mode="determinate", maximum=100)
        self._progress.pack(side="left", fill="x", expand=True, padx=10)
        self._pct = tk.StringVar(value="0%")
        ttk.Label(actions, textvariable=self._pct, width=6).pack(side="left")

        log_frame = ttk.LabelFrame(parent, text="Registro en vivo")
        log_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self._log = tk.Text(log_frame, height=14, state="disabled", wrap="none")
        scroll = ttk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=scroll.set)
        self._log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._status = tk.StringVar(value="Listo.")
        ttk.Label(parent, textvariable=self._status, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

    # ---------------------------------------------------------------- SINGLE
    def _build_single_tab(self, parent: ttk.Frame) -> None:
        form = ttk.LabelFrame(parent, text="Datos del certificado (mismos campos del CSV)")
        form.pack(fill="x", padx=8, pady=8)
        for c in (1, 3):
            form.columnconfigure(c, weight=1)

        # Campos de parametros en dos columnas de pares (label, widget).
        cols = list(PARAM_COLUMNS.keys())
        for i, col in enumerate(cols):
            var = tk.StringVar()
            self._single_vars[col] = var
            r, block = divmod(i, 2)
            ttk.Label(form, text=FIELD_LABELS.get(col, col) + ":").grid(
                row=r, column=block * 2, sticky="w", padx=6, pady=3
            )
            widget = self._make_field_widget(form, col, var)
            widget.grid(row=r, column=block * 2 + 1, sticky="ew", padx=6, pady=3)

        base = (len(cols) + 1) // 2
        ttk.Label(form, text="Formato salida:").grid(row=base, column=0, sticky="w", padx=6, pady=3)
        self._single_vars[FORMAT_COLUMN] = tk.StringVar(value="pdf")
        ttk.Combobox(form, textvariable=self._single_vars[FORMAT_COLUMN], values=FORMATOS_SALIDA,
                     state="readonly", width=10).grid(row=base, column=1, sticky="w", padx=6, pady=3)
        ttk.Label(form, text="Nombre archivo:").grid(row=base, column=2, sticky="w", padx=6, pady=3)
        self._single_vars[NAME_COLUMN] = tk.StringVar()
        ttk.Entry(form, textvariable=self._single_vars[NAME_COLUMN]).grid(
            row=base, column=3, sticky="ew", padx=6, pady=3
        )

        form_btns = ttk.Frame(parent)
        form_btns.pack(fill="x", padx=8)
        ttk.Button(form_btns, text="Agregar a la cola", command=self._on_add_single).pack(side="left")
        ttk.Button(form_btns, text="Limpiar formulario", command=self._clear_single_form).pack(
            side="left", padx=6
        )

        list_frame = ttk.LabelFrame(parent, text="Certificados en proceso")
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        columns = ("embarque", "formato", "estado")
        self._single_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        for col, text, width in (
            ("embarque", "Embarque", 160),
            ("formato", "Formato", 90),
            ("estado", "Estado", 140),
        ):
            self._single_tree.heading(col, text=text)
            self._single_tree.column(col, width=width, anchor="w")
        tree_scroll = ttk.Scrollbar(list_frame, command=self._single_tree.yview)
        self._single_tree.configure(yscrollcommand=tree_scroll.set)
        self._single_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        # Opciones de envio: paridad con la ejecucion por CSV (reporte + workers).
        options = ttk.LabelFrame(parent, text="Opciones de envio")
        options.pack(fill="x", padx=8)
        ttk.Label(options, text="Reporte:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self._single_report_var = tk.StringVar()
        self._single_report_combo = ttk.Combobox(
            options, textvariable=self._single_report_var, state="readonly", width=42
        )
        self._single_report_combo.grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(options, text="Workers:").grid(row=0, column=2, sticky="w", padx=(18, 6))
        self._single_workers_var = tk.IntVar(value=1)
        ttk.Spinbox(options, from_=MIN_WORKERS, to=MAX_WORKERS,
                    textvariable=self._single_workers_var, width=6).grid(row=0, column=3, sticky="w", padx=6)
        ttk.Label(options, text="Motor:").grid(row=0, column=4, sticky="w", padx=(18, 6))
        self._single_engine_var = tk.StringVar(value="oracle")
        engine_combo = ttk.Combobox(options, textvariable=self._single_engine_var,
                                    values=["oracle", "local"], state="readonly", width=8)
        engine_combo.grid(row=0, column=5, sticky="w", padx=6)
        # Al cambiar el motor, el combo de formato carga plantillas locales o el catalogo.
        engine_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_formato_options())

        list_btns = ttk.Frame(parent)
        list_btns.pack(fill="x", padx=8, pady=(0, 8))
        self._process_btn = ttk.Button(list_btns, text="Procesar cola", command=self._on_process_single)
        self._process_btn.pack(side="left")
        self._single_stop_btn = ttk.Button(
            list_btns, text="Detener", command=self._on_stop, state="disabled"
        )
        self._single_stop_btn.pack(side="left", padx=6)
        ttk.Button(list_btns, text="Quitar seleccionado", command=self._on_remove_single).pack(side="left")
        ttk.Button(list_btns, text="Limpiar completados", command=self._clear_done).pack(side="left", padx=6)

    def _make_field_widget(self, parent, col, var):
        """Elige el widget segun el tipo de campo (combo cantidad, combo catalogo, entry)."""
        if col in CANTIDAD_FIELDS:
            return ttk.Combobox(parent, textvariable=var, values=CANTIDAD_VALUES,
                                state="readonly", width=8)
        if col in CATALOG_FIELDS:
            entries = self._catalogs.get(col, [])
            # editable: si el catalogo no cubre un valor, el usuario puede escribirlo.
            combo = ttk.Combobox(parent, textvariable=var, values=[e.display for e in entries])
            self._catalog_combos[col] = combo  # para recargar catalogos en caliente
            if col == "formato":
                self._formato_combo = combo  # se repuebla segun el motor elegido
            return combo
        return ttk.Entry(parent, textvariable=var)

    def _update_formato_options(self) -> None:
        """Con motor local, el combo de formato muestra solo plantillas locales;
        con oracle, el catalogo de formatos configurado."""
        if not hasattr(self, "_formato_combo"):
            return
        if self._single_engine_var.get() == "local":
            valores = self.controller.local_formats()  # ej. ['1']
        else:
            valores = [e.display for e in self._catalogs.get("formato", [])]
        self._formato_combo["values"] = valores
        actual = self._single_vars["formato"].get()
        # Si el valor actual no aplica al nuevo motor, toma el primero disponible.
        actuales_val = [v.split(" - ")[0] for v in valores]
        if valores and actual.split(" - ")[0] not in actuales_val:
            self._single_vars["formato"].set(valores[0])

    def _clear_single_form(self) -> None:
        for col in PARAM_COLUMNS:
            self._single_vars[col].set("")
        self._single_vars[FORMAT_COLUMN].set("pdf")
        self._single_vars[NAME_COLUMN].set("")

    def _on_add_single(self) -> None:
        embarque = self._single_vars["embarque"].get().strip()
        if not embarque:
            messagebox.showwarning("Falta dato", "El Embarque es obligatorio.")
            return
        params = {}
        for col, pkey in PARAM_COLUMNS.items():
            raw = self._single_vars[col].get()
            # En combos de catalogo el texto es "valor - descripcion"; guardamos el valor.
            params[pkey] = parse_valor(raw) if col in CATALOG_FIELDS else raw.strip()
        output_format = self._single_vars[FORMAT_COLUMN].get().strip().lower() or "pdf"
        output_name = self._single_vars[NAME_COLUMN].get().strip() or None

        item_id = str(self._single_next_id)
        self._single_next_id += 1
        request = ReportRequest(
            row_number=int(item_id), params=params,
            output_format=output_format, output_name=output_name,
        )
        self._queued[item_id] = request
        self._single_tree.insert("", "end", iid=item_id, values=(embarque, output_format, "En cola"))
        self._clear_single_form()

    def _on_remove_single(self) -> None:
        if self._running:
            return
        for iid in self._single_tree.selection():
            self._single_tree.delete(iid)
            self._queued.pop(iid, None)

    def _clear_done(self) -> None:
        if self._running:
            return
        for iid in list(self._queued):
            if self._single_tree.set(iid, "estado") == "OK":
                self._single_tree.delete(iid)
                self._queued.pop(iid, None)

    def _on_process_single(self) -> None:
        if self._running:
            return
        pending = [
            (iid, req) for iid, req in self._queued.items()
            if self._single_tree.set(iid, "estado") != "OK"
        ]
        if not pending:
            messagebox.showinfo("Sin pendientes", "No hay certificados en cola por procesar.")
            return
        report = self._single_report_var.get()
        workers = int(self._single_workers_var.get())
        engine = self._single_engine_var.get()
        self._active = "single"
        self._set_running(True)
        self._append_log(
            f"Procesando {len(pending)} certificado(s) | reporte={report} "
            f"| workers={workers} | motor={engine}"
        )
        self.controller.process_requests_async(
            pending, self._queue, report=report, workers=workers, engine=engine
        )

    # ------------------------------------------------------------------ LOGS
    def _build_logs_tab(self, parent: ttk.Frame) -> None:
        self._runs_by_iid: dict[str, object] = {}

        top = ttk.LabelFrame(parent, text="Ejecuciones (mas recientes primero)")
        top.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        run_cols = ("fecha", "reporte", "total", "ok", "error", "invalido")
        self._runs_tree = ttk.Treeview(top, columns=run_cols, show="headings", height=8)
        for col, text, width, anchor in (
            ("fecha", "Fecha", 150, "w"),
            ("reporte", "Reporte", 240, "w"),
            ("total", "Total", 55, "center"),
            ("ok", "OK", 50, "center"),
            ("error", "Error", 55, "center"),
            ("invalido", "Invalido", 65, "center"),
        ):
            self._runs_tree.heading(col, text=text)
            self._runs_tree.column(col, width=width, anchor=anchor)
        runs_scroll = ttk.Scrollbar(top, command=self._runs_tree.yview)
        self._runs_tree.configure(yscrollcommand=runs_scroll.set)
        self._runs_tree.pack(side="left", fill="both", expand=True)
        runs_scroll.pack(side="right", fill="y")
        self._runs_tree.bind("<<TreeviewSelect>>", self._on_run_selected)

        ttk.Button(parent, text="Refrescar", command=self._load_runs).pack(
            anchor="w", padx=8, pady=(0, 4)
        )

        detail = ttk.LabelFrame(parent, text="Detalle de la ejecucion")
        detail.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        detail_nb = ttk.Notebook(detail)
        detail_nb.pack(fill="both", expand=True, padx=4, pady=4)

        # Sub-pestana: resultados por fila (estructurado)
        res_frame = ttk.Frame(detail_nb)
        detail_nb.add(res_frame, text="Resultados")
        det_cols = ("fila", "reporte", "estado", "formato", "duracion_seg", "archivo", "mensaje")
        self._detail_tree = ttk.Treeview(res_frame, columns=det_cols, show="headings", height=8)
        for col, text, width in (
            ("fila", "Fila", 50),
            ("reporte", "Reporte", 200),
            ("estado", "Estado", 90),
            ("formato", "Formato", 70),
            ("duracion_seg", "Duracion(s)", 90),
            ("archivo", "Archivo", 200),
            ("mensaje", "Mensaje", 300),
        ):
            self._detail_tree.heading(col, text=text)
            self._detail_tree.column(col, width=width, anchor="w")
        det_scroll = ttk.Scrollbar(res_frame, command=self._detail_tree.yview)
        self._detail_tree.configure(yscrollcommand=det_scroll.set)
        self._detail_tree.pack(side="left", fill="both", expand=True)
        det_scroll.pack(side="right", fill="y")
        # Colores por estado para lectura comoda.
        self._detail_tree.tag_configure("OK", foreground="#1a7f37")
        self._detail_tree.tag_configure("ERROR", foreground="#b42318")
        self._detail_tree.tag_configure("INVALIDO", foreground="#b54708")

        # Sub-pestana: log de texto completo
        log_frame = ttk.Frame(detail_nb)
        detail_nb.add(log_frame, text="Log completo")
        self._log_detail = tk.Text(log_frame, wrap="none", state="disabled")
        log_scroll = ttk.Scrollbar(log_frame, command=self._log_detail.yview)
        self._log_detail.configure(yscrollcommand=log_scroll.set)
        self._log_detail.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        self._load_runs()

    def _load_runs(self) -> None:
        self._runs_tree.delete(*self._runs_tree.get_children())
        self._runs_by_iid.clear()
        try:
            runs = self.controller.read_runs()
        except Exception as exc:  # pragma: no cover - defensivo
            self._append_log(f"No se pudieron leer los logs: {exc}")
            return
        for run in runs:
            iid = run.results_path.name
            self._runs_by_iid[iid] = run
            self._runs_tree.insert(
                "", "end", iid=iid,
                values=(run.fecha, run.reporte, run.total, run.ok, run.error, run.invalido),
            )

    def _on_run_selected(self, _event=None) -> None:
        selection = self._runs_tree.selection()
        if not selection:
            return
        run = self._runs_by_iid.get(selection[0])
        if run is None:
            return

        self._detail_tree.delete(*self._detail_tree.get_children())
        for row in self.controller.read_run_results(run.results_path):
            estado = (row.get("estado") or "").upper()
            self._detail_tree.insert(
                "", "end",
                values=(
                    row.get("fila", ""), row.get("reporte", ""), row.get("estado", ""),
                    row.get("formato", ""), row.get("duracion_seg", ""),
                    row.get("archivo", ""), row.get("mensaje", ""),
                ),
                tags=(estado,) if estado in ("OK", "ERROR", "INVALIDO") else (),
            )

        text = self.controller.read_run_log(run.log_path)
        self._log_detail.configure(state="normal")
        self._log_detail.delete("1.0", "end")
        self._log_detail.insert("end", text)
        self._log_detail.configure(state="disabled")

    # ---------------------------------------------------- SETTINGS / CATALOGOS
    def _open_settings(self) -> None:
        """Abre Settings como ventana modal (bloquea la principal). Tiene pestanas
        internas: Configuracion, Catalogos y Health check. Al cerrarse, la
        principal recarga catalogos (pudieron editarse) y, si se guardo config,
        recarga y valida."""
        win = SettingsWindow(self, self.controller)
        self.wait_window(win)
        self._reload_catalogs(silent=True)  # reflejar cambios de catalogos siempre
        if getattr(win, "saved", False):
            self._load_into_forms()          # refresca combos runtime (reporte/workers/motor)
            try:
                self.controller.validate_settings()
                messagebox.showinfo("Configuracion", "Cambios guardados y aplicados. Configuracion valida.")
            except Exception as exc:
                messagebox.showwarning(
                    "Configuracion",
                    f"Se guardo, pero la configuracion tiene un problema:\n{exc}",
                )

    # --------------------------------------------------------------- UPDATES
    # Chequeo automatico al arrancar (silencioso). El chequeo manual vive en la
    # pestana "Actualizaciones" de SettingsWindow.
    def _check_updates_async(self, silent: bool) -> None:
        """Lanza el chequeo en un hilo para no congelar la GUI. El resultado se
        entrega en el hilo de Tk con ``self.after``."""
        def worker():
            try:
                from certificados import updater
                info = updater.check_for_update()
                self.after(0, lambda: self._on_update_checked(info, silent))
            except Exception as exc:  # red/auth: solo molestar si fue manual
                if not silent:
                    self.after(0, lambda: messagebox.showwarning(
                        "Actualizaciones",
                        f"No se pudo verificar actualizaciones:\n{exc}", parent=self))
        threading.Thread(target=worker, daemon=True).start()

    def _on_update_checked(self, info, silent: bool) -> None:
        if info is None:
            if not silent:
                messagebox.showinfo(
                    "Actualizaciones",
                    f"Estas en la ultima version (v{__version__}).", parent=self)
            return
        notes = (info.notes or "").strip()
        if len(notes) > 800:
            notes = notes[:800] + "..."
        if not messagebox.askyesno(
            "Actualizacion disponible",
            f"Version nueva: {info.tag}  (tienes v{__version__})\n\n"
            f"{notes}\n\n¿Descargar e instalar ahora? La app se cerrara y "
            f"volvera a abrir sola.",
            parent=self,
        ):
            return
        self._apply_update(info)

    def _apply_update(self, info) -> None:
        """Descarga con barra de progreso modal y aplica. No retorna si tiene
        exito (el proceso se cierra para que el .bat reemplace archivos)."""
        from certificados import updater

        win = tk.Toplevel(self)
        win.title("Actualizando")
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)
        ttk.Label(win, text=f"Descargando {info.tag}...").pack(padx=16, pady=(14, 6))
        bar = ttk.Progressbar(win, length=320, mode="determinate", maximum=100)
        bar.pack(padx=16, pady=(0, 14))

        def progress(done, total):
            pct = int(done * 100 / total) if total else 0
            self.after(0, lambda: bar.configure(value=pct))

        def worker():
            try:
                updater.download_and_apply(info, progress_cb=progress)
            except Exception as exc:
                self.after(0, lambda: (win.destroy(), messagebox.showerror(
                    "Actualizaciones", f"Fallo la actualizacion:\n{exc}", parent=self)))

        threading.Thread(target=worker, daemon=True).start()

    def _reload_catalogs(self, silent: bool = False) -> None:
        try:
            self._catalogs = self.controller.read_catalogs()
        except Exception as exc:
            messagebox.showerror("Catalogos", f"No se pudieron recargar:\n{exc}")
            return
        for col, combo in self._catalog_combos.items():
            if col == "formato":
                continue  # lo maneja _update_formato_options segun el motor
            combo["values"] = [e.display for e in self._catalogs.get(col, [])]
        self._update_formato_options()
        if not silent:
            total = sum(len(v) for v in self._catalogs.values())
            messagebox.showinfo("Catalogos", f"Catalogos recargados ({total} opciones).")

    # ------------------------------------------------------------------ DATA
    def _load_into_forms(self) -> None:
        try:
            raw = self.controller.read_raw()
        except Exception as exc:  # pragma: no cover - defensivo
            messagebox.showerror("Error", f"No se pudo leer la configuracion:\n{exc}")
            return

        self._refresh_report_combos(list(raw["reports"]), raw["default_report"])
        default_workers = int(raw["max_workers"] or 1)
        self._vars["workers"].set(default_workers)
        self._single_workers_var.set(default_workers)

        # Motor de PDF: el config da el default; el usuario lo cambia por corrida.
        engine = raw.get("pdf_engine", "oracle")
        self._exec_engine_var.set(engine)
        self._single_engine_var.set(engine)
        self._update_formato_options()

    def _refresh_report_combos(self, keys: list[str], default: str) -> None:
        self._report_combo["values"] = keys
        self._single_report_combo["values"] = keys
        chosen = default if default in keys else (keys[0] if keys else "")
        self._vars["report"].set(chosen)
        self._single_report_var.set(chosen)

    # --------------------------------------------------------------- EVENTS
    def _pick_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecciona el CSV de solicitudes",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if path:
            self._vars["csv"].set(path)

    def _on_run(self) -> None:
        if self._running:
            return
        csv_path = self._vars["csv"].get().strip()
        if not csv_path:
            messagebox.showwarning("Falta CSV", "Selecciona un archivo CSV primero.")
            return

        self._active = "batch"
        self._set_running(True)
        engine = self._exec_engine_var.get()
        self._append_log(f"Iniciando: {csv_path} | reporte={self._vars['report'].get()} "
                         f"| workers={self._vars['workers'].get()} | motor={engine}")
        self.controller.run_async(
            csv_path,
            self._vars["report"].get(),
            int(self._vars["workers"].get()),
            self._queue,
            engine=engine,
        )

    def _on_stop(self) -> None:
        if not self._running:
            return
        self.controller.cancel()
        self._status.set("Deteniendo... (la peticion en curso termina; no se lanzan mas)")
        self._append_log("Cancelacion solicitada por el usuario.")
        self._stop_btn.configure(state="disabled")
        self._single_stop_btn.configure(state="disabled")

    # ---------------------------------------------------------------- LOOP
    def _poll_queue(self) -> None:
        try:
            while True:
                message = self._queue.get_nowait()
                kind = message[0]
                if kind == "log":
                    self._append_log(message[1])
                elif kind == "progress":
                    _, done, total = message
                    pct = int(done * 100 / total) if total else 0
                    self._progress["value"] = pct
                    self._pct.set(f"{pct}%")
                    self._status.set(f"Procesando... {done}/{total} ({pct}%)")
                elif kind == "item":
                    _, item_id, estado, detalle = message
                    if self._single_tree.exists(item_id):
                        self._single_tree.set(item_id, "estado", estado)
                    if detalle:
                        self._append_log(f"[{item_id}] {estado}: {detalle}")
                elif kind == "done":
                    summary = message[1]
                    self._set_running(False)
                    self._progress["value"] = 100
                    self._pct.set("100%")
                    self._status.set(f"Terminado. {summary}")
                    self._append_log(f"== {summary} ==")
                    self._load_runs()  # la nueva ejecucion aparece en la pestana Logs
                    messagebox.showinfo("Proceso terminado", str(summary))
                elif kind == "error":
                    self._set_running(False)
                    self._status.set(f"Error: {message[1]}")
                    self._append_log(f"ERROR: {message[1]}")
                    messagebox.showerror("Error", str(message[1]))
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _set_running(self, running: bool) -> None:
        self._running = running
        run_state = "disabled" if running else "normal"
        stop_state = "normal" if running else "disabled"
        self._run_btn.configure(state=run_state)
        self._process_btn.configure(state=run_state)
        self._stop_btn.configure(state=stop_state)
        self._single_stop_btn.configure(state=stop_state)
        if running:
            self._progress["value"] = 0
            self._pct.set("0%")
            self._status.set("Procesando...")
        else:
            self._active = None

    def _append_log(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_icon(self) -> None:
        try:
            from certificados.runtime import icon_path
            ico = icon_path()
            if ico.exists():
                self.iconbitmap(str(ico))  # aplica tambien a las ventanas hijas (Toplevel)
        except Exception:
            pass  # sin icono no es critico


class SettingsWindow(tk.Toplevel):
    """Ventana modal de configuracion. Bloquea la principal. Tiene pestanas:
    Configuracion (guardar config.ini/.env), Catalogos (recargar/validar) y
    Health check (test entero de la app)."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.saved = False
        self.title("Configuracion (Settings)")
        self.geometry("700x600")
        self.transient(parent)
        self.grab_set()  # modal: bloquea la ventana principal
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._vars: dict[str, tk.Variable] = {}
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        config_tab = ttk.Frame(nb)
        catalog_tab = ttk.Frame(nb)
        health_tab = ttk.Frame(nb)
        info_tab = ttk.Frame(nb)
        updates_tab = ttk.Frame(nb)
        nb.add(config_tab, text="  Configuracion  ")
        nb.add(catalog_tab, text="  Catalogos  ")
        nb.add(health_tab, text="  Health check  ")
        nb.add(info_tab, text="  Info / Ayuda  ")
        nb.add(updates_tab, text="  Actualizaciones  ")
        self._build_config_tab(config_tab)
        self._build_catalog_tab(catalog_tab)
        self._build_health_tab(health_tab)
        self._build_info_tab(info_tab)
        self._build_updates_tab(updates_tab)

        self._load()

    # ---- pestana Configuracion ----
    def _build_config_tab(self, parent) -> None:
        form = ttk.LabelFrame(parent, text="Configuracion interna (se guarda en config.ini / .env)")
        form.pack(fill="x", padx=8, pady=8)
        form.columnconfigure(1, weight=1)

        rows = [
            ("host", "Host:"), ("service_path", "Service path:"),
            ("timeout", "Read timeout (seg):"), ("connect_timeout", "Connect timeout (seg):"),
            ("output_dir", "Carpeta salida:"), ("log_dir", "Carpeta logs:"),
            ("user", "Usuario:"), ("password", "Contrasena:"),
        ]
        for i, (key, label) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            var = tk.StringVar()
            self._vars[key] = var
            show = "*" if key == "password" else ""
            ttk.Entry(form, textvariable=var, show=show).grid(row=i, column=1, sticky="ew", padx=6)

        n = len(rows)
        self._vars["verify_ssl"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="Verificar certificado TLS (verify_ssl)",
                        variable=self._vars["verify_ssl"]).grid(row=n, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(form, text="Nivel de log:").grid(row=n + 1, column=0, sticky="w", padx=6, pady=4)
        self._vars["log_level"] = tk.StringVar(value="INFO")
        ttk.Combobox(form, textvariable=self._vars["log_level"], values=LOG_LEVELS,
                     state="readonly", width=12).grid(row=n + 1, column=1, sticky="w", padx=6)

        ttk.Label(form, text="Reporte por defecto:").grid(row=n + 2, column=0, sticky="w", padx=6, pady=4)
        self._vars["default_report"] = tk.StringVar()
        self._default_report_combo = ttk.Combobox(
            form, textvariable=self._vars["default_report"], state="readonly")
        self._default_report_combo.grid(row=n + 2, column=1, sticky="ew", padx=6)

        ttk.Label(form, text=f"Max workers (1-{MAX_WORKERS}):").grid(row=n + 3, column=0, sticky="w", padx=6, pady=4)
        self._vars["max_workers"] = tk.StringVar(value="1")
        ttk.Spinbox(form, from_=MIN_WORKERS, to=MAX_WORKERS, textvariable=self._vars["max_workers"],
                    width=6).grid(row=n + 3, column=1, sticky="w", padx=6)

        ttk.Label(form, text="Motor de PDF:").grid(row=n + 4, column=0, sticky="w", padx=6, pady=4)
        self._vars["pdf_engine"] = tk.StringVar(value="oracle")
        ttk.Combobox(form, textvariable=self._vars["pdf_engine"], values=["oracle", "local"],
                     state="readonly", width=12).grid(row=n + 4, column=1, sticky="w", padx=6)

        cat = ttk.LabelFrame(parent, text="Catalogo de reportes (una linea:  clave = /ruta/reporte.xdo)")
        cat.pack(fill="both", expand=True, padx=8, pady=8)
        self._reports_text = tk.Text(cat, height=7, wrap="none")
        self._reports_text.pack(fill="both", expand=True, padx=6, pady=6)

        btns = ttk.Frame(parent)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btns, text="Guardar y aplicar", command=self._on_save).pack(side="right")
        ttk.Button(btns, text="Cerrar", command=self.destroy).pack(side="right", padx=6)

    # ---- pestana Catalogos ----
    def _build_catalog_tab(self, parent) -> None:
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Button(top, text="Recargar y validar catalogos", command=self._reload_catalogs).pack(side="left")
        ttk.Label(top, text="(los CSV de la carpeta 'catalogos')", foreground="#666").pack(side="left", padx=8)

        cols = ("catalogo", "opciones", "estado", "detalle")
        self._cat_tree = ttk.Treeview(parent, columns=cols, show="headings")
        for col, text, width in (("catalogo", "Catalogo", 120), ("opciones", "Opciones", 80),
                                 ("estado", "Estado", 80), ("detalle", "Detalle", 360)):
            self._cat_tree.heading(col, text=text)
            self._cat_tree.column(col, width=width, anchor="w")
        self._cat_tree.tag_configure("ok", foreground="#1a7f37")
        self._cat_tree.tag_configure("fail", foreground="#b42318")
        self._cat_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _reload_catalogs(self) -> None:
        self._cat_tree.delete(*self._cat_tree.get_children())
        try:
            catalogos = self.controller.read_catalogs()
            problemas = dict(self.controller.validate_catalogs())
        except Exception as exc:
            messagebox.showerror("Catalogos", f"No se pudieron leer:\n{exc}", parent=self)
            return
        for campo in ("formato", "inspector", "planta_prod"):
            issues = problemas.get(campo, [])
            n = len(catalogos.get(campo, []))
            estado = "OK" if not issues else "PROBLEMA"
            self._cat_tree.insert("", "end",
                                  values=(campo, n, estado, "; ".join(issues) if issues else "OK"),
                                  tags=("ok" if not issues else "fail",))

    # ---- pestana Health check ----
    def _build_health_tab(self, parent) -> None:
        bar = ttk.Frame(parent)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(bar, text="Correr health check", command=self._run_health).pack(side="left")
        self._conn_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="incluir conectividad al servicio", variable=self._conn_var).pack(side="left", padx=8)
        self._health_summary = tk.StringVar(value="(sin correr)")
        ttk.Label(parent, textvariable=self._health_summary).pack(anchor="w", padx=8)

        cols = ("check", "estado", "detalle")
        self._health_tree = ttk.Treeview(parent, columns=cols, show="headings")
        for col, text, width in (("check", "Chequeo", 180), ("estado", "Estado", 70),
                                 ("detalle", "Detalle", 400)):
            self._health_tree.heading(col, text=text)
            self._health_tree.column(col, width=width, anchor="w")
        self._health_tree.tag_configure("ok", foreground="#1a7f37")
        self._health_tree.tag_configure("fail", foreground="#b42318")
        self._health_tree.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    def _run_health(self) -> None:
        self._health_tree.delete(*self._health_tree.get_children())
        self._health_summary.set("Ejecutando...")
        self.update_idletasks()
        try:
            results = self.controller.run_health_checks(check_connectivity=self._conn_var.get())
        except Exception as exc:
            self._health_summary.set(f"Error: {exc}")
            return
        fallos = sum(1 for r in results if not r.ok)
        for r in results:
            self._health_tree.insert("", "end", values=(r.nombre, "OK" if r.ok else "FALLA", r.detalle),
                                     tags=("ok" if r.ok else "fail",))
        total = len(results)
        self._health_summary.set(
            f"{total - fallos}/{total} OK" + (f"  |  {fallos} con problemas" if fallos else "  |  todo bien"))

    # ---- pestana Info / Ayuda (solo lectura) ----
    def _build_info_tab(self, parent) -> None:
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Documento:").pack(side="left")
        self._doc_var = tk.StringVar()
        self._doc_combo = ttk.Combobox(top, textvariable=self._doc_var, state="readonly", width=40)
        self._doc_combo.pack(side="left", padx=6)
        self._doc_combo.bind("<<ComboboxSelected>>", lambda _e: self._show_doc())

        body = ttk.Frame(parent)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._doc_text = tk.Text(body, wrap="word", state="disabled", padx=8, pady=8)
        doc_scroll = ttk.Scrollbar(body, command=self._doc_text.yview)
        self._doc_text.configure(yscrollcommand=doc_scroll.set)
        self._doc_text.pack(side="left", fill="both", expand=True)
        doc_scroll.pack(side="right", fill="y")

        try:
            self._docs = self.controller.list_docs()
        except Exception:
            self._docs = []
        self._doc_combo["values"] = [p.stem for p in self._docs]
        if self._docs:
            self._doc_combo.current(0)
            self._show_doc()
        else:
            self._set_doc_text("(No hay documentos de ayuda disponibles.)")

    def _show_doc(self) -> None:
        idx = self._doc_combo.current()
        if idx < 0 or idx >= len(self._docs):
            return
        try:
            contenido = self.controller.read_doc(self._docs[idx])
        except Exception as exc:
            contenido = f"No se pudo leer el documento:\n{exc}"
        self._set_doc_text(contenido)

    def _set_doc_text(self, text: str) -> None:
        self._doc_text.configure(state="normal")
        self._doc_text.delete("1.0", "end")
        self._doc_text.insert("end", text)
        self._doc_text.configure(state="disabled")  # solo lectura

    # ---- pestana Actualizaciones ----
    def _build_updates_tab(self, parent) -> None:
        box = ttk.LabelFrame(parent, text="Actualizaciones de la aplicacion")
        box.pack(fill="x", padx=8, pady=8)

        ttk.Label(box, text=f"Version instalada:  v{__version__}").pack(anchor="w", padx=8, pady=(8, 2))

        bar = ttk.Frame(box)
        bar.pack(fill="x", padx=8, pady=6)
        self._upd_btn = ttk.Button(bar, text="Buscar actualizaciones", command=self._on_check_updates)
        self._upd_btn.pack(side="left")

        self._upd_status = tk.StringVar(value="Pulsa 'Buscar actualizaciones' para consultar la ultima version.")
        ttk.Label(box, textvariable=self._upd_status, wraplength=620, justify="left").pack(
            anchor="w", padx=8, pady=(2, 8))

        self._upd_progress = ttk.Progressbar(box, length=620, mode="determinate", maximum=100)
        # se muestra solo durante la descarga (pack cuando haga falta)

        notes = ttk.LabelFrame(parent, text="Notas de la version disponible")
        notes.pack(fill="both", expand=True, padx=8, pady=8)
        self._upd_notes = tk.Text(notes, wrap="word", state="disabled", height=10, padx=8, pady=8)
        nscroll = ttk.Scrollbar(notes, command=self._upd_notes.yview)
        self._upd_notes.configure(yscrollcommand=nscroll.set)
        self._upd_notes.pack(side="left", fill="both", expand=True)
        nscroll.pack(side="right", fill="y")

    def _set_upd_notes(self, text: str) -> None:
        self._upd_notes.configure(state="normal")
        self._upd_notes.delete("1.0", "end")
        self._upd_notes.insert("end", text)
        self._upd_notes.configure(state="disabled")

    def _on_check_updates(self) -> None:
        """Chequeo manual desde la pestana (hilo aparte, no congela la ventana)."""
        self._upd_btn.configure(state="disabled")
        self._upd_status.set("Buscando actualizaciones...")
        self._set_upd_notes("")

        def worker():
            try:
                from certificados import updater
                info = updater.check_for_update()
                self.after(0, lambda: self._on_updates_checked(info))
            except Exception as exc:
                self.after(0, lambda: self._on_updates_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_updates_error(self, exc) -> None:
        self._upd_btn.configure(state="normal")
        self._upd_status.set(f"No se pudo verificar: {exc}")

    def _on_updates_checked(self, info) -> None:
        self._upd_btn.configure(state="normal")
        if info is None:
            self._upd_status.set(f"Estas en la ultima version (v{__version__}).")
            return
        self._upd_status.set(f"Version disponible: {info.tag}  (tienes v{__version__}).")
        self._set_upd_notes((info.notes or "").strip() or "(sin notas)")
        if messagebox.askyesno(
            "Actualizacion disponible",
            f"Version nueva: {info.tag}  (tienes v{__version__})\n\n"
            f"¿Descargar e instalar ahora? La app se cerrara y volvera a abrir sola.",
            parent=self,
        ):
            self._download_update(info)

    def _download_update(self, info) -> None:
        from certificados import updater

        self._upd_btn.configure(state="disabled")
        self._upd_status.set(f"Descargando {info.tag}...")
        self._upd_progress.pack(fill="x", padx=8, pady=(0, 8))
        self._upd_progress.configure(value=0)

        def progress(done, total):
            pct = int(done * 100 / total) if total else 0
            self.after(0, lambda: self._upd_progress.configure(value=pct))

        def worker():
            try:
                updater.download_and_apply(info, progress_cb=progress)
            except Exception as exc:
                self.after(0, lambda: self._on_download_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_download_error(self, exc) -> None:
        self._upd_progress.pack_forget()
        self._upd_btn.configure(state="normal")
        self._upd_status.set(f"Fallo la actualizacion: {exc}")
        messagebox.showerror("Actualizaciones", f"Fallo la actualizacion:\n{exc}", parent=self)

    # ---- datos / guardado ----
    def _load(self) -> None:
        try:
            raw = self.controller.read_raw()
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo leer la configuracion:\n{exc}", parent=self)
            return
        for key in ("host", "service_path", "timeout", "connect_timeout", "output_dir",
                    "log_dir", "user", "password", "log_level", "default_report",
                    "max_workers", "pdf_engine"):
            if key in self._vars:
                self._vars[key].set(raw[key])
        self._vars["verify_ssl"].set(raw["verify_ssl"])
        self._default_report_combo["values"] = list(raw["reports"])
        self._reports_text.delete("1.0", "end")
        for clave, ruta in raw["reports"].items():
            self._reports_text.insert("end", f"{clave} = {ruta}\n")
        self._reload_catalogs()

    def _parse_reports(self) -> dict:
        reports: dict[str, str] = {}
        for raw_line in self._reports_text.get("1.0", "end").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, path = line.partition("=")
            key, path = key.strip(), path.strip()
            if key and path:
                reports[key] = path
        return reports

    def _on_save(self) -> None:
        reports = self._parse_reports()
        if not reports:
            messagebox.showwarning("Catalogo vacio", "Agrega al menos un reporte (clave = ruta).", parent=self)
            return
        try:
            self.controller.save(
                host=self._vars["host"].get().strip(),
                service_path=self._vars["service_path"].get().strip(),
                timeout=int(self._vars["timeout"].get()),
                connect_timeout=int(self._vars["connect_timeout"].get()),
                verify_ssl=self._vars["verify_ssl"].get(),
                default_report=self._vars["default_report"].get().strip() or next(iter(reports)),
                reports=reports,
                max_workers=int(self._vars["max_workers"].get()),
                output_dir=self._vars["output_dir"].get().strip() or "output",
                log_dir=self._vars["log_dir"].get().strip() or "logs",
                log_level=self._vars["log_level"].get(),
                pdf_engine=self._vars["pdf_engine"].get(),
                user=self._vars["user"].get().strip(),
                password=self._vars["password"].get(),
            )
        except ValueError:
            messagebox.showerror("Error", "Timeouts y workers deben ser numeros enteros.", parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Error al guardar", str(exc), parent=self)
            return
        self.saved = True
        self.destroy()  # la principal recarga y valida al cerrarse


def launch(config_path: str = "config.ini", env_path: str = ".env") -> None:
    CertificadosApp(config_path, env_path).mainloop()
