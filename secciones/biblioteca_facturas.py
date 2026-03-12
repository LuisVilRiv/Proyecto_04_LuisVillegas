"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Sección de facturas/recibos en PDF.
                 Lista los PDFs generados, los muestra en un visor
                 embebido y permite descargar a la ubicación elegida.
Autor/a:         Luis Villegas Rivera
Fecha:           2026-03-10
"""

import tkinter as tk
from tkinter import filedialog, ttk
import os
import shutil
import sqlite3
from datetime import datetime

from secciones.biblioteca_gestion_libros import (
    aplicar_tema,
    COLOR_BG, COLOR_CARD, COLOR_CARD2, COLOR_GOLD, COLOR_GOLD_DIM,
    COLOR_TEXT, COLOR_DIM, COLOR_ERROR, COLOR_SUCCESS,
    FONT_TITLE, FONT_SMALL, FONT_BTN,
)
from secciones.biblioteca_ajustes import T, ConfigApp

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIBOS_DIR = os.path.join(BASE_DIR, "recibos")
# ── Traducciones ──────────────────────────────────────────────────────────
_TX = {
    "es": {
        "cab":              "🧾  Facturas y Recibos",
        "sin_recibos":      "No hay recibos generados todavía.",
        "sel_recibo":       "Selecciona un recibo de la lista",
        "descargar":        "⬇  Descargar recibo",
        "guardado_ok":      "Recibo guardado correctamente.",
        "guardado_err":     "Error al guardar el recibo.",
        "filtrar":          "Filtrar...",
        "num_recibos":      "recibo(s)",
        "abrir_externo":    "Abrir en visor PDF",
        # tarjeta
        "titulo_bib":       "✦  EL ARCHIVO DE LOS MUNDOS  ✦",
        "subtitulo":        "COMPROBANTE DE PRÉSTAMO",
        "lbl_prestamo":     "PRÉSTAMO",
        "lbl_emision":      "FECHA DE EMISIÓN",
        "sec_socio":        "DATOS DEL SOCIO",
        "sec_libro":        "LIBRO PRESTADO",
        "sec_devolucion":   "DEVOLUCIÓN",
        "lbl_id":           "ID socio",
        "lbl_nombre":       "Nombre",
        "lbl_correo":       "Correo",
        "lbl_telefono":     "Teléfono",
        "lbl_isbn":         "ISBN",
        "lbl_titulo":       "Título",
        "lbl_autor":        "Autor",
        "lbl_fecha_lim":    "Fecha límite",
        "lbl_plazo":        "Plazo",
        "plazo_val":        "15 días naturales",
        "pie":              "Conserve este comprobante como justificante del préstamo.",
        "pie_info":         "📄  Recibo en formato PDF — usa 'Abrir' para verlo o 'Descargar' para guardarlo.",
        # sello devolución
        "devuelto":         "✓  DEVUELTO",
        "devuelto_retraso": "✕  DEVUELTO CON RETRASO",
        "retraso_dias":     "días de retraso",
        "devuelto_el":      "el",
    },
    "en": {
        "cab":              "🧾  Invoices & Receipts",
        "sin_recibos":      "No receipts have been generated yet.",
        "sel_recibo":       "Select a receipt from the list",
        "descargar":        "⬇  Download receipt",
        "guardado_ok":      "Receipt saved successfully.",
        "guardado_err":     "Error saving the receipt.",
        "filtrar":          "Filter...",
        "num_recibos":      "receipt(s)",
        "abrir_externo":    "Open in PDF viewer",
        # card
        "titulo_bib":       "✦  THE ARCHIVE OF WORLDS  ✦",
        "subtitulo":        "LOAN RECEIPT",
        "lbl_prestamo":     "LOAN",
        "lbl_emision":      "ISSUE DATE",
        "sec_socio":        "MEMBER DETAILS",
        "sec_libro":        "BORROWED BOOK",
        "sec_devolucion":   "RETURN",
        "lbl_id":           "Member ID",
        "lbl_nombre":       "Name",
        "lbl_correo":       "Email",
        "lbl_telefono":     "Phone",
        "lbl_isbn":         "ISBN",
        "lbl_titulo":       "Title",
        "lbl_autor":        "Author",
        "lbl_fecha_lim":    "Due date",
        "lbl_plazo":        "Period",
        "plazo_val":        "15 calendar days",
        "pie":              "Keep this receipt as proof of your loan.",
        "pie_info":         "📄  PDF receipt — use 'Open' to view or 'Download' to save.",
        # return stamp
        "devuelto":         "✓  RETURNED",
        "devuelto_retraso": "✕  RETURNED LATE",
        "retraso_dias":     "days late",
        "devuelto_el":      "on",
    },
}

def _t(c: str) -> str:
    idioma = ConfigApp.get("idioma") or "es"
    return _TX.get(idioma, _TX["es"]).get(c, c)


# ═══════════════════════════════════════════════════════════════════════════
class SeccionFacturas:
    """
    Panel de facturas/recibos PDF.
    - Izquierda : lista filtrable de archivos en /recibos/*.pdf
    - Derecha   : tarjeta con los datos del recibo + botones de acción
    """

    def __init__(self, parent: tk.Widget, db_path: str, usuario):
        aplicar_tema()
        self.db_path      = db_path
        self.usuario      = usuario
        self._ruta_activa = None
        self._archivos_visibles: list = []
        self.frame = tk.Frame(parent, bg=COLOR_BG)
        self._build_ui()

    # ── Construcción UI ──────────────────────────────────────────────────
    def _build_ui(self):
        # Cabecera
        cab = tk.Frame(self.frame, bg=COLOR_CARD, height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text=T("cab_facturas", "🧾  Facturas y Recibos"),
                 font=FONT_TITLE, bg=COLOR_CARD, fg=COLOR_GOLD
                 ).pack(side="left", padx=24, pady=10)
        tk.Frame(self.frame, height=1, bg=COLOR_GOLD_DIM).pack(fill="x")

        body = tk.Frame(self.frame, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=20, pady=18)

        # ── Panel izquierdo: lista ──────────────────────────────────────
        left = tk.Frame(body, bg=COLOR_CARD, width=270)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        ff = tk.Frame(left, bg=COLOR_CARD)
        ff.pack(fill="x", padx=10, pady=(12, 4))
        self._var_filtro = tk.StringVar()
        self._var_filtro.trace_add("write", lambda *_: self._actualizar_lista())
        self._entry_filtro = tk.Entry(
            ff, textvariable=self._var_filtro,
            font=("Georgia", 11), bg=COLOR_CARD2, fg=COLOR_TEXT,
            insertbackground=COLOR_GOLD, relief="flat",
            highlightthickness=1, highlightbackground=COLOR_GOLD_DIM,
            highlightcolor=COLOR_GOLD
        )
        self._entry_filtro.pack(fill="x", ipady=5)
        self._entry_filtro.insert(0, _t("filtrar"))
        self._entry_filtro.config(fg=COLOR_DIM)
        self._entry_filtro.bind("<FocusIn>",  lambda e: self._focus_filtro(True))
        self._entry_filtro.bind("<FocusOut>", lambda e: self._focus_filtro(False))

        self._lbl_count = tk.Label(left, text="", font=("Georgia", 9),
                                   bg=COLOR_CARD, fg=COLOR_DIM)
        self._lbl_count.pack(anchor="w", padx=12)
        tk.Frame(left, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=8, pady=4)

        lf = tk.Frame(left, bg=COLOR_CARD)
        lf.pack(fill="both", expand=True, padx=6, pady=(0, 10))
        scroll = tk.Scrollbar(lf, orient="vertical", bg=COLOR_CARD,
                              troughcolor=COLOR_CARD2, relief="flat", width=7)
        self._listbox = tk.Listbox(
            lf, yscrollcommand=scroll.set,
            font=("Georgia", 11), bg=COLOR_CARD2, fg=COLOR_TEXT,
            selectbackground=COLOR_GOLD_DIM, selectforeground=COLOR_TEXT,
            activestyle="none", relief="flat", bd=0,
            highlightthickness=0, cursor="hand2"
        )
        scroll.config(command=self._listbox.yview)
        self._listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # ── Panel derecho: visor ────────────────────────────────────────
        right = tk.Frame(body, bg=COLOR_BG)
        right.pack(side="left", fill="both", expand=True)

        tb = tk.Frame(right, bg=COLOR_CARD, height=44)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        self._lbl_nombre = tk.Label(tb, text="", font=("Georgia", 10, "italic"),
                                    bg=COLOR_CARD, fg=COLOR_DIM)
        self._lbl_nombre.pack(side="left", padx=14, pady=10)

        self._btn_abrir = tk.Button(
            tb, text="🔍  " + _t("abrir_externo"),
            font=("Georgia", 10), bg=COLOR_CARD2, fg=COLOR_TEXT,
            relief="flat", bd=0, cursor="hand2", state="disabled",
            command=self._abrir_externo
        )
        self._btn_abrir.pack(side="right", padx=(4, 10), pady=6, ipadx=10, ipady=2)

        self._btn_descargar = tk.Button(
            tb, text=_t("descargar"),
            font=("Georgia", 11, "bold"),
            bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
            activebackground=COLOR_GOLD, activeforeground="#000",
            relief="flat", bd=0, cursor="hand2", state="disabled",
            command=self._descargar
        )
        self._btn_descargar.pack(side="right", padx=(10, 0), pady=6, ipadx=14, ipady=2)
        self._btn_descargar.bind("<Enter>",
            lambda _: self._btn_descargar.config(bg=COLOR_GOLD, fg="#000")
                      if self._ruta_activa else None)
        self._btn_descargar.bind("<Leave>",
            lambda _: self._btn_descargar.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))
        self._btn_abrir.bind("<Enter>",
            lambda _: self._btn_abrir.config(bg=COLOR_CARD)
                      if self._ruta_activa else None)
        self._btn_abrir.bind("<Leave>",
            lambda _: self._btn_abrir.config(bg=COLOR_CARD2))

        tk.Frame(right, height=1, bg=COLOR_GOLD_DIM).pack(fill="x")

        # Canvas con scroll para la tarjeta del recibo
        vf = tk.Frame(right, bg=COLOR_BG)
        vf.pack(fill="both", expand=True)
        vscroll = ttk.Scrollbar(vf, orient="vertical")
        vscroll.pack(side="right", fill="y")
        self._canvas = tk.Canvas(vf, bg=COLOR_BG, bd=0,
                                  highlightthickness=0,
                                  yscrollcommand=vscroll.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        vscroll.config(command=self._canvas.yview)
        self._inner = tk.Frame(self._canvas, bg=COLOR_BG)
        self._inner_win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        # Propagar ancho del canvas al frame interno para evitar superposición
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._inner_win, width=e.width))
        self._canvas.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))

        self._lbl_msg = tk.Label(right, text="", font=("Georgia", 10, "italic"),
                                  bg=COLOR_BG, fg=COLOR_SUCCESS)
        self._lbl_msg.pack(anchor="e", padx=18, pady=(4, 0))

        self._mostrar_placeholder()
        self._actualizar_lista()

    # ── Filtro ────────────────────────────────────────────────────────────
    def _focus_filtro(self, focused: bool):
        ph = _t("filtrar")
        if focused:
            if self._entry_filtro.get() == ph:
                self._entry_filtro.delete(0, "end")
                self._entry_filtro.config(fg=COLOR_TEXT)
            self._entry_filtro.config(highlightbackground=COLOR_GOLD)
        else:
            if not self._entry_filtro.get():
                self._entry_filtro.insert(0, ph)
                self._entry_filtro.config(fg=COLOR_DIM)
            self._entry_filtro.config(highlightbackground=COLOR_GOLD_DIM)

    # ── Lista ─────────────────────────────────────────────────────────────
    def _es_admin(self) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT rol FROM usuarios WHERE nombre=? LIMIT 1",
                        (str(self.usuario),))
            fila = cur.fetchone()
            conn.close()
            return bool(fila and fila[0] == "admin")
        except Exception:
            return False

    def _id_usuario_activo(self) -> str | None:
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT id_usuario FROM usuarios WHERE nombre=? LIMIT 1",
                        (str(self.usuario),))
            fila = cur.fetchone()
            conn.close()
            return str(fila[0]) if fila else None
        except Exception:
            return None

    def _listar_archivos(self) -> list:
        if not os.path.isdir(RECIBOS_DIR):
            return []
        archivos = [f for f in os.listdir(RECIBOS_DIR) if f.endswith(".pdf")]
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
        if filtro == _t("filtrar").lower():
            filtro = ""
        archivos = self._listar_archivos()
        if filtro:
            archivos = [f for f in archivos if filtro in f.lower()]
        self._archivos_visibles = archivos
        self._listbox.delete(0, "end")
        for f in archivos:
            base   = os.path.splitext(f)[0]
            partes = base.split("_", 4)
            if len(partes) >= 5:
                idp   = partes[1].lstrip("0") or "0"
                nom   = partes[3].replace("_", " ").title()
                ts    = partes[4][:8]
                try:
                    fecha = datetime.strptime(ts, "%Y%m%d").strftime("%d/%m/%Y")
                except Exception:
                    fecha = ts
                label = f"  #{idp}  {nom}  —  {fecha}"
            else:
                label = f"  {base}"
            self._listbox.insert("end", label)
        n = len(archivos)
        self._lbl_count.config(text=f"{n} {_t('num_recibos')}")
        if not archivos:
            self._mostrar_placeholder()
            self._btn_descargar.config(state="disabled")
            self._btn_abrir.config(state="disabled")
            self._ruta_activa = None

    # ── Selección ─────────────────────────────────────────────────────────
    def _on_select(self, _=None):
        sel = self._listbox.curselection()
        if not sel or sel[0] >= len(self._archivos_visibles):
            return
        nombre = self._archivos_visibles[sel[0]]
        ruta   = os.path.join(RECIBOS_DIR, nombre)
        self._ruta_activa = ruta
        self._lbl_nombre.config(text=nombre, fg=COLOR_TEXT)
        self._btn_descargar.config(state="normal")
        self._btn_abrir.config(state="normal")
        self._renderizar_tarjeta(nombre)
        self._lbl_msg.config(text="")

    # ── Visor ─────────────────────────────────────────────────────────────
    def _limpiar_visor(self):
        for w in self._inner.winfo_children():
            w.destroy()

    def _mostrar_placeholder(self):
        self._limpiar_visor()
        archivos = self._listar_archivos()
        msg = _t("sin_recibos") if not archivos else _t("sel_recibo")
        outer = tk.Frame(self._inner, bg=COLOR_BG)
        outer.pack(pady=80, padx=40)
        tk.Label(outer, text="🧾", font=("Georgia", 52),
                 bg=COLOR_BG, fg=COLOR_GOLD_DIM).pack()
        tk.Label(outer, text=msg, font=("Georgia", 12, "italic"),
                 bg=COLOR_BG, fg=COLOR_DIM,
                 wraplength=340, justify="center").pack(pady=(14, 0))
        self._lbl_nombre.config(text="", fg=COLOR_DIM)
        self._canvas.yview_moveto(0)

    def _datos_desde_bd(self, nombre: str) -> dict | None:
        try:
            base   = os.path.splitext(nombre)[0]
            partes = base.split("_", 4)
            if len(partes) < 3 or partes[0] != "recibo":
                return None
            id_prestamo = int(partes[1])
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("""
                SELECT p.id_prestamo, p.fecha_prestamo,
                       u.id_usuario, u.nombre,
                       COALESCE(u.correo,'—'), COALESCE(u.telefono,'—'),
                       l.isbn, l.titulo, l.autor,
                       p.fecha_devolucion_estimada,
                       p.devuelto,
                       COALESCE(p.fecha_devolucion_real, '')
                FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                JOIN libros   l ON p.isbn        = l.isbn
                WHERE p.id_prestamo = ?
            """, (id_prestamo,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return None

            def fmt(s):
                try:    return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
                except: return s or "—"

            hora_emision = ""
            if len(partes) >= 5:
                try:
                    hora_emision = datetime.strptime(
                        partes[4], "%Y%m%d_%H%M").strftime("%d/%m/%Y  %H:%M")
                except Exception:
                    pass

            devuelto      = bool(row[10])
            fecha_real    = row[11]
            dias_retraso  = 0
            if devuelto and fecha_real:
                try:
                    fe = datetime.strptime(row[9],      "%Y-%m-%d")
                    fr = datetime.strptime(fecha_real,  "%Y-%m-%d")
                    dias_retraso = max(0, (fr - fe).days)
                except Exception:
                    pass

            return {
                "id_prestamo": f"{row[0]:04d}",
                "fecha":       hora_emision or fmt(row[1]),
                "socio": {
                    "id":       str(row[2]),
                    "nombre":   row[3],
                    "correo":   row[4],
                    "telefono": row[5],
                },
                "libro": {
                    "isbn":   row[6],
                    "titulo": row[7],
                    "autor":  row[8],
                },
                "devolucion": {
                    "fecha": fmt(row[9]),
                    "plazo": "15 días naturales",
                },
                "devuelto":      devuelto,
                "fecha_real":    fmt(fecha_real) if fecha_real else "—",
                "dias_retraso":  dias_retraso,
            }
        except Exception:
            return None

    def _renderizar_tarjeta(self, nombre: str):
        self._limpiar_visor()
        data = self._datos_desde_bd(nombre)

        # ── Contenedor principal ──────────────────────────────────
        wrapper = tk.Frame(self._inner, bg=COLOR_BG)
        wrapper.pack(fill="x", padx=20, pady=20)

        outer = tk.Frame(wrapper, bg=COLOR_BG)
        outer.pack(fill="both", expand=True)

        # ── Helpers (todos sobre outer) ───────────────────────────
        def sep(c=COLOR_GOLD_DIM, h=1):
            tk.Frame(outer, bg=c, height=h).pack(fill="x")

        def kv(icon, lbl, val, vc=COLOR_TEXT):
            row = tk.Frame(outer, bg=COLOR_CARD)
            row.pack(fill="x")
            tk.Label(row, text=icon, font=("Georgia", 12),
                     bg=COLOR_CARD, fg=COLOR_GOLD_DIM, width=2
                     ).pack(side="left", padx=(10, 4))
            tk.Label(row, text=lbl, font=("Georgia", 10),
                     bg=COLOR_CARD, fg=COLOR_DIM, width=14, anchor="w"
                     ).pack(side="left")
            val_lbl = tk.Label(row, text=val or "—", font=("Georgia", 10, "bold"),
                     bg=COLOR_CARD, fg=vc, anchor="w", wraplength=1, justify="left")
            val_lbl.pack(side="left", fill="x", expand=True, padx=(6, 14), pady=5)
            val_lbl.bind("<Configure>",
                lambda e, w=val_lbl: w.config(wraplength=max(1, e.width - 4)))

        def sec_head(icon, titulo, c=COLOR_GOLD):
            f = tk.Frame(outer, bg=COLOR_CARD2)
            f.pack(fill="x")
            tk.Frame(f, bg=c, width=4).pack(side="left", fill="y")
            inner = tk.Frame(f, bg=COLOR_CARD2)
            inner.pack(side="left", padx=14, pady=8)
            tk.Label(inner, text=f"{icon}  {titulo}",
                     font=("Georgia", 10, "bold"),
                     bg=COLOR_CARD2, fg=c).pack(side="left")

        def spacer(h=6):
            tk.Frame(outer, bg=COLOR_CARD, height=h).pack(fill="x")

        # ── Cabecera ──────────────────────────────────────────────
        tk.Frame(outer, bg=COLOR_GOLD, height=3).pack(fill="x")
        cab = tk.Frame(outer, bg=COLOR_CARD)
        cab.pack(fill="x")
        tk.Label(cab, text=_t("titulo_bib"),
                 font=("Georgia", 15, "bold"),
                 bg=COLOR_CARD, fg=COLOR_GOLD).pack(pady=(14, 2))
        tk.Label(cab, text=_t("subtitulo"),
                 font=("Georgia", 9),
                 bg=COLOR_CARD, fg=COLOR_DIM).pack()
        sep()

        if data:
            ir = tk.Frame(cab, bg=COLOR_CARD)
            ir.pack(fill="x", padx=20, pady=12)

            nb = tk.Frame(ir, bg=COLOR_CARD)
            nb.pack(side="left", padx=10)
            tk.Label(nb, text=_t("lbl_prestamo"), font=("Georgia", 8),
                     bg=COLOR_CARD, fg=COLOR_DIM).pack(anchor="w")
            tk.Label(nb, text=f"# {data['id_prestamo']}",
                     font=("Georgia", 26, "bold"),
                     bg=COLOR_CARD, fg=COLOR_GOLD).pack(anchor="w")

            tk.Frame(ir, bg=COLOR_GOLD_DIM, width=1).pack(
                side="left", fill="y", padx=28)

            fb = tk.Frame(ir, bg=COLOR_CARD)
            fb.pack(side="left")
            tk.Label(fb, text=_t("lbl_emision"), font=("Georgia", 8),
                     bg=COLOR_CARD, fg=COLOR_DIM).pack(anchor="w")
            tk.Label(fb, text=data["fecha"],
                     font=("Georgia", 13, "bold"),
                     bg=COLOR_CARD, fg=COLOR_TEXT).pack(anchor="w", pady=(4, 0))

            sep()

            # ── Banner de devolución ─────────────────────────────
            if data.get("devuelto"):
                con_retraso = data["dias_retraso"] > 0
                banner_bg   = "#2a1010" if con_retraso else "#0e2318"
                banner_col  = COLOR_ERROR if con_retraso else COLOR_SUCCESS
                txt_sello   = _t("devuelto_retraso") if con_retraso else _t("devuelto")
                txt_sub     = (f"{data['dias_retraso']} {_t('retraso_dias')}"
                               if con_retraso else f"{_t('devuelto_el')} {data['fecha_real']}")

                banner = tk.Frame(outer, bg=banner_bg)
                banner.pack(fill="x")
                tk.Frame(banner, bg=banner_col, width=4).pack(side="left", fill="y")
                inner_b = tk.Frame(banner, bg=banner_bg)
                inner_b.pack(side="left", fill="x", expand=True, padx=14, pady=10)
                top_row = tk.Frame(inner_b, bg=banner_bg)
                top_row.pack(anchor="w")
                tk.Label(top_row, text=txt_sello,
                         font=("Georgia", 11, "bold"),
                         bg=banner_bg, fg=banner_col).pack(side="left")
                tk.Label(top_row, text=f"  ·  {txt_sub}",
                         font=("Georgia", 10),
                         bg=banner_bg, fg=banner_col).pack(side="left")

            sec_head("👤", _t("sec_socio"))
            kv("🆔", _t("lbl_id"),       data["socio"]["id"])
            kv("✏",  _t("lbl_nombre"),   data["socio"]["nombre"], COLOR_GOLD)
            kv("✉",  _t("lbl_correo"),   data["socio"]["correo"])
            kv("📱", _t("lbl_telefono"), data["socio"]["telefono"])
            spacer()

            # Libro
            sep()
            sec_head("📖", _t("sec_libro"))
            kv("🔢", _t("lbl_isbn"),   data["libro"]["isbn"])
            kv("📚", _t("lbl_titulo"), data["libro"]["titulo"])
            kv("✍",  _t("lbl_autor"),  data["libro"]["autor"])
            spacer()

            # Devolución
            sep()
            sec_head("🗓", _t("sec_devolucion"), c=COLOR_ERROR)
            kv("⚠",  _t("lbl_fecha_lim"), data["devolucion"]["fecha"], COLOR_ERROR)
            kv("⏱",  _t("lbl_plazo"),     _t("plazo_val"))
            spacer(10)

        else:
            tk.Label(cab, text=nombre,
                     font=("Georgia", 10, "italic"),
                     bg=COLOR_CARD, fg=COLOR_DIM,
                     wraplength=460, justify="center").pack(pady=14)
            spacer(8)

        # Pie
        sep(COLOR_GOLD)
        pie = tk.Frame(outer, bg=COLOR_CARD)
        pie.pack(fill="x")
        tk.Label(pie,
                 text=_t("pie"),
                 font=("Georgia", 9, "italic"),
                 bg=COLOR_CARD, fg=COLOR_DIM,
                 wraplength=500, justify="center").pack(pady=8)
        tk.Label(pie, text="✦", font=("Georgia", 10),
                 bg=COLOR_CARD, fg=COLOR_GOLD_DIM).pack(pady=(0, 8))
        tk.Frame(outer, bg=COLOR_GOLD, height=3).pack(fill="x")

        # Indicador PDF
        tk.Label(outer,
                 text=_t("pie_info"),
                 font=("Georgia", 9, "italic"),
                 bg=COLOR_BG, fg=COLOR_DIM).pack(pady=(12, 0))

        self._canvas.update_idletasks()
        self._canvas.yview_moveto(0)

    # ── Acciones ──────────────────────────────────────────────────────────
    def _regenerar_pdf(self) -> str | None:
        """
        Regenera el PDF del recibo activo con el tema e idioma actuales.
        Devuelve la ruta al PDF actualizado, o None si falla.
        El archivo original en /recibos/ se sobreescribe con los nuevos estilos.
        """
        if not self._ruta_activa or not os.path.isfile(self._ruta_activa):
            return None
        try:
            nombre = os.path.basename(self._ruta_activa)
            base   = os.path.splitext(nombre)[0]
            partes = base.split("_", 4)
            if len(partes) < 3 or partes[0] != "recibo":
                return self._ruta_activa   # no parseable, usar tal cual
            id_prestamo = int(partes[1])

            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("""
                SELECT p.id_usuario, u.nombre,
                       COALESCE(u.correo,''), COALESCE(u.telefono,''),
                       l.isbn, l.titulo, l.autor,
                       p.devuelto,
                       COALESCE(p.fecha_devolucion_real,''),
                       p.fecha_devolucion_estimada
                FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                JOIN libros   l ON p.isbn = l.isbn
                WHERE p.id_prestamo = ?
            """, (id_prestamo,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return self._ruta_activa

            from secciones.biblioteca_gestion_usuarios import Usuario
            from secciones.biblioteca_gestion_libros   import Libro
            from secciones.biblioteca_gestion_prestamos import (
                generar_recibo, estampar_devolucion_en_pdf)

            usuario = Usuario(nombre=row[1], id_usuario=row[0],
                              correo=row[2], telefono=row[3])
            libro   = Libro(titulo=row[5], autor=row[6],
                            isbn=row[4], estado="")

            # Regenerar el PDF (sobreescribe el existente con el mismo nombre)
            import tempfile, datetime as _dt_mod
            ruta_nueva = generar_recibo(usuario, libro, id_prestamo,
                                        ruta_destino=self._ruta_activa)

            # Re-estampar si ya fue devuelto
            if row[7] and row[8]:
                estampar_devolucion_en_pdf(id_prestamo, row[8], row[9])

            return self._ruta_activa

        except Exception:
            return self._ruta_activa   # si algo falla, usar el original

    def _abrir_externo(self):
        """Regenera con tema/idioma actuales y abre con el visor del sistema."""
        ruta = self._regenerar_pdf()
        if not ruta:
            return
        import subprocess, sys
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            self._lbl_msg.config(
                text=f"No se pudo abrir: {e}", fg=COLOR_ERROR)

    def _descargar(self):
        """Regenera con tema/idioma actuales y guarda donde el usuario elija."""
        ruta = self._regenerar_pdf()
        if not ruta:
            return
        destino = filedialog.asksaveasfilename(
            title=_t("descargar"),
            initialfile=os.path.basename(ruta),
            defaultextension=".pdf",
            filetypes=[("Archivo PDF", "*.pdf"), ("Todos los archivos", "*.*")]
        )
        if not destino:
            return
        try:
            shutil.copy2(ruta, destino)
            self._lbl_msg.config(text=f"✓  {_t('guardado_ok')}", fg=COLOR_SUCCESS)
            self.frame.after(4000, lambda: self._lbl_msg.config(text=""))
        except Exception as e:
            self._lbl_msg.config(
                text=f"✗  {_t('guardado_err')}  ({e})", fg=COLOR_ERROR)

    # ── Ciclo de vida ─────────────────────────────────────────────────────
    def mostrar(self):
        self.frame.pack(fill="both", expand=True)
        self._actualizar_lista()

    def ocultar(self):
        self.frame.pack_forget()