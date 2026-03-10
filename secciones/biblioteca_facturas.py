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
from tkinter import filedialog, ttk
import os
import shutil
import sqlite3
from datetime import datetime, timedelta

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
    - Panel derecho:   visor del contenido formateado
    - Botón descargar: copia el archivo a la ruta elegida por el usuario
    """

    def __init__(self, parent: tk.Widget, db_path: str, usuario):
        aplicar_tema()
        self.db_path      = db_path
        self.usuario      = usuario
        self._ruta_activa = None

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

        # ── Cuerpo ──
        body = tk.Frame(self.frame, bg=bg)
        body.pack(fill="both", expand=True, padx=20, pady=18)

        # ── Panel izquierdo: lista ──
        left = tk.Frame(body, bg=card, width=280)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        # Barra de filtro
        filtro_frame = tk.Frame(left, bg=card)
        filtro_frame.pack(fill="x", padx=10, pady=(12, 6))
        self._var_filtro = tk.StringVar()
        self._var_filtro.trace_add("write", lambda *_: self._actualizar_lista())
        self._entry_filtro = tk.Entry(
            filtro_frame, textvariable=self._var_filtro,
            font=("Georgia", 12), bg=self._card2, fg=text,
            insertbackground=gold, relief="flat",
            highlightthickness=1, highlightbackground=golddim,
            highlightcolor=gold
        )
        self._entry_filtro.pack(fill="x", ipady=5)
        self._entry_filtro.insert(0, _t("filtrar"))
        self._entry_filtro.config(fg=dim)
        self._entry_filtro.bind("<FocusIn>",  lambda e: self._focus_filtro(True))
        self._entry_filtro.bind("<FocusOut>", lambda e: self._focus_filtro(False))

        # Contador
        self._lbl_count = tk.Label(left, text="", font=("Georgia", 10),
                                   bg=card, fg=dim)
        self._lbl_count.pack(anchor="w", padx=12)
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

        # ── Panel derecho: visor ──
        right = tk.Frame(body, bg=bg)
        right.pack(side="left", fill="both", expand=True)

        toolbar = tk.Frame(right, bg=card, height=44)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        self._lbl_nombre = tk.Label(toolbar, text="", font=("Georgia", 11, "italic"),
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

        vscroll = ttk.Scrollbar(visor_frame, orient="vertical")
        vscroll.pack(side="right", fill="y")

        self._canvas = tk.Canvas(
            visor_frame, bg=bg, bd=0,
            highlightthickness=0,
            yscrollcommand=vscroll.set
        )
        self._canvas.pack(side="left", fill="both", expand=True)
        vscroll.config(command=self._canvas.yview)

        self._visor_inner = tk.Frame(self._canvas, bg=bg)
        self._canvas_win  = self._canvas.create_window(
            (4, 4), window=self._visor_inner, anchor="nw")

        self._visor_inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # Mensaje de feedback
        self._lbl_msg = tk.Label(right, text="", font=("Georgia", 11, "italic"),
                                 bg=bg, fg=self._ok)
        self._lbl_msg.pack(anchor="e", padx=18, pady=(4, 0))

        self._mostrar_placeholder()
        self._actualizar_lista()

    def _on_inner_configure(self, event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # ── Filtro ───────────────────────────────────────────────
    def _focus_filtro(self, focused: bool):
        placeholder = _t("filtrar")
        if focused:
            if self._entry_filtro.get() == placeholder:
                self._entry_filtro.delete(0, "end")
                self._entry_filtro.config(fg=self._text)
            self._entry_filtro.config(highlightbackground=self._gold)
        else:
            if not self._entry_filtro.get():
                self._entry_filtro.insert(0, placeholder)
                self._entry_filtro.config(fg=self._dim)
            self._entry_filtro.config(highlightbackground=self._golddim)

    # ── Lista de recibos ─────────────────────────────────────
    def _es_admin(self) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT rol FROM usuarios WHERE nombre = ? LIMIT 1",
                        (str(self.usuario),))
            fila = cur.fetchone()
            conn.close()
            return fila and fila[0] == "admin"
        except Exception:
            return False

    def _id_usuario_activo(self) -> str | None:
        try:
            conn = sqlite3.connect(self.db_path)
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
            base   = os.path.splitext(f)[0]
            partes = base.split("_", 4)
            if len(partes) >= 5:
                idp    = partes[1].lstrip("0") or "0"
                nombre = partes[3].replace("_", " ").title()
                fecha  = partes[4][:8]
                try:
                    fecha_fmt = datetime.strptime(fecha, "%Y%m%d").strftime("%d/%m/%Y")
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
        self._cargar_recibo(nombre, ruta)
        self._lbl_msg.config(text="")

    # ── Carga de datos del recibo ─────────────────────────────
    def _datos_desde_bd(self, nombre_archivo: str) -> dict | None:
        """
        Extrae id_prestamo del nombre del archivo y consulta la BD.
        Nombre esperado: recibo_{id_prestamo:04d}_{id_usuario}_{nombre}_{fecha}.txt
        """
        try:
            base   = os.path.splitext(nombre_archivo)[0]
            partes = base.split("_", 4)
            if len(partes) < 3 or partes[0] != "recibo":
                return None
            id_prestamo = int(partes[1])

            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("""
                SELECT p.id_prestamo,
                       p.fecha_prestamo,
                       u.id_usuario,
                       u.nombre,
                       COALESCE(u.correo,   '—'),
                       COALESCE(u.telefono, '—'),
                       l.isbn,
                       l.titulo,
                       l.autor,
                       p.fecha_devolucion_estimada
                FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                JOIN libros   l ON p.isbn        = l.isbn
                WHERE p.id_prestamo = ?
            """, (id_prestamo,))
            row = cur.fetchone()
            conn.close()

            if not row:
                return None

            # Formatear fechas
            def fmt_fecha(s):
                try:
                    return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    return s or "—"

            # Calcular hora de emisión desde el nombre del archivo
            hora_emision = ""
            if len(partes) >= 5:
                ts = partes[4]            # "20260310_0933"
                try:
                    hora_emision = datetime.strptime(ts, "%Y%m%d_%H%M").strftime(
                        "%d/%m/%Y  %H:%M")
                except Exception:
                    pass
            if not hora_emision:
                hora_emision = fmt_fecha(row[1])

            return {
                "id_prestamo":  str(row[0]),
                "fecha":        hora_emision,
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
                    "fecha": fmt_fecha(row[9]),
                    "plazo": "15 días naturales",
                },
            }
        except Exception:
            return None

    def _parse_recibo_txt(self, ruta: str) -> dict:
        """
        Parsea el fichero .txt como fallback si la BD no devuelve datos.
        Limpia correctamente los caracteres de borde (║) al final de los valores.
        """
        data = {
            "id_prestamo": "",
            "fecha":       "",
            "socio":      {"id": "", "nombre": "", "correo": "", "telefono": ""},
            "libro":      {"isbn": "", "titulo": "", "autor": ""},
            "devolucion": {"fecha": "", "plazo": "15 días naturales"},
        }
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                texto = f.read()
        except Exception:
            return data

        def get(clave: str) -> str:
            for line in texto.splitlines():
                # Eliminar bordes izquierdo y derecho
                s = line.strip()
                s = s.lstrip("║╠╔╚").rstrip("║╣╗╝").strip()
                if ":" not in s:
                    continue
                k, _, v = s.partition(":")
                if k.strip().lower() == clave.strip().lower():
                    return v.strip().rstrip("║").strip()
            return ""

        data["id_prestamo"]          = get("Nº Préstamo").lstrip("#").strip()
        data["fecha"]                = get("Fecha emisión") or get("Fecha")
        data["socio"]["id"]          = get("ID")
        data["socio"]["nombre"]      = get("Nombre")
        data["socio"]["correo"]      = get("Correo")
        data["socio"]["telefono"]    = get("Teléfono")
        data["libro"]["isbn"]        = get("ISBN")
        data["libro"]["titulo"]      = get("Título")
        data["libro"]["autor"]       = get("Autor")
        data["devolucion"]["fecha"]  = get("Fecha límite")
        data["devolucion"]["plazo"]  = get("Plazo") or "15 días naturales"
        return data

    def _cargar_recibo(self, nombre: str, ruta: str):
        self._limpiar_visor()
        # Intentar obtener datos fiables desde la BD
        data = self._datos_desde_bd(nombre)
        if not data:
            data = self._parse_recibo_txt(ruta)
        self._renderizar_recibo(data)
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(0)

    # ── Visor ────────────────────────────────────────────────
    def _limpiar_visor(self):
        for w in self._visor_inner.winfo_children():
            w.destroy()

    def _mostrar_placeholder(self):
        self._limpiar_visor()
        archivos = self._listar_archivos()
        msg = _t("sin_recibos") if not archivos else _t("sel_recibo")
        outer = tk.Frame(self._visor_inner, bg=self._bg)
        outer.pack(pady=80, padx=40)
        tk.Label(outer, text="🧾", font=("Georgia", 48),
                 bg=self._bg, fg=self._golddim).pack()
        tk.Label(outer, text=msg, font=("Georgia", 12, "italic"),
                 bg=self._bg, fg=self._dim,
                 wraplength=320, justify="center").pack(pady=(12, 0))
        self._lbl_nombre.config(text="", fg=self._dim)
        self._canvas.yview_moveto(0)

    def _renderizar_recibo(self, data: dict):
        """Construye el recibo visualmente dentro del visor."""
        bg      = self._bg
        card    = self._card
        card2   = self._card2
        gold    = self._gold
        golddim = self._golddim
        text    = self._text
        dim     = self._dim
        err     = self._err
        CARD_W  = 600

        # Marco exterior con margen
        outer = tk.Frame(self._visor_inner, bg=bg)
        outer.pack(fill="x", padx=24, pady=20)

        def sep(parent, color=golddim, h=1):
            tk.Frame(parent, bg=color, height=h).pack(fill="x")

        def kv_row(parent, icon, label, value, vc=None):
            row = tk.Frame(parent, bg=card)
            row.pack(fill="x", padx=20, pady=3)
            tk.Label(row, text=icon, font=("Georgia", 13),
                     bg=card, fg=golddim, width=2, anchor="w").pack(side="left")
            tk.Label(row, text=label, font=("Georgia", 11),
                     bg=card, fg=dim, anchor="w", width=16).pack(side="left", padx=(4, 0))
            tk.Label(row, text=value or "—", font=("Georgia", 11, "bold"),
                     bg=card, fg=vc or text, anchor="w",
                     wraplength=CARD_W - 220).pack(side="left", padx=(8, 0))

        def sec_head(parent, icon, titulo, accent=None):
            accent = accent or gold
            f = tk.Frame(parent, bg=card2)
            f.pack(fill="x")
            tk.Frame(f, bg=accent, width=4).pack(side="left", fill="y")
            inner = tk.Frame(f, bg=card2)
            inner.pack(side="left", padx=14, pady=10)
            tk.Label(inner, text=icon, font=("Georgia", 13),
                     bg=card2, fg=accent).pack(side="left", padx=(0, 8))
            tk.Label(inner, text=titulo, font=("Georgia", 11, "bold"),
                     bg=card2, fg=accent).pack(side="left")

        def spacer(parent, h=8):
            tk.Frame(parent, bg=card, height=h).pack(fill="x")

        # ═══════════════════════════════════════
        # CABECERA PRINCIPAL
        # ═══════════════════════════════════════
        cab = tk.Frame(outer, bg=card)
        cab.pack(fill="x")

        # Borde superior dorado
        tk.Frame(cab, bg=gold, height=4).pack(fill="x")

        # Título de la biblioteca
        tk.Label(cab,
                 text="✦  EL ARCHIVO DE LOS MUNDOS  ✦",
                 font=("Georgia", 17, "bold"),
                 bg=card, fg=gold).pack(pady=(18, 2))
        tk.Label(cab,
                 text="C O M P R O B A N T E   D E   P R É S T A M O",
                 font=("Georgia", 10),
                 bg=card, fg=dim).pack()

        sep(cab, golddim)

        # Número de préstamo + fecha
        info_row = tk.Frame(cab, bg=card)
        info_row.pack(fill="x", padx=20, pady=14)

        # Bloque izquierdo: número
        num_blk = tk.Frame(info_row, bg=card)
        num_blk.pack(side="left", padx=(10, 0))
        tk.Label(num_blk, text="PRÉSTAMO", font=("Georgia", 9),
                 bg=card, fg=dim).pack(anchor="w")
        tk.Label(num_blk,
                 text=f"# {data['id_prestamo'] or '—'}",
                 font=("Georgia", 28, "bold"),
                 bg=card, fg=gold).pack(anchor="w")

        # Separador vertical
        tk.Frame(info_row, bg=golddim, width=1).pack(
            side="left", fill="y", padx=30)

        # Bloque derecho: fecha
        fecha_blk = tk.Frame(info_row, bg=card)
        fecha_blk.pack(side="left")
        tk.Label(fecha_blk, text="FECHA DE EMISIÓN", font=("Georgia", 9),
                 bg=card, fg=dim).pack(anchor="w")
        tk.Label(fecha_blk,
                 text=data["fecha"] or "—",
                 font=("Georgia", 15, "bold"),
                 bg=card, fg=text).pack(anchor="w", pady=(4, 0))

        sep(cab, golddim)
        spacer(cab, 4)

        # ═══════════════════════════════════════
        # SECCIÓN: DATOS DEL SOCIO
        # ═══════════════════════════════════════
        sep(outer, golddim)
        sec_head(outer, "👤", "DATOS DEL SOCIO")
        s_card = tk.Frame(outer, bg=card)
        s_card.pack(fill="x")
        spacer(s_card)
        kv_row(s_card, "🆔", "ID socio",   data["socio"]["id"])
        kv_row(s_card, "✏", "Nombre",      data["socio"]["nombre"], gold)
        kv_row(s_card, "✉", "Correo",      data["socio"]["correo"])
        kv_row(s_card, "📱", "Teléfono",   data["socio"]["telefono"])
        spacer(s_card, 12)

        # ═══════════════════════════════════════
        # SECCIÓN: LIBRO PRESTADO
        # ═══════════════════════════════════════
        sep(outer, golddim)
        sec_head(outer, "📖", "LIBRO PRESTADO")
        l_card = tk.Frame(outer, bg=card)
        l_card.pack(fill="x")
        spacer(l_card)
        kv_row(l_card, "🔢", "ISBN",   data["libro"]["isbn"])
        kv_row(l_card, "📚", "Título", data["libro"]["titulo"])
        kv_row(l_card, "✍", "Autor",   data["libro"]["autor"])
        spacer(l_card, 12)

        # ═══════════════════════════════════════
        # SECCIÓN: DEVOLUCIÓN
        # ═══════════════════════════════════════
        sep(outer, golddim)
        sec_head(outer, "🗓", "DEVOLUCIÓN", accent=err)
        d_card = tk.Frame(outer, bg=card)
        d_card.pack(fill="x")
        spacer(d_card)
        kv_row(d_card, "⚠", "Fecha límite", data["devolucion"]["fecha"], err)
        kv_row(d_card, "⏱", "Plazo",        data["devolucion"]["plazo"])
        spacer(d_card, 12)

        # ═══════════════════════════════════════
        # PIE
        # ═══════════════════════════════════════
        sep(outer, gold)
        pie = tk.Frame(outer, bg=card)
        pie.pack(fill="x")
        tk.Label(pie,
                 text="Conserve este comprobante como justificante del préstamo.",
                 font=("Georgia", 10, "italic"),
                 bg=card, fg=dim,
                 wraplength=CARD_W - 60, justify="center").pack(pady=12)
        tk.Label(pie, text="✦", font=("Georgia", 12),
                 bg=card, fg=golddim).pack(pady=(0, 10))
        tk.Frame(pie, bg=gold, height=4).pack(fill="x")

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
            return
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