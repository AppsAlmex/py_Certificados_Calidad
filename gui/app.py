"""Vista Tkinter. Solo widgets y eventos; toda la logica vive en el controlador.

Dos pestanas:
  * Ejecucion — configuraciones "al momento": CSV, reporte, workers, correr.
  * Settings  — configuraciones internas persistentes (host, timeouts, TLS,
                carpetas, credenciales, catalogo de reportes).
"""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from certificados.catalogs import parse_valor
from certificados.csv_reader import FORMAT_COLUMN, NAME_COLUMN, PARAM_COLUMNS
from certificados.models import ReportRequest

from .controller import CATALOG_FIELDS, BatchController

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
FORMATOS_SALIDA = ["pdf", "xml", "xlsx"]
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
        self.title("Certificados de Calidad - Ejecucion masiva")
        self.geometry("820x620")
        self.minsize(720, 560)

        self.controller = BatchController(config_path, env_path)
        self._queue: "queue.Queue" = queue.Queue()
        self._running = False
        self._active = None  # "batch" | "single" | None

        # estado de la pestana individual
        self._single_vars: dict[str, tk.StringVar] = {}
        self._queued: dict[str, ReportRequest] = {}
        self._single_next_id = 1
        try:
            self._catalogs = self.controller.read_catalogs()
        except Exception:
            self._catalogs = {}

        self._vars: dict[str, tk.Variable] = {}
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self._exec_tab = ttk.Frame(notebook)
        self._single_tab = ttk.Frame(notebook)
        self._settings_tab = ttk.Frame(notebook)
        notebook.add(self._exec_tab, text="  Ejecucion (CSV)  ")
        notebook.add(self._single_tab, text="  Certificado individual  ")
        notebook.add(self._settings_tab, text="  Settings  ")

        self._build_exec_tab(self._exec_tab)
        self._build_single_tab(self._single_tab)
        self._build_settings_tab(self._settings_tab)

        self._load_into_forms()
        self.after(100, self._poll_queue)

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
        ttk.Spinbox(top, from_=1, to=32, textvariable=self._vars["workers"], width=6).grid(
            row=2, column=1, sticky="w", padx=6
        )

        actions = ttk.Frame(parent)
        actions.pack(fill="x", padx=8)
        self._run_btn = ttk.Button(actions, text="Ejecutar", command=self._on_run)
        self._run_btn.pack(side="left")
        self._stop_btn = ttk.Button(actions, text="Detener", command=self._on_stop, state="disabled")
        self._stop_btn.pack(side="left", padx=(6, 0))
        self._progress = ttk.Progressbar(actions, mode="indeterminate")
        self._progress.pack(side="left", fill="x", expand=True, padx=10)

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
            return ttk.Combobox(parent, textvariable=var, values=[e.display for e in entries])
        return ttk.Entry(parent, textvariable=var)

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
        self._active = "single"
        self._set_running(True)
        self._append_log(f"Procesando {len(pending)} certificado(s) de la cola...")
        self.controller.process_requests_async(pending, self._queue)

    # -------------------------------------------------------------- SETTINGS
    def _build_settings_tab(self, parent: ttk.Frame) -> None:
        form = ttk.LabelFrame(parent, text="Configuracion interna (se guarda en config.ini / .env)")
        form.pack(fill="x", padx=8, pady=8)
        form.columnconfigure(1, weight=1)

        rows = [
            ("host", "Host:", tk.StringVar()),
            ("service_path", "Service path:", tk.StringVar()),
            ("timeout", "Read timeout (seg):", tk.StringVar()),
            ("connect_timeout", "Connect timeout (seg):", tk.StringVar()),
            ("output_dir", "Carpeta salida:", tk.StringVar()),
            ("log_dir", "Carpeta logs:", tk.StringVar()),
            ("user", "Usuario:", tk.StringVar()),
            ("password", "Contrasena:", tk.StringVar()),
        ]
        for i, (key, label, var) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            show = "*" if key == "password" else ""
            ttk.Entry(form, textvariable=var, show=show).grid(row=i, column=1, sticky="ew", padx=6)
            self._vars[key] = var

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
            form, textvariable=self._vars["default_report"], state="readonly"
        )
        self._default_report_combo.grid(row=n + 2, column=1, sticky="ew", padx=6)

        ttk.Label(form, text="Max workers (default):").grid(row=n + 3, column=0, sticky="w", padx=6, pady=4)
        self._vars["max_workers"] = tk.StringVar(value="1")
        ttk.Spinbox(form, from_=1, to=32, textvariable=self._vars["max_workers"], width=6).grid(
            row=n + 3, column=1, sticky="w", padx=6
        )

        cat = ttk.LabelFrame(parent, text="Catalogo de reportes (una linea:  clave = /ruta/reporte.xdo)")
        cat.pack(fill="both", expand=True, padx=8, pady=8)
        self._reports_text = tk.Text(cat, height=8, wrap="none")
        self._reports_text.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Button(parent, text="Guardar configuracion", command=self._on_save).pack(
            side="right", padx=8, pady=6
        )

    # ------------------------------------------------------------------ DATA
    def _load_into_forms(self) -> None:
        try:
            raw = self.controller.read_raw()
        except Exception as exc:  # pragma: no cover - defensivo
            messagebox.showerror("Error", f"No se pudo leer la configuracion:\n{exc}")
            return

        for key in ("host", "service_path", "timeout", "connect_timeout", "output_dir",
                    "log_dir", "user", "password", "log_level", "default_report", "max_workers"):
            if key in self._vars:
                self._vars[key].set(raw[key])
        self._vars["verify_ssl"].set(raw["verify_ssl"])

        self._reports_text.delete("1.0", "end")
        for clave, ruta in raw["reports"].items():
            self._reports_text.insert("end", f"{clave} = {ruta}\n")

        self._refresh_report_combos(list(raw["reports"]), raw["default_report"])
        self._vars["workers"].set(int(raw["max_workers"] or 1))

    def _refresh_report_combos(self, keys: list[str], default: str) -> None:
        self._report_combo["values"] = keys
        self._default_report_combo["values"] = keys
        if default in keys:
            self._vars["report"].set(default)
            self._vars["default_report"].set(default)
        elif keys:
            self._vars["report"].set(keys[0])

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

    # --------------------------------------------------------------- EVENTS
    def _pick_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecciona el CSV de solicitudes",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if path:
            self._vars["csv"].set(path)

    def _on_save(self) -> None:
        reports = self._parse_reports()
        if not reports:
            messagebox.showwarning("Catalogo vacio", "Agrega al menos un reporte (clave = ruta).")
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
                user=self._vars["user"].get().strip(),
                password=self._vars["password"].get(),
            )
        except ValueError:
            messagebox.showerror("Error", "Timeouts y workers deben ser numeros enteros.")
            return
        except Exception as exc:
            messagebox.showerror("Error al guardar", str(exc))
            return

        self._refresh_report_combos(list(reports), self._vars["default_report"].get())
        messagebox.showinfo("Guardado", "Configuracion guardada correctamente.")

    def _on_run(self) -> None:
        if self._running:
            return
        csv_path = self._vars["csv"].get().strip()
        if not csv_path:
            messagebox.showwarning("Falta CSV", "Selecciona un archivo CSV primero.")
            return

        self._active = "batch"
        self._set_running(True)
        self._append_log(f"Iniciando: {csv_path} | reporte={self._vars['report'].get()} "
                         f"| workers={self._vars['workers'].get()}")
        self.controller.run_async(
            csv_path,
            self._vars["report"].get(),
            int(self._vars["workers"].get()),
            self._queue,
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
                elif kind == "item":
                    _, item_id, estado, detalle = message
                    if self._single_tree.exists(item_id):
                        self._single_tree.set(item_id, "estado", estado)
                    if detalle:
                        self._append_log(f"[{item_id}] {estado}: {detalle}")
                elif kind == "done":
                    summary = message[1]
                    self._set_running(False)
                    self._status.set(f"Terminado. {summary}")
                    self._append_log(f"== {summary} ==")
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
            self._progress.start(12)
            self._status.set("Procesando...")
        else:
            self._active = None
            self._progress.stop()

    def _append_log(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")


def launch(config_path: str = "config.ini", env_path: str = ".env") -> None:
    CertificadosApp(config_path, env_path).mainloop()
