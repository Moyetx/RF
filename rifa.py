#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de Rifas
===============
Aplicación de escritorio (Tkinter) para administrar la venta de boletos de una rifa.

Funciones principales:
  * Crear una nueva rifa como archivo CSV: nombre, rango de boletos y campos
    personalizados (Nombre, Teléfono, Correo, Método de pago, etc.).
    La columna "Boleto" se genera automáticamente.
  * Ciclo de captura que se puede iniciar y detener para llenar los datos de
    cada boleto uno por uno.
  * Vista del CSV dentro de la aplicación (doble clic en una fila para editarla).
  * Resumen: cuántos boletos van vendidos, cuáles números faltan y cuántos
    siguen vacíos.
  * Agregar más números de boleto a una rifa existente.
  * Interfaz con tema claro y oscuro.

Requisitos: Python 3.8+ con Tkinter (incluido en la instalación estándar).
Ejecución:  python rifa.py
"""

import csv
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

TICKET_COL = "Boleto"

LIGHT = {
    "bg":        "#f2f3f7",
    "surface":   "#ffffff",
    "bg2":       "#e6e8ef",
    "text":      "#1b1d23",
    "subtext":   "#5c6270",
    "border":    "#c9cdd8",
    "entry_bg":  "#ffffff",
    "accent":    "#2563eb",
    "accent_fg": "#ffffff",
    "success":   "#15803d",
    "danger":    "#dc2626",
    "row_filled": "#dcfce7",
}

DARK = {
    "bg":        "#15171c",
    "surface":   "#1f2229",
    "bg2":       "#2a2e37",
    "text":      "#eceef2",
    "subtext":   "#9aa1af",
    "border":    "#3a3f4b",
    "entry_bg":  "#2a2e37",
    "accent":    "#3b82f6",
    "accent_fg": "#ffffff",
    "success":   "#4ade80",
    "danger":    "#f87171",
    "row_filled": "#14532d",
}


def compress_numbers(nums):
    """Convierte [1,2,3,5,7,8] en '1-3, 5, 7-8' para mostrar listas largas."""
    nums = sorted(set(nums))
    if not nums:
        return "—"
    parts = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = n
    parts.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(parts)


class Rifa:
    """Modelo de datos: una rifa respaldada por un archivo CSV."""

    def __init__(self, path, fields, rows):
        self.path = path
        self.fields = fields          # columnas personalizadas (sin "Boleto")
        self.rows = rows              # lista de dicts en orden

    @property
    def name(self):
        return os.path.splitext(os.path.basename(self.path))[0]

    @classmethod
    def new(cls, path, start, end, fields):
        rows = [{TICKET_COL: str(n), **{f: "" for f in fields}}
                for n in range(start, end + 1)]
        rifa = cls(path, list(fields), rows)
        rifa.save()
        return rifa

    @classmethod
    def load(cls, path):
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            headers = reader.fieldnames or []
            if not headers or headers[0] != TICKET_COL:
                raise ValueError(
                    f'El CSV debe tener "{TICKET_COL}" como primera columna. '
                    f"Columnas encontradas: {headers}"
                )
            fields = headers[1:]
            rows = [{h: (row.get(h) or "").strip() for h in headers}
                    for row in reader]
        return cls(path, fields, rows)

    def save(self):
        with open(self.path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=[TICKET_COL] + self.fields)
            writer.writeheader()
            writer.writerows(self.rows)

    # ---- consultas ----
    def is_filled(self, row):
        return any(row.get(f, "").strip() for f in self.fields)

    def numeric_tickets(self):
        out = []
        for row in self.rows:
            try:
                out.append(int(row[TICKET_COL]))
            except ValueError:
                pass
        return out

    def sold_numbers(self):
        out = []
        for row in self.rows:
            if self.is_filled(row):
                try:
                    out.append(int(row[TICKET_COL]))
                except ValueError:
                    pass
        return out

    def empty_numbers(self):
        out = []
        for row in self.rows:
            if not self.is_filled(row):
                try:
                    out.append(int(row[TICKET_COL]))
                except ValueError:
                    pass
        return out

    def next_empty_index(self, after=-1):
        """Siguiente boleto vacío después de `after`, dando la vuelta una vez."""
        n = len(self.rows)
        for offset in range(1, n + 1):
            i = (after + offset) % n
            if not self.is_filled(self.rows[i]):
                return i
        return None

    def add_range(self, start, end):
        existing = set(self.numeric_tickets())
        added = 0
        for n in range(start, end + 1):
            if n in existing:
                continue
            self.rows.append({TICKET_COL: str(n),
                              **{f: "" for f in self.fields}})
            added += 1
        # mantener el orden numérico cuando todos los boletos son números
        try:
            self.rows.sort(key=lambda r: int(r[TICKET_COL]))
        except ValueError:
            pass
        if added:
            self.save()
        return added


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de Rifas")
        self.geometry("1050x700")
        self.minsize(820, 560)

        self.dark = False
        self.rifa = None
        self.capturing = False
        self.capture_index = None
        self.current_view = "home"     # home | new | rifa
        self.current_tab = "captura"   # captura | vista | resumen | agregar
        self._capture_backup = None    # valores del formulario al cambiar tema
        self._new_fields = ["Nombre", "Teléfono"]  # campos del formulario "nueva rifa"

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.header = tk.Frame(self)
        self.header.pack(fill="x")
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.render()

    # ------------------------------------------------------------------ tema
    @property
    def palette(self):
        return DARK if self.dark else LIGHT

    def toggle_theme(self):
        if self.capturing:
            self._capture_backup = self._read_capture_form()
        if self.current_view == "new":
            self._snapshot_new_form()
        self.dark = not self.dark
        self.render()

    def apply_ttk_styles(self):
        p = self.palette
        self.style.configure("Treeview", background=p["surface"],
                             fieldbackground=p["surface"], foreground=p["text"],
                             bordercolor=p["border"], rowheight=26, font=("TkDefaultFont", 10))
        self.style.configure("Treeview.Heading", background=p["bg2"],
                             foreground=p["text"], relief="flat",
                             font=("TkDefaultFont", 10, "bold"))
        self.style.map("Treeview.Heading", background=[("active", p["bg2"])])
        self.style.map("Treeview",
                       background=[("selected", p["accent"])],
                       foreground=[("selected", p["accent_fg"])])
        for orient in ("Vertical", "Horizontal"):
            self.style.configure(f"{orient}.TScrollbar", background=p["bg2"],
                                 troughcolor=p["bg"], bordercolor=p["bg"],
                                 arrowcolor=p["subtext"])
            self.style.map(f"{orient}.TScrollbar", background=[("active", p["border"])])

    # ------------------------------------------------------- widgets con tema
    def label(self, parent, text, size=10, bold=False, color=None, **kw):
        p = self.palette
        font = ("TkDefaultFont", size, "bold" if bold else "normal")
        bg = kw.pop("bg", parent.cget("bg"))
        return tk.Label(parent, text=text, font=font, bg=bg,
                        fg=color or p["text"], **kw)

    def button(self, parent, text, command, kind="accent", **kw):
        p = self.palette
        colors = {
            "accent": (p["accent"], p["accent_fg"]),
            "ghost":  (p["bg2"], p["text"]),
            "danger": (p["danger"], "#ffffff"),
            "success": (p["success"] if not self.dark else "#166534", "#ffffff"),
        }
        bg, fg = colors.get(kind, colors["accent"])
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground=bg, activeforeground=fg,
                         relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
                         font=("TkDefaultFont", 10, "bold"), **kw)

    def entry(self, parent, textvariable=None, width=24):
        p = self.palette
        return tk.Entry(parent, textvariable=textvariable, width=width,
                        bg=p["entry_bg"], fg=p["text"], insertbackground=p["text"],
                        relief="flat", highlightthickness=1,
                        highlightbackground=p["border"], highlightcolor=p["accent"],
                        font=("TkDefaultFont", 11))

    def card(self, parent):
        p = self.palette
        outer = tk.Frame(parent, bg=p["border"], padx=1, pady=1)
        inner = tk.Frame(outer, bg=p["surface"], padx=18, pady=16)
        inner.pack(fill="both", expand=True)
        return outer, inner

    # ------------------------------------------------------------- estructura
    def render(self):
        p = self.palette
        self.unbind("<Return>")
        self.configure(bg=p["bg"])
        self.apply_ttk_styles()
        for w in self.header.winfo_children():
            w.destroy()
        for w in self.container.winfo_children():
            w.destroy()
        self.header.configure(bg=p["surface"])
        self.container.configure(bg=p["bg"])
        self.build_header()
        if self.current_view == "home":
            self.build_home()
        elif self.current_view == "new":
            self.build_new()
        else:
            self.build_rifa_view()

    def build_header(self):
        p = self.palette
        bar = tk.Frame(self.header, bg=p["surface"], padx=16, pady=10)
        bar.pack(fill="x")
        self.label(bar, "🎟  Gestor de Rifas", size=14, bold=True,
                   bg=p["surface"]).pack(side="left")
        if self.rifa:
            self.label(bar, f"   {self.rifa.name}", size=11,
                       color=p["subtext"], bg=p["surface"]).pack(side="left")
        self.button(bar, "☀ Claro" if self.dark else "🌙 Oscuro",
                    self.toggle_theme, kind="ghost").pack(side="right")
        if self.current_view != "home":
            self.button(bar, "⌂ Inicio", self.go_home,
                        kind="ghost").pack(side="right", padx=(0, 8))
        tk.Frame(self.header, bg=p["border"], height=1).pack(fill="x")

    def go_home(self):
        if self.capturing:
            self.stop_capture(save_current=False)
        self.current_view = "home"
        self.render()

    # ------------------------------------------------------------------ home
    def build_home(self):
        p = self.palette
        wrap = tk.Frame(self.container, bg=p["bg"])
        wrap.place(relx=0.5, rely=0.42, anchor="center")
        outer, card = self.card(wrap)
        outer.pack()
        self.label(card, "¿Qué deseas hacer?", size=15, bold=True,
                   bg=p["surface"]).pack(pady=(0, 4))
        self.label(card, "Crea una rifa nueva o continúa llenando una existente.",
                   color=p["subtext"], bg=p["surface"]).pack(pady=(0, 16))
        self.button(card, "＋  Crear nueva rifa",
                    self.show_new, kind="accent").pack(fill="x", pady=4)
        self.button(card, "📂  Abrir rifa existente (CSV)",
                    self.open_rifa, kind="ghost").pack(fill="x", pady=4)

    def show_new(self):
        self.current_view = "new"
        self.render()

    def open_rifa(self):
        path = filedialog.askopenfilename(
            title="Abrir rifa", filetypes=[("Archivos CSV", "*.csv")])
        if not path:
            return
        try:
            self.rifa = Rifa.load(path)
        except Exception as exc:
            messagebox.showerror("No se pudo abrir", str(exc))
            return
        self.capturing = False
        self.capture_index = None
        self.current_view = "rifa"
        self.current_tab = "captura"
        self.render()

    # ------------------------------------------------------------- nueva rifa
    def build_new(self):
        p = self.palette
        wrap = tk.Frame(self.container, bg=p["bg"])
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        outer, card = self.card(wrap)
        outer.pack()

        self.label(card, "Nueva rifa", size=15, bold=True,
                   bg=p["surface"]).grid(row=0, column=0, columnspan=4,
                                         sticky="w", pady=(0, 12))

        self.label(card, "Nombre de la rifa:", bg=p["surface"]).grid(
            row=1, column=0, sticky="w", pady=4)
        self.new_name = tk.StringVar(value=getattr(self, "_new_name", ""))
        self.entry(card, self.new_name, width=34).grid(
            row=1, column=1, columnspan=3, sticky="we", pady=4, padx=(8, 0))

        self.label(card, "Boletos del número:", bg=p["surface"]).grid(
            row=2, column=0, sticky="w", pady=4)
        self.new_start = tk.StringVar(value=getattr(self, "_new_start", "1"))
        self.entry(card, self.new_start, width=8).grid(
            row=2, column=1, sticky="w", pady=4, padx=(8, 0))
        self.label(card, "al:", bg=p["surface"]).grid(
            row=2, column=2, sticky="e", pady=4)
        self.new_end = tk.StringVar(value=getattr(self, "_new_end", "100"))
        self.entry(card, self.new_end, width=8).grid(
            row=2, column=3, sticky="w", pady=4, padx=(8, 0))

        self.label(card, "Campos por boleto (la columna Boleto se genera sola):",
                   bg=p["surface"], color=p["subtext"]).grid(
            row=3, column=0, columnspan=4, sticky="w", pady=(14, 4))

        self.fields_frame = tk.Frame(card, bg=p["surface"])
        self.fields_frame.grid(row=4, column=0, columnspan=4, sticky="we")
        self.field_vars = []
        for name in self._new_fields:
            self._add_field_row(name)

        btns = tk.Frame(card, bg=p["surface"])
        btns.grid(row=5, column=0, columnspan=4, sticky="we", pady=(6, 0))
        self.button(btns, "＋ Agregar campo",
                    lambda: self._add_field_row(""), kind="ghost").pack(side="left")

        actions = tk.Frame(card, bg=p["surface"])
        actions.grid(row=6, column=0, columnspan=4, sticky="we", pady=(18, 0))
        self.button(actions, "Crear rifa 🎟", self.create_rifa,
                    kind="accent").pack(side="left")
        self.button(actions, "Cancelar", self.go_home,
                    kind="ghost").pack(side="left", padx=8)

    def _snapshot_new_form(self):
        """Conserva lo tecleado en el formulario de nueva rifa al re-renderizar."""
        if not hasattr(self, "new_name"):
            return
        self._new_name = self.new_name.get()
        self._new_start = self.new_start.get()
        self._new_end = self.new_end.get()
        fields = [var.get() for var, _row in self.field_vars]
        self._new_fields = fields or self._new_fields

    def _add_field_row(self, initial=""):
        p = self.palette
        row = tk.Frame(self.fields_frame, bg=p["surface"])
        row.pack(fill="x", pady=2)
        var = tk.StringVar(value=initial)
        self.entry(row, var, width=30).pack(side="left")
        entry_pair = (var, row)
        self.field_vars.append(entry_pair)

        def remove():
            self.field_vars.remove(entry_pair)
            row.destroy()

        self.button(row, "✕", remove, kind="danger").pack(side="left", padx=6)

    def create_rifa(self):
        name = self.new_name.get().strip()
        if not name:
            messagebox.showwarning("Falta el nombre", "Escribe el nombre de la rifa.")
            return
        try:
            start = int(self.new_start.get())
            end = int(self.new_end.get())
        except ValueError:
            messagebox.showwarning("Rango inválido",
                                   "El rango de boletos debe ser numérico.")
            return
        if end < start:
            messagebox.showwarning("Rango inválido",
                                   "El número final debe ser mayor o igual al inicial.")
            return
        fields, seen = [], set()
        for var, _row in self.field_vars:
            f = var.get().strip()
            if not f:
                continue
            if f == TICKET_COL or f in seen:
                messagebox.showwarning(
                    "Campo repetido",
                    f'El campo "{f}" está repetido o se llama igual que la '
                    f"columna automática {TICKET_COL}.")
                return
            seen.add(f)
            fields.append(f)
        if not fields:
            messagebox.showwarning("Sin campos",
                                   "Agrega al menos un campo (por ejemplo: Nombre).")
            return
        self._new_fields = fields

        path = filedialog.asksaveasfilename(
            title="Guardar rifa como", defaultextension=".csv",
            initialfile=f"{name}.csv", filetypes=[("Archivos CSV", "*.csv")])
        if not path:
            return
        try:
            self.rifa = Rifa.new(path, start, end, fields)
        except Exception as exc:
            messagebox.showerror("No se pudo crear", str(exc))
            return
        self.capturing = False
        self.capture_index = None
        self.current_view = "rifa"
        self.current_tab = "captura"
        self.render()

    # ---------------------------------------------------------- vista de rifa
    def build_rifa_view(self):
        p = self.palette
        tabs = tk.Frame(self.container, bg=p["bg"], padx=16, pady=10)
        tabs.pack(fill="x")
        options = [("captura", "📝 Captura"), ("vista", "📄 Vista CSV"),
                   ("resumen", "📊 Resumen"), ("agregar", "➕ Agregar boletos")]
        for key, text in options:
            kind = "accent" if key == self.current_tab else "ghost"
            self.button(tabs, text, lambda k=key: self.switch_tab(k),
                        kind=kind).pack(side="left", padx=(0, 8))

        self.tab_body = tk.Frame(self.container, bg=p["bg"], padx=16, pady=4)
        self.tab_body.pack(fill="both", expand=True)

        builders = {"captura": self.build_capture_tab, "vista": self.build_view_tab,
                    "resumen": self.build_summary_tab, "agregar": self.build_add_tab}
        builders[self.current_tab]()

    def switch_tab(self, key):
        if key == self.current_tab:
            return
        if self.capturing and self.current_tab == "captura":
            self._capture_backup = self._read_capture_form()
        self.current_tab = key
        self.render()

    # ------------------------------------------------------------ tab captura
    def build_capture_tab(self):
        p = self.palette
        outer, card = self.card(self.tab_body)
        outer.pack(pady=6, fill="x")

        total = len(self.rifa.rows)
        empty = total - len([r for r in self.rifa.rows if self.rifa.is_filled(r)])

        if not self.capturing:
            self.label(card, "Ciclo de captura", size=14, bold=True,
                       bg=p["surface"]).pack(anchor="w")
            self.label(card,
                       f"Boletos vacíos por llenar: {empty} de {total}. "
                       "Inicia el ciclo para capturarlos uno por uno; puedes "
                       "detenerlo cuando quieras.",
                       color=p["subtext"], bg=p["surface"],
                       wraplength=640, justify="left").pack(anchor="w", pady=(4, 14))
            self.button(card, "▶  Iniciar ciclo", self.start_capture,
                        kind="success").pack(anchor="w")
            return

        row = self.rifa.rows[self.capture_index]
        self.label(card, f"Boleto  #{row[TICKET_COL]}", size=18, bold=True,
                   bg=p["surface"], color=p["accent"]).pack(anchor="w")
        self.label(card, f"Vacíos restantes: {empty} de {total}",
                   color=p["subtext"], bg=p["surface"]).pack(anchor="w", pady=(0, 10))

        form = tk.Frame(card, bg=p["surface"])
        form.pack(anchor="w", fill="x")
        self.capture_vars = {}
        backup = self._capture_backup or {}
        self._capture_backup = None
        first_entry = None
        for i, field in enumerate(self.rifa.fields):
            self.label(form, field + ":", bg=p["surface"]).grid(
                row=i, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=backup.get(field, row.get(field, "")))
            self.capture_vars[field] = var
            e = self.entry(form, var, width=40)
            e.grid(row=i, column=1, sticky="w", pady=4, padx=(10, 0))
            if first_entry is None:
                first_entry = e
        if first_entry is not None:
            first_entry.focus_set()

        actions = tk.Frame(card, bg=p["surface"])
        actions.pack(anchor="w", pady=(16, 0))
        self.button(actions, "💾 Guardar y siguiente  (Enter)",
                    self.save_and_next, kind="accent").pack(side="left")
        self.button(actions, "⏭ Omitir", self.skip_ticket,
                    kind="ghost").pack(side="left", padx=8)
        self.button(actions, "⏹ Detener ciclo",
                    lambda: self.stop_capture(save_current=False),
                    kind="danger").pack(side="left")
        self.bind("<Return>", lambda _e: self.save_and_next())

    def _read_capture_form(self):
        if not getattr(self, "capture_vars", None):
            return {}
        return {f: v.get() for f, v in self.capture_vars.items()}

    def start_capture(self, at_index=None):
        if at_index is None:
            at_index = self.rifa.next_empty_index()
            if at_index is None:
                messagebox.showinfo("Rifa completa",
                                    "¡Todos los boletos ya están llenos! 🎉")
                return
        self.capturing = True
        self.capture_index = at_index
        self.current_tab = "captura"
        self.render()

    def stop_capture(self, save_current=False):
        if save_current and self.capturing:
            self._store_form_into_row()
        self.capturing = False
        self.capture_index = None
        self._capture_backup = None
        self.unbind("<Return>")
        if self.current_view == "rifa":
            self.render()

    def _store_form_into_row(self):
        row = self.rifa.rows[self.capture_index]
        for field, var in self.capture_vars.items():
            row[field] = var.get().strip()
        self.rifa.save()

    def save_and_next(self):
        if not self.capturing:
            return
        values = self._read_capture_form()
        if not any(v.strip() for v in values.values()):
            messagebox.showwarning(
                "Boleto vacío",
                "Llena al menos un campo, o usa «Omitir» para saltarlo.")
            return
        self._store_form_into_row()
        nxt = self.rifa.next_empty_index(after=self.capture_index)
        if nxt is None:
            self.stop_capture()
            messagebox.showinfo("Rifa completa",
                                "¡Todos los boletos quedaron llenos! 🎉")
            return
        self.capture_index = nxt
        self.render()

    def skip_ticket(self):
        nxt = self.rifa.next_empty_index(after=self.capture_index)
        if nxt is None or nxt == self.capture_index:
            messagebox.showinfo("Sin más boletos",
                                "No hay otro boleto vacío al cual saltar.")
            return
        self.capture_index = nxt
        self.render()

    # -------------------------------------------------------------- tab vista
    def build_view_tab(self):
        p = self.palette
        info = self.label(self.tab_body,
                          "Doble clic sobre una fila para editar ese boleto.",
                          color=p["subtext"])
        info.pack(anchor="w", pady=(4, 6))

        frame = tk.Frame(self.tab_body, bg=p["border"], padx=1, pady=1)
        frame.pack(fill="both", expand=True, pady=(0, 10))
        cols = [TICKET_COL] + self.rifa.fields
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=90 if c == TICKET_COL else 160, anchor="w")
        tree.tag_configure("filled", background=p["row_filled"],
                           foreground=p["text"])
        for i, row in enumerate(self.rifa.rows):
            tags = ("filled",) if self.rifa.is_filled(row) else ()
            tree.insert("", "end", iid=str(i),
                        values=[row[c] for c in cols], tags=tags)

        def on_double(_event):
            sel = tree.selection()
            if sel:
                self.start_capture(at_index=int(sel[0]))

        tree.bind("<Double-1>", on_double)

    # ------------------------------------------------------------ tab resumen
    def build_summary_tab(self):
        p = self.palette
        sold = self.rifa.sold_numbers()
        empty = self.rifa.empty_numbers()
        total = len(self.rifa.rows)
        pct = (len(sold) / total * 100) if total else 0

        stats = tk.Frame(self.tab_body, bg=p["bg"])
        stats.pack(fill="x", pady=(6, 10))
        for title, value, color in (
                ("Total de boletos", str(total), p["text"]),
                ("Vendidos / llenados", str(len(sold)), p["success"]),
                ("Vacíos / faltantes", str(total - len(sold)), p["danger"]),
                ("Avance", f"{pct:.1f} %", p["accent"])):
            outer, card = self.card(stats)
            outer.pack(side="left", padx=(0, 10), fill="x", expand=True)
            self.label(card, title, color=p["subtext"],
                       bg=p["surface"]).pack(anchor="w")
            self.label(card, value, size=18, bold=True, color=color,
                       bg=p["surface"]).pack(anchor="w")

        for title, nums, color in (
                ("✅ Números vendidos", sold, p["success"]),
                ("⭕ Números que faltan", empty, p["danger"])):
            outer, card = self.card(self.tab_body)
            outer.pack(fill="both", expand=True, pady=(0, 10))
            self.label(card, f"{title} ({len(nums)})", bold=True, size=11,
                       color=color, bg=p["surface"]).pack(anchor="w", pady=(0, 4))
            text = tk.Text(card, height=4, wrap="word", relief="flat",
                           bg=p["surface"], fg=p["text"],
                           highlightthickness=0, font=("TkDefaultFont", 10))
            text.insert("1.0", compress_numbers(nums))
            text.configure(state="disabled")
            text.pack(fill="both", expand=True)

    # ------------------------------------------------------------ tab agregar
    def build_add_tab(self):
        p = self.palette
        outer, card = self.card(self.tab_body)
        outer.pack(pady=6, anchor="w")

        nums = self.rifa.numeric_tickets()
        current_max = max(nums) if nums else 0
        self.label(card, "Agregar más números de boleto", size=14, bold=True,
                   bg=p["surface"]).grid(row=0, column=0, columnspan=4,
                                         sticky="w", pady=(0, 4))
        self.label(card,
                   f"Boleto más alto actual: {current_max}. Los números que ya "
                   "existan en la rifa se omiten automáticamente.",
                   color=p["subtext"], bg=p["surface"], wraplength=560,
                   justify="left").grid(row=1, column=0, columnspan=4,
                                        sticky="w", pady=(0, 14))

        self.label(card, "Del número:", bg=p["surface"]).grid(
            row=2, column=0, sticky="w")
        self.add_start = tk.StringVar(value=str(current_max + 1))
        self.entry(card, self.add_start, width=8).grid(
            row=2, column=1, sticky="w", padx=(8, 16))
        self.label(card, "al:", bg=p["surface"]).grid(row=2, column=2, sticky="w")
        self.add_end = tk.StringVar(value=str(current_max + 50))
        self.entry(card, self.add_end, width=8).grid(
            row=2, column=3, sticky="w", padx=(8, 0))

        self.button(card, "➕ Agregar boletos", self.do_add_tickets,
                    kind="accent").grid(row=3, column=0, columnspan=4,
                                        sticky="w", pady=(16, 0))

    def do_add_tickets(self):
        try:
            start = int(self.add_start.get())
            end = int(self.add_end.get())
        except ValueError:
            messagebox.showwarning("Rango inválido",
                                   "Escribe números válidos para el rango.")
            return
        if end < start:
            messagebox.showwarning("Rango inválido",
                                   "El número final debe ser mayor o igual al inicial.")
            return
        added = self.rifa.add_range(start, end)
        if added:
            messagebox.showinfo("Boletos agregados",
                                f"Se agregaron {added} boletos nuevos.")
        else:
            messagebox.showinfo("Sin cambios",
                                "Todos los números de ese rango ya existían.")
        self.render()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
