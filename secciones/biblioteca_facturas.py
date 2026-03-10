"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Sección de facturas/recibos. Lista los recibos generados,
                 muestra su contenido formateado y permite descargar a
                 cualquier ubicación elegida por el usuario.
Autor/a:         Luis Villegas Rivera
Clases:
    - SeccionFacturas : Panel tkinter de visualización de recibos.
"""

import tkinter as tk
from tkinter import filedialog
import os
import shutil

from secciones.biblioteca_gestion_libros import (
    aplicar_tema,
    COLOR_BG, COLOR_CARD, COLOR_CARD2, COLOR_GOLD, COLOR_GOLD_DIM,
    COLOR_TEXT, COLOR_DIM, COLOR_ERROR, COLOR_SUCCESS,
    FONT_TITLE, FONT_LABEL, FONT_SMALL, FONT_BTN,
)
from secciones.biblioteca_ajustes import T, ConfigApp

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIBOS_DIR = os.path.join(BASE_DIR, "recibos")

# ── Traducciones ─────────────────────────────────────────────
_TX = {
    "es": {
        "cab":          "🧾  Facturas y Recibos",
        "sin_recibos":  "No hay recibos generados todavía.",
        "sel_recibo":   "Selecciona un recibo de la lista",
        "descargar":    "⬇  Descargar recibo",
        "guardado_ok":  "Recibo guardado correctamente.",
        "guardado_err": "Error al guardar el recibo.",
        "filtrar":      "Filtrar...",
        "num_recibos":  "recibo(s)",
    },
    "en": {
        "cab":          "🧾  Invoices & Receipts",
        "sin_recibos":  "No receipts have been generated yet.",
        "sel_recibo":   "Select a receipt from the list",
        "descargar":    "⬇  Download receipt",
        "guardado_ok":  "Receipt saved successfully.",
        "guardado_err": "Error saving the receipt.",
        "filtrar":      "Filter...",
        "num_recibos":  "receipt(s)",
    },
}

def _t(clave: str) -> str:
    idioma = ConfigApp.get("idioma") or "es"
    return _TX.get(idioma, _TX["es"]).get(clave, clave)


# ═══════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════
class SeccionFacturas:
    """
    Panel de facturas/recibos:
    - Panel izquierdo: lista filtrable de archivos en /recibos/
    - Panel derecho: visor del contenido formateado
    - Botón descargar: copia el archivo a la ruta elegida por el usuario
    """

    def __init__(self, parent: tk.Widget, db_path: str, usuario):
        aplicar_tema()
        self.db_path      = db_path
        self.usuario      = usuario
        self._ruta_activa = None   # ruta completa del recibo seleccionado

        c = ConfigApp.colores()
        self._bg      = c["bg"]
        self._card    = c["card"]
        self._card2   = c.get("card2", c["card"])
        self._gold    = c["acento"]
        self._golddim = c["acento_dim"]
        self._text    = c["text"]
        self._dim     = c["dim"]
        self._err     = c.get("error", "#c45a3a")
        self._ok      = c.get("success", "#4a8c5a")

        self.frame = tk.Frame(parent, bg=self._bg)
        self._build_ui()

    # ── Construcción UI ─────────────────────────────────────
    def _build_ui(self):
        bg, card, gold, golddim = self._bg, self._card, self._gold, self._golddim
        text, dim = self._text, self._dim

        # ── Cabecera ──
        cab = tk.Frame(self.frame, bg=card, height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text=T("cab_facturas", "🧾  Facturas y Recibos"),
                 font=FONT_TITLE, bg=card, fg=gold).pack(side="left", padx=24, pady=10)
        tk.Frame(self.frame, height=1, bg=golddim).pack(fill="x")

        # ── Cuerpo principal (panel izq + panel der) ──
        body = tk.Frame(self.frame, bg=bg)
        body.pack(fill="both", expand=True, padx=20, pady=18)

        # ── Panel izquierdo: lista ──────────────────────────
        left = tk.Frame(body, bg=card, width=280)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        # Barra de filtro
        filtro_frame = tk.Frame(left, bg=card)
        filtro_frame.pack(fill="x", padx=10, pady=(12, 6))
        self._var_filtro = tk.StringVar()
        self._var_filtro.trace_add("write", lambda *_: self._actualizar_lista())
        entry_filtro = tk.Entry(
            filtro_frame, textvariable=self._var_filtro,
            font=("Georgia", 12), bg=self._card2, fg=text,
            insertbackground=gold, relief="flat",
            highlightthickness=1, highlightbackground=golddim,
            highlightcolor=gold
        )
        entry_filtro.pack(fill="x", ipady=5)
        entry_filtro.insert(0, _t("filtrar"))
        entry_filtro.config(fg=dim)
        entry_filtro.bind("<FocusIn>",  lambda e: self._focus_filtro(entry_filtro, True))
        entry_filtro.bind("<FocusOut>", lambda e: self._focus_filtro(entry_filtro, False))

        # Contador
        self._lbl_count = tk.Label(left, text="", font=("Georgia", 10),
                                   bg=card, fg=dim)
        self._lbl_count.pack(anchor="w", padx=12)

        # Separador
        tk.Frame(left, height=1, bg=golddim).pack(fill="x", padx=10, pady=4)

        # Lista con scroll
        list_frame = tk.Frame(left, bg=card)
        list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 10))

        scroll = tk.Scrollbar(list_frame, orient="vertical", bg=card,
                               troughcolor=self._card2, relief="flat", width=8)
        self._listbox = tk.Listbox(
            list_frame, yscrollcommand=scroll.set,
            font=("Georgia", 12), bg=self._card2, fg=text,
            selectbackground=golddim, selectforeground=text,
            activestyle="none", relief="flat", bd=0,
            highlightthickness=0, cursor="hand2"
        )
        scroll.config(command=self._listbox.yview)
        self._listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # ── Panel derecho: visor ────────────────────────────
        right = tk.Frame(body, bg=bg)
        right.pack(side="left", fill="both", expand=True)

        # Toolbar derecho: nombre archivo + botón descargar
        toolbar = tk.Frame(right, bg=card, height=44)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        self._lbl_nombre = tk.Label(
            toolbar, text="", font=("Georgia", 11, "italic"),
            bg=card, fg=dim)
        self._lbl_nombre.pack(side="left", padx=16, pady=10)

        self._btn_descargar = tk.Button(
            toolbar, text=_t("descargar"),
            font=("Georgia", 12, "bold"),
            bg=golddim, fg=text,
            activebackground=gold, activeforeground="#000",
            relief="flat", bd=0, cursor="hand2",
            state="disabled",
            command=self._descargar
        )
        self._btn_descargar.pack(side="right", padx=12, pady=6, ipadx=14, ipady=2)
        self._btn_descargar.bind("<Enter>", lambda _: self._btn_descargar.config(
            bg=gold, fg="#000") if self._ruta_activa else None)
        self._btn_descargar.bind("<Leave>", lambda _: self._btn_descargar.config(
            bg=golddim, fg=text))

        tk.Frame(right, height=1, bg=golddim).pack(fill="x")

        # Canvas visor con scroll
        visor_frame = tk.Frame(right, bg=bg)
        visor_frame.pack(fill="both", expand=True)

        vscroll = tk.Scrollbar(visor_frame, orient="vertical",
                               bg=self._card2, troughcolor=bg,
                               relief="flat", width=8)
        vscroll.pack(side="right", fill="y")

        self._canvas = tk.Canvas(
            visor_frame, bg=bg, bd=0,
            highlightthickness=0,
            yscrollcommand=vscroll.set
        )
        self._canvas.pack(side="left", fill="both", expand=True)
        vscroll.config(command=self._canvas.yview)

        # Frame interior que vive dentro del canvas
        self._visor_inner = tk.Frame(self._canvas, bg=bg)
        self._canvas_win  = self._canvas.create_window(
            (0, 0), window=self._visor_inner, anchor="n")

        def _on_configure(e):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            # Centrar horizontalmente
            cw = self._canvas.winfo_width()
            self._canvas.coords(self._canvas_win, cw // 2, 0)

        def _on_canvas_resize(e):
            cw = e.width
            self._canvas.coords(self._canvas_win, cw // 2, 0)

        self._visor_inner.bind("<Configure>", _on_configure)
        self._canvas.bind("<Configure>", _on_canvas_resize)
        self._canvas.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))
        self._visor_inner.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))

        # Mensaje de feedback
        self._lbl_msg = tk.Label(right, text="", font=("Georgia", 11, "italic"),
                                  bg=bg, fg=self._ok)
        self._lbl_msg.pack(anchor="e", padx=18, pady=(4, 0))

        # Placeholder inicial
        self._mostrar_placeholder()

        # Cargar lista
        self._actualizar_lista()

    # ── Filtro entrada ───────────────────────────────────────
    def _focus_filtro(self, entry, focused):
        placeholder = _t("filtrar")
        if focused:
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.config(fg=self._text)
            entry.config(highlightbackground=self._gold, highlightcolor=self._gold)
        else:
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(fg=self._dim)
            entry.config(highlightbackground=self._golddim)

    # ── Lista de recibos ─────────────────────────────────────
    def _es_admin(self) -> bool:
        """Comprueba en la BD si el usuario activo es administrador."""
        try:
            import sqlite3 as _sq
            conn = _sq.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT rol FROM usuarios WHERE nombre = ? LIMIT 1",
                        (str(self.usuario),))
            fila = cur.fetchone()
            conn.close()
            return fila and fila[0] == "admin"
        except Exception:
            return False

    def _id_usuario_activo(self) -> str | None:
        """Obtiene el id_usuario del usuario activo desde la BD."""
        try:
            import sqlite3 as _sq
            conn = _sq.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT id_usuario FROM usuarios WHERE nombre = ? LIMIT 1",
                        (str(self.usuario),))
            fila = cur.fetchone()
            conn.close()
            return str(fila[0]) if fila else None
        except Exception:
            return None

    def _listar_archivos(self) -> list:
        if not os.path.isdir(RECIBOS_DIR):
            return []
        archivos = [f for f in os.listdir(RECIBOS_DIR) if f.endswith(".txt")]
        # Socios solo ven sus propios recibos
        # Nombre: recibo_{id_prestamo}_{id_usuario}_{nombre}_{fecha}.txt
        if not self._es_admin():
            uid = self._id_usuario_activo()
            if uid:
                archivos = [f for f in archivos
                            if f.startswith("recibo_") and
                            len(f.split("_")) > 2 and f.split("_")[2] == uid]
            else:
                archivos = []
        return sorted(archivos, reverse=True)

    def _actualizar_lista(self, *_):
        if not hasattr(self, "_listbox"):
            return
        filtro = self._var_filtro.get().strip().lower()
        placeholder = _t("filtrar").lower()
        if filtro == placeholder:
            filtro = ""

        archivos = self._listar_archivos()
        if filtro:
            archivos = [f for f in archivos if filtro in f.lower()]

        self._archivos_visibles = archivos
        self._listbox.delete(0, "end")

        for f in archivos:
            # recibo_{id_prestamo}_{id_usuario}_{nombre}_{fecha}.txt
            base = os.path.splitext(f)[0]
            partes = base.split("_", 4)  # [recibo, idp, idu, nombre, fecha_hora]
            if len(partes) >= 5:
                idp   = partes[1].lstrip("0") or "0"
                nombre = partes[3].replace("_", " ")
                fecha  = partes[4][:8]  # YYYYMMDD
                try:
                    from datetime import datetime as _dt
                    fecha_fmt = _dt.strptime(fecha, "%Y%m%d").strftime("%d/%m/%Y")
                except Exception:
                    fecha_fmt = fecha
                label = f"  #{idp}  {nombre}  —  {fecha_fmt}"
            else:
                label = f"  {base}"
            self._listbox.insert("end", label)

        n = len(archivos)
        self._lbl_count.config(text=f"{n} {_t('num_recibos')}")

        if not archivos:
            self._mostrar_placeholder()
            self._btn_descargar.config(state="disabled")
            self._ruta_activa = None

    # ── Selección ────────────────────────────────────────────
    def _on_select(self, _event=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._archivos_visibles):
            return
        nombre = self._archivos_visibles[idx]
        ruta   = os.path.join(RECIBOS_DIR, nombre)
        self._ruta_activa = ruta
        self._lbl_nombre.config(text=nombre, fg=self._text)
        self._btn_descargar.config(state="normal")
        self._cargar_recibo(ruta)
        self._lbl_msg.config(text="")

    # ── Visor de contenido ───────────────────────────────────
    def _limpiar_canvas(self):
        for w in self._visor_inner.winfo_children():
            w.destroy()

    def _bind_scroll(self, widget):
        widget.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))
        for child in widget.winfo_children():
            self._bind_scroll(child)

    def _mostrar_placeholder(self):
        self._limpiar_canvas()
        msg = _t("sin_recibos") if not self._listar_archivos() else _t("sel_recibo")
        outer = tk.Frame(self._visor_inner, bg=self._bg)
        outer.pack(pady=80, padx=40)
        tk.Label(outer, text="🧾", font=("Georgia", 48),
                 bg=self._bg, fg=self._golddim).pack()
        tk.Label(outer, text=msg, font=("Georgia", 12, "italic"),
                 bg=self._bg, fg=self._dim,
                 wraplength=320, justify="center").pack(pady=(12, 0))
        self._lbl_nombre.config(text="", fg=self._dim)
        self._canvas.yview_moveto(0)

    def _parse_recibo(self, ruta: str) -> dict:
        data = {
            "id_prestamo": "", "fecha": "",
            "socio":      {"id": "", "nombre": "", "correo": "", "telefono": ""},
            "libro":      {"isbn": "", "titulo": "", "autor": ""},
            "devolucion": {"fecha": "", "plazo": ""},
        }
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                texto = f.read()
        except Exception:
            return data

        def get(clave):
            for line in texto.splitlines():
                s = line.strip().lstrip("║").strip()
                if ":" in s:
                    k, _, v = s.partition(":")
                    if k.strip().lower() == clave.strip().lower():
                        return v.strip()
            return ""

        data["id_prestamo"] = (get("Nº Préstamo") or get("Nº Préstamo")).lstrip("#").strip()
        data["fecha"]       = get("Fecha emisión") or get("Fecha")
        data["socio"]["id"]       = get("ID")
        data["socio"]["nombre"]   = get("Nombre")
        data["socio"]["correo"]   = get("Correo")
        data["socio"]["telefono"] = get("Teléfono")
        data["libro"]["isbn"]     = get("ISBN")
        data["libro"]["titulo"]   = get("Título")
        data["libro"]["autor"]    = get("Autor")
        data["devolucion"]["fecha"] = get("Fecha límite")
        data["devolucion"]["plazo"] = get("Plazo") or "15 días naturales"
        return data

    def _cargar_recibo(self, ruta: str):
        self._limpiar_canvas()
        data = self._parse_recibo(ruta)
        self._renderizar_recibo(data)
        self._canvas.yview_moveto(0)

    def _renderizar_recibo(self, data: dict):
        bg      = self._bg
        card    = self._card
        card2   = self._card2
        gold    = self._gold
        golddim = self._golddim
        text    = self._text
        dim     = self._dim
        err     = self._err
        CARD_W  = 640

        outer = tk.Frame(self._visor_inner, bg=bg)
        outer.pack(pady=28, padx=20, anchor="n")

        def sep(parent, color=golddim, h=1, pady_val=0):
            tk.Frame(parent, bg=color, height=h, width=CARD_W).pack(pady=pady_val)

        def kv_row(parent, icon, label, value, vc=None):
            row = tk.Frame(parent, bg=card, width=CARD_W)
            row.pack(fill="x", padx=24, pady=4)
            row.pack_propagate(False)
            tk.Label(row, text=icon, font=("Segoe UI Emoji", 14),
                     bg=card, fg=golddim, width=2).pack(side="left")
            tk.Label(row, text=label, font=("Georgia", 13),
                     bg=card, fg=dim, anchor="w", width=15).pack(side="left", padx=(6, 0))
            tk.Label(row, text=value or "—", font=("Georgia", 13, "bold"),
                     bg=card, fg=vc or text, anchor="w").pack(side="left", padx=(8, 0))
            self._bind_scroll(row)

        def sec_head(parent, icon, titulo, accent=gold):
            f = tk.Frame(parent, bg=card2, width=CARD_W)
            f.pack(fill="x")
            # left accent bar
            tk.Frame(f, bg=accent, width=5).pack(side="left", fill="y")
            inner = tk.Frame(f, bg=card2)
            inner.pack(side="left", padx=16, pady=11)
            tk.Label(inner, text=icon, font=("Segoe UI Emoji", 14),
                     bg=card2, fg=accent).pack(side="left", padx=(0, 8))
            tk.Label(inner, text=titulo, font=("Georgia", 13, "bold"),
                     bg=card2, fg=accent).pack(side="left")
            self._bind_scroll(f)

        def space(parent, h=10):
            tk.Frame(parent, bg=card, height=h, width=CARD_W).pack()

        # ── CABECERA ──────────────────────────────────────────
        cab = tk.Frame(outer, bg=card, width=CARD_W)
        cab.pack()
        cab.pack_propagate(False)
        tk.Frame(cab, bg=gold, height=4, width=CARD_W).pack(fill="x")  # borde superior
        tk.Label(cab, text="✦  EL ARCHIVO DE LOS MUNDOS  ✦",
                 font=("Georgia", 18, "bold"),
                 bg=card, fg=gold).pack(pady=(22, 4))
        tk.Label(cab, text="C O M P R O B A N T E   D E   P R É S T A M O",
                 font=("Georgia", 11),
                 bg=card, fg=dim).pack()
        sep(cab, golddim, pady_val=16)

        # Número grande + fecha
        mid = tk.Frame(cab, bg=card)
        mid.pack(pady=(0, 22))
        num_f = tk.Frame(mid, bg=card)
        num_f.pack(side="left", padx=36)
        tk.Label(num_f, text="PRÉSTAMO", font=("Georgia", 11),
                 bg=card, fg=dim).pack()
        tk.Label(num_f, text=f"# {data['id_prestamo'] or '—'}",
                 font=("Georgia", 34, "bold"),
                 bg=card, fg=gold).pack()
        tk.Frame(mid, bg=golddim, width=1, height=70).pack(side="left", fill="y", padx=24)
        dt_f = tk.Frame(mid, bg=card)
        dt_f.pack(side="left", padx=24)
        tk.Label(dt_f, text="FECHA DE EMISIÓN", font=("Georgia", 11),
                 bg=card, fg=dim).pack(anchor="w")
        tk.Label(dt_f, text=data["fecha"] or "—",
                 font=("Georgia", 16, "bold"),
                 bg=card, fg=text).pack(anchor="w", pady=(6, 0))
        self._bind_scroll(cab)

        # ── SOCIO ─────────────────────────────────────────────
        sep(outer, golddim)
        sec_head(outer, "👤", "DATOS DEL SOCIO")
        s_card = tk.Frame(outer, bg=card, width=CARD_W)
        s_card.pack()
        space(s_card, 6)
        kv_row(s_card, "🆔", "ID socio",  data["socio"]["id"])
        kv_row(s_card, "✏", "Nombre",    data["socio"]["nombre"], gold)
        kv_row(s_card, "✉", "Correo",    data["socio"]["correo"])
        kv_row(s_card, "📱", "Teléfono", data["socio"]["telefono"])
        space(s_card, 12)
        self._bind_scroll(s_card)

        # ── LIBRO ─────────────────────────────────────────────
        sep(outer, golddim)
        sec_head(outer, "📖", "LIBRO PRESTADO")
        l_card = tk.Frame(outer, bg=card, width=CARD_W)
        l_card.pack()
        space(l_card, 6)
        kv_row(l_card, "🔢", "ISBN",   data["libro"]["isbn"])
        kv_row(l_card, "📚", "Título", data["libro"]["titulo"])
        kv_row(l_card, "✍", "Autor",  data["libro"]["autor"])
        space(l_card, 12)
        self._bind_scroll(l_card)

        # ── DEVOLUCIÓN ────────────────────────────────────────
        sep(outer, golddim)
        sec_head(outer, "🗓", "DEVOLUCIÓN", accent=err)
        d_card = tk.Frame(outer, bg=card, width=CARD_W)
        d_card.pack()
        space(d_card, 6)
        kv_row(d_card, "⚠", "Fecha límite", data["devolucion"]["fecha"], err)
        kv_row(d_card, "⏱", "Plazo",        data["devolucion"]["plazo"])
        space(d_card, 12)
        self._bind_scroll(d_card)

        # ── PIE ───────────────────────────────────────────────
        sep(outer, gold)
        pie = tk.Frame(outer, bg=card, width=CARD_W)
        pie.pack()
        tk.Label(pie,
                 text="Conserve este comprobante como justificante del préstamo.",
                 font=("Georgia", 12, "italic"),
                 bg=card, fg=dim, wraplength=CARD_W - 48, justify="center").pack(pady=14)
        tk.Label(pie, text="✦", font=("Georgia", 14),
                 bg=card, fg=golddim).pack(pady=(0, 16))
        tk.Frame(pie, bg=gold, height=4, width=CARD_W).pack(fill="x")  # borde inferior
        self._bind_scroll(pie)
        self._bind_scroll(outer)


        # ── Descarga ─────────────────────────────────────────────
    def _descargar(self):
        if not self._ruta_activa or not os.path.isfile(self._ruta_activa):
            return

        nombre_sugerido = os.path.basename(self._ruta_activa)
        destino = filedialog.asksaveasfilename(
            title=_t("descargar"),
            initialfile=nombre_sugerido,
            defaultextension=".txt",
            filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if not destino:
            return  # usuario canceló

        try:
            shutil.copy2(self._ruta_activa, destino)
            self._lbl_msg.config(text=f"✓  {_t('guardado_ok')}", fg=self._ok)
            self.frame.after(4000, lambda: self._lbl_msg.config(text=""))
        except Exception as e:
            self._lbl_msg.config(text=f"✗  {_t('guardado_err')}  ({e})", fg=self._err)

    # ── Ciclo de vida ────────────────────────────────────────
    def mostrar(self):
        self.frame.pack(fill="both", expand=True)
        self._actualizar_lista()

    def ocultar(self):
        self.frame.pack_forget()