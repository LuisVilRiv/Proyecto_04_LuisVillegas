"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Módulo de calendario. Muestra eventos del mes (préstamos
                 nuevos, vencimientos y devoluciones) en una cuadrícula
                 mensual interactiva. Vista adaptada por rol: el admin ve
                 todos los socios; el usuario normal solo los suyos.
Autor/a:         Luis Villegas Rivera
Fecha:           2026-03-09
Clases principales:
    - SeccionCalendario : Panel tkinter con calendario mensual y detalle lateral.
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
import calendar
from datetime import datetime, date, timedelta

from secciones.biblioteca_gestion_libros import (
    aplicar_tema,
    COLOR_BG, COLOR_CARD, COLOR_CARD2, COLOR_GOLD, COLOR_GOLD_DIM,
    COLOR_TEXT, COLOR_DIM, COLOR_ERROR, COLOR_SUCCESS,
    FONT_TITLE, FONT_SMALL, FONT_BTN,
)
from secciones.biblioteca_ajustes import T, ConfigApp
from secciones.biblioteca_sanciones import (
    leer_config, estado_prestamo, calcular_dias_retraso, COLOR_WARN,
)

# ── Colores propios del calendario ──────────────────────────
COLOR_NUEVO     = "#4a8aaf"   # azul — préstamo registrado ese día
COLOR_VENCE_HOY = COLOR_WARN  # amarillo — vence hoy
COLOR_VENCIDO   = COLOR_ERROR # rojo — ya vencido y sin devolver
COLOR_DEVUELTO  = COLOR_SUCCESS  # verde — devuelto ese día
COLOR_HOY_BG    = "#1e1a2e"  # fondo celda de hoy
COLOR_SEL_BG    = "#1a1e1a"  # fondo celda seleccionada
COLOR_CELDA     = COLOR_CARD2
COLOR_CELDA_OFF = "#100f15"  # días fuera del mes

_DIAS = {
    "es": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}
_MESES = {
    "es": ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"],
    "en": ["","January","February","March","April","May","June",
            "July","August","September","October","November","December"],
}
_STATS_TX = {
    "es": {"nuevo":"Nuevos esta semana","vence":"Vencen esta semana",
           "vencido":"Con retraso","devuelto":"Devueltos esta semana",
           "hoy":"Hoy","sel_dia":"Selecciona un día",
           "sin_eventos":"Sin eventos este día.",
           "nuevo_lbl":"Nuevo préstamo","vence_lbl":"Vencimiento",
           "vencido_lbl":"VENCIDO","devuelto_lbl":"Devuelto",
           "socio":"Socio","prestamo":"Préstamo"},
    "en": {"nuevo":"New this week","vence":"Due this week",
           "vencido":"Overdue","devuelto":"Returned this week",
           "hoy":"Today","sel_dia":"Select a day",
           "sin_eventos":"No events this day.",
           "nuevo_lbl":"New loan","vence_lbl":"Due",
           "vencido_lbl":"OVERDUE","devuelto_lbl":"Returned",
           "socio":"Member","prestamo":"Loan"},
}

def _cal_tx(clave: str) -> str:
    idioma = ConfigApp.get("idioma") or "es"
    return _STATS_TX.get(idioma, _STATS_TX["es"]).get(clave, clave)

def _dias_semana() -> list:
    idioma = ConfigApp.get("idioma") or "es"
    return _DIAS.get(idioma, _DIAS["es"])

def _meses() -> list:
    idioma = ConfigApp.get("idioma") or "es"
    return _MESES.get(idioma, _MESES["es"])



# ═══════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════
class SeccionCalendario:
    """
    Calendario mensual interactivo.
    - Cada celda muestra puntos de colores según los eventos del día.
    - Clic en una celda → panel lateral con lista detallada.
    - Barra superior con resumen semanal.
    - Botones ◀ / hoy / ▶ para navegar.
    - Admin ve todos los usuarios; socio normal solo los suyos.
    """

    def __init__(self, parent: tk.Widget, db_path: str, usuario: str):
        aplicar_tema()
        self.db_path = db_path
        self.usuario = usuario
        # Leer colores del tema activo
        c = ConfigApp.colores()
        self._bg      = c["bg"]
        self._card    = c["card"]
        self._card2   = c.get("card2", c["card"])
        self._gold    = c["acento"]
        self._golddim = c["acento_dim"]
        self._text    = c["text"]
        self._dim     = c["dim"]
        self.frame    = tk.Frame(parent, bg=self._bg)

        # Determinar rol desde la BD
        self.rol         = self._leer_rol()
        self.id_usuario  = self._leer_id()

        # Estado del calendario
        hoy = date.today()
        self._mes  = hoy.month
        self._año  = hoy.year
        self._sel  = hoy          # día seleccionado
        self._hoy  = hoy

        # Cache de eventos {date: [evento, ...]}
        self._eventos: dict[date, list] = {}

        self._celdas: dict[date, tk.Frame] = {}   # frame de cada día
        self._build_ui()

    # ── Consultas BD ────────────────────────────────────────
    def _leer_rol(self) -> str:
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT rol FROM usuarios WHERE nombre=?", (self.usuario,))
            row = cur.fetchone()
            conn.close()
            return row[0] if row else "normal"
        except sqlite3.Error:
            return "normal"

    def _leer_id(self) -> int | None:
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT id_usuario FROM usuarios WHERE nombre=?", (self.usuario,))
            row = cur.fetchone()
            conn.close()
            return row[0] if row else None
        except sqlite3.Error:
            return None

    def _cargar_eventos(self):
        """Carga todos los eventos del mes visible en self._eventos."""
        self._eventos = {}
        primer_dia = date(self._año, self._mes, 1)
        ultimo_dia = date(self._año, self._mes,
                          calendar.monthrange(self._año, self._mes)[1])
        # Ampliar un poco para incluir préstamos vencidos del mes anterior
        desde = (primer_dia - timedelta(days=31)).strftime("%Y-%m-%d")
        hasta = ultimo_dia.strftime("%Y-%m-%d")

        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()

            # Filtro por usuario según rol
            filtro_u = "" if self.rol == "admin" \
                else f" AND p.id_usuario = {self.id_usuario}"

            # 1. Préstamos registrados en el mes
            cur.execute(f"""
                SELECT p.fecha_prestamo, u.nombre, l.titulo,
                       p.id_prestamo, 'nuevo'
                FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                JOIN libros   l ON p.isbn = l.isbn
                WHERE p.fecha_prestamo BETWEEN ? AND ?{filtro_u}
            """, (primer_dia.strftime("%Y-%m-%d"), hasta))
            for row in cur.fetchall():
                self._añadir_evento(row[0], {
                    "tipo": "nuevo", "socio": row[1], "libro": row[2],
                    "id": row[3], "texto": f"Préstamo: {row[2]}"
                })

            # 2. Vencimientos que caen en el mes (activos o no)
            cur.execute(f"""
                SELECT p.fecha_devolucion_estimada, u.nombre, l.titulo,
                       p.id_prestamo, p.devuelto
                FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                JOIN libros   l ON p.isbn = l.isbn
                WHERE p.fecha_devolucion_estimada BETWEEN ? AND ?{filtro_u}
            """, (primer_dia.strftime("%Y-%m-%d"), hasta))
            for row in cur.fetchall():
                devuelto = row[4]
                if not devuelto:
                    dias_ret = calcular_dias_retraso(row[0])
                    tipo = "vencido" if dias_ret > 0 else "vence"
                    texto = (f"Vence: {row[2]}"
                             if tipo == "vence"
                             else f"Vencido +{dias_ret}d: {row[2]}")
                    self._añadir_evento(row[0], {
                        "tipo": tipo, "socio": row[1], "libro": row[2],
                        "id": row[3], "texto": texto,
                    })

            # 2b. Préstamos vencidos de meses anteriores aún sin devolver
            #     → se anclan al día de hoy si hoy pertenece al mes visible,
            #       o al primer día del mes visible si es un mes futuro.
            if self._hoy.month == self._mes and self._hoy.year == self._año:
                ancla = self._hoy
            else:
                ancla = primer_dia   # mes futuro: primer día del mes

            cur.execute(f"""
                SELECT p.fecha_devolucion_estimada, u.nombre, l.titulo,
                       p.id_prestamo
                FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                JOIN libros   l ON p.isbn = l.isbn
                WHERE p.devuelto = 0
                  AND p.fecha_devolucion_estimada < ?{filtro_u}
            """, (primer_dia.strftime("%Y-%m-%d"),))
            for row in cur.fetchall():
                dias_ret = calcular_dias_retraso(row[0])
                texto = f"Vencido +{dias_ret}d: {row[2]}"
                self._añadir_evento(ancla.isoformat(), {
                    "tipo": "vencido", "socio": row[1], "libro": row[2],
                    "id": row[3], "texto": texto,
                })

            # 3. Devoluciones usando fecha real de devolución
            cur.execute(f"""
                SELECT p.fecha_devolucion_real, u.nombre, l.titulo,
                       p.id_prestamo
                FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                JOIN libros   l ON p.isbn = l.isbn
                WHERE p.devuelto = 1
                  AND p.fecha_devolucion_real IS NOT NULL
                  AND p.fecha_devolucion_real BETWEEN ? AND ?{filtro_u}
            """, (primer_dia.strftime("%Y-%m-%d"), hasta))
            for row in cur.fetchall():
                self._añadir_evento(row[0], {
                    "tipo": "devuelto", "socio": row[1], "libro": row[2],
                    "id": row[3], "texto": f"Devuelto: {row[2]}",
                })

            conn.close()
        except sqlite3.Error:
            pass

    def _añadir_evento(self, fecha_str: str, evento: dict):
        try:
            d = date.fromisoformat(fecha_str)
        except ValueError:
            return
        self._eventos.setdefault(d, []).append(evento)

    def _eventos_semana(self) -> dict:
        """Estadísticas de la semana actual."""
        hoy   = self._hoy
        lunes = hoy - timedelta(days=hoy.weekday())
        totals = {"nuevo": 0, "vence": 0, "vencido": 0, "devuelto": 0}
        for i in range(7):
            d = lunes + timedelta(days=i)
            for ev in self._eventos.get(d, []):
                t = ev["tipo"]
                if t in totals:
                    totals[t] += 1
        return totals

    # ── Construcción de UI ───────────────────────────────────
    def _build_ui(self):
        # ── Cabecera ──
        cab = tk.Frame(self.frame, bg=self._card, height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text=T("cab_calendario", "📅  Calendario de Préstamos"),
                 font=FONT_TITLE, bg=self._card, fg=self._gold
                 ).pack(side="left", padx=24, pady=12)
        tk.Frame(self.frame, height=1, bg=self._golddim).pack(fill="x")

        # ── Barra de estadísticas semanales ──
        self._stats_bar = tk.Frame(self.frame, bg=self._card, height=40)
        self._stats_bar.pack(fill="x")
        self._stats_bar.pack_propagate(False)
        self._stats_labels = {}
        items = [
            ("nuevo",    COLOR_NUEVO,    _cal_tx("nuevo")),
            ("vence",    COLOR_VENCE_HOY,_cal_tx("vence")),
            ("vencido",  COLOR_VENCIDO,  _cal_tx("vencido")),
            ("devuelto", COLOR_DEVUELTO, _cal_tx("devuelto")),
        ]
        tk.Frame(self._stats_bar, width=16, bg=self._card).pack(side="left")
        for key, color, label in items:
            fr = tk.Frame(self._stats_bar, bg=self._card)
            fr.pack(side="left", padx=(0, 24))
            lbl_n = tk.Label(fr, text="0", font=("Georgia", 14, "bold"),
                             bg=self._card, fg=color)
            lbl_n.pack(side="left", pady=6)
            tk.Label(fr, text=f"  {label}", font=("Georgia", 8, "italic"),
                     bg=self._card, fg=self._dim).pack(side="left")
            self._stats_labels[key] = lbl_n
        tk.Frame(self.frame, height=1, bg=self._golddim).pack(fill="x")

        # ── Cuerpo principal ──
        body = tk.Frame(self.frame, bg=self._bg)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # ── Panel izquierdo: navegación + cuadrícula ──
        left = tk.Frame(body, bg=self._bg)
        left.pack(side="left", fill="both", expand=True)

        # Navegación mes
        nav = tk.Frame(left, bg=self._bg)
        nav.pack(fill="x", pady=(0, 10))

        self._btn_prev = tk.Button(
            nav, text="◀", font=("Georgia", 13, "bold"),
            bg=self._card, fg=self._gold, activebackground=self._golddim,
            activeforeground=self._text, relief="flat", bd=0,
            cursor="hand2", width=3, command=self._mes_anterior)
        self._btn_prev.pack(side="left", ipady=4)

        self._lbl_mes = tk.Label(
            nav, text="", font=("Georgia", 15, "bold"),
            bg=self._bg, fg=self._text, width=22, anchor="center")
        self._lbl_mes.pack(side="left", expand=True)

        btn_hoy = tk.Button(
            nav, text=_cal_tx("hoy"), font=("Georgia", 9, "bold"),
            bg=self._golddim, fg=self._text,
            activebackground=self._gold, activeforeground="#000",
            relief="flat", bd=0, cursor="hand2",
            command=self._ir_hoy)
        btn_hoy.pack(side="left", ipadx=12, ipady=4, padx=(0, 8))
        btn_hoy.bind("<Enter>", lambda _: btn_hoy.config(bg=self._gold, fg='#000'))
        btn_hoy.bind("<Leave>", lambda _: btn_hoy.config(bg=self._golddim, fg=self._text))

        self._btn_next = tk.Button(
            nav, text="▶", font=("Georgia", 13, "bold"),
            bg=self._card, fg=self._gold, activebackground=self._golddim,
            activeforeground=self._text, relief="flat", bd=0,
            cursor="hand2", width=3, command=self._mes_siguiente)
        self._btn_next.pack(side="left", ipady=4)

        # Cabecera días de la semana
        dias_frame = tk.Frame(left, bg=self._bg)
        dias_frame.pack(fill="x")
        for i, dia in enumerate(_dias_semana()):
            color = self._gold if i >= 5 else self._dim
            tk.Label(dias_frame, text=dia,
                     font=("Georgia", 9, "bold"),
                     bg=self._bg, fg=color,
                     width=6, anchor="center").grid(row=0, column=i,
                                                    padx=2, pady=(0, 4))

        # Cuadrícula de celdas
        self._grid_frame = tk.Frame(left, bg=self._bg)
        self._grid_frame.pack(fill="both", expand=True)

        # ── Panel derecho: detalle del día ──
        sep = tk.Frame(body, bg=self._golddim, width=1)
        sep.pack(side="left", fill="y", padx=(10, 0))

        self._panel_det = tk.Frame(body, bg=self._card, width=260)
        self._panel_det.pack(side="left", fill="y", padx=(0, 0))
        self._panel_det.pack_propagate(False)
        self._build_panel_detalle()

        # Leyenda
        ley_frame = tk.Frame(left, bg=self._bg)
        ley_frame.pack(fill="x", pady=(8, 0))
        for color, txt in [
            (COLOR_NUEVO,     _cal_tx("nuevo_lbl")),
            (COLOR_VENCE_HOY, _cal_tx("vence_lbl")),
            (COLOR_VENCIDO,   _cal_tx("vencido_lbl")),
            (COLOR_DEVUELTO,  _cal_tx("devuelto_lbl")),
        ]:
            tk.Label(ley_frame, text="●", font=("Georgia", 11),
                     bg=self._bg, fg=color).pack(side="left", padx=(0, 2))
            tk.Label(ley_frame, text=f"{txt}   ", font=("Georgia", 8),
                     bg=self._bg, fg=self._dim).pack(side="left")

        self._renderizar_mes()

    def _build_panel_detalle(self):
        """Construye el panel lateral de detalle (vacío hasta seleccionar día)."""
        self._det_titulo = tk.Label(
            self._panel_det, text=_cal_tx("sel_dia"),
            font=("Georgia", 11, "bold"),
            bg=self._card, fg=self._gold,
            anchor="w", wraplength=230)
        self._det_titulo.pack(anchor="w", padx=14, pady=(18, 4))
        tk.Frame(self._panel_det, height=1, bg=self._golddim).pack(fill="x", padx=14)

        self._det_scroll_frame = tk.Frame(self._panel_det, bg=self._card)
        self._det_scroll_frame.pack(fill="both", expand=True, padx=6, pady=8)

        canvas = tk.Canvas(self._det_scroll_frame, bg=self._card,
                           highlightthickness=0, bd=0)
        vsb    = ttk.Scrollbar(self._det_scroll_frame, orient="vertical",
                               command=canvas.yview)
        self._det_inner = tk.Frame(canvas, bg=self._card)
        self._det_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._det_inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._det_canvas = canvas

    # ── Renderizado del calendario ───────────────────────────
    def _renderizar_mes(self):
        """Destruye y reconstruye las celdas del mes."""
        for w in self._grid_frame.winfo_children():
            w.destroy()
        self._celdas = {}

        self._lbl_mes.config(text=f"{_meses()[self._mes]}  {self._año}")
        self._cargar_eventos()
        self._actualizar_stats()

        cal = calendar.Calendar(firstweekday=0)  # Lunes primero
        semanas = cal.monthdatescalendar(self._año, self._mes)

        for row_idx, semana in enumerate(semanas):
            self._grid_frame.rowconfigure(row_idx, weight=1)
            for col_idx, d in enumerate(semana):
                self._grid_frame.columnconfigure(col_idx, weight=1)
                self._crear_celda(d, row_idx, col_idx)

        # Resaltar selección actual
        self._resaltar_seleccion()

    def _crear_celda(self, d: date, row: int, col: int):
        es_mes_actual = (d.month == self._mes)
        es_hoy        = (d == self._hoy)
        es_finde      = (d.weekday() >= 5)

        _celda     = self._card2
        _celda_off = self._bg
        _hoy_bg    = self._card2  # highlighted by border
        bg = (_hoy_bg   if es_hoy
              else _celda if es_mes_actual
              else _celda_off)

        cell = tk.Frame(self._grid_frame, bg=bg,
                        highlightthickness=1,
                        highlightbackground=self._golddim if es_hoy else "#1e1c28")
        cell.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
        cell.configure(width=72, height=64)
        cell.pack_propagate(False)

        # Número del día
        num_color = (self._gold    if es_hoy
                     else self._gold if es_finde and es_mes_actual
                     else self._text if es_mes_actual
                     else "#3a3640")
        num_font  = ("Georgia", 11, "bold") if es_hoy else ("Georgia", 10)
        tk.Label(cell, text=str(d.day), font=num_font,
                 bg=bg, fg=num_color, anchor="ne").pack(anchor="ne", padx=5, pady=3)

        # Indicadores de eventos
        evs = self._eventos.get(d, [])
        if evs:
            dots_frame = tk.Frame(cell, bg=bg)
            dots_frame.pack(anchor="w", padx=3, pady=(0, 3))
            conteos = {}
            for ev in evs:
                conteos[ev["tipo"]] = conteos.get(ev["tipo"], 0) + 1
            orden = ["vencido", "vence", "nuevo", "devuelto"]
            color_map = {
                "nuevo":    COLOR_NUEVO,
                "vence":    COLOR_VENCE_HOY,
                "vencido":  COLOR_VENCIDO,
                "devuelto": COLOR_DEVUELTO,
            }
            for tipo in orden:
                if tipo in conteos:
                    color = color_map[tipo]
                    n     = conteos[tipo]
                    # Chip de color con número
                    chip = tk.Frame(dots_frame, bg=color,
                                    highlightthickness=0, bd=0)
                    chip.pack(side="left", padx=(0, 2))
                    txt = str(n) if n > 1 else "·"
                    lbl = tk.Label(chip,
                                   text=txt,
                                   font=("Georgia", 7, "bold"),
                                   bg=color, fg="#ffffff",
                                   padx=3, pady=0)
                    lbl.pack()

        # Bind clic en toda la celda (incluyendo chips anidados)
        def _bind_rec(w):
            w.bind("<Button-1>", lambda e, day=d: self._seleccionar_dia(day))
            w.bind("<Enter>",    lambda e, c=cell, day=d:
                        c.config(highlightbackground=self._gold)
                        if day != self._sel else None)
            w.bind("<Leave>",    lambda e, c=cell, day=d, hoy=es_hoy:
                        c.config(highlightbackground=self._golddim
                                 if hoy else "#1e1c28")
                        if day != self._sel else None)
            for child in w.winfo_children():
                _bind_rec(child)
        _bind_rec(cell)

        self._celdas[d] = cell

    def _resaltar_seleccion(self):
        for d, cell in self._celdas.items():
            if not cell.winfo_exists():
                continue
            if d == self._sel:
                cell.config(bg=self._card,
                            highlightbackground=self._gold,
                            highlightthickness=2)
                for w in cell.winfo_children():
                    w.config(bg=self._card)
                    for ww in w.winfo_children():
                        try: ww.config(bg=self._card)
                        except: pass
            elif d == self._hoy:
                cell.config(bg=self._card2,
                            highlightbackground=self._golddim,
                            highlightthickness=1)
            else:
                bg = (self._card2 if d.month == self._mes
                      else self._bg)
                cell.config(bg=bg,
                            highlightbackground="#1e1c28",
                            highlightthickness=1)

    def _actualizar_stats(self):
        totals = self._eventos_semana()
        for key, lbl in self._stats_labels.items():
            lbl.config(text=str(totals.get(key, 0)))

    # ── Panel de detalle ─────────────────────────────────────
    def _seleccionar_dia(self, d: date):
        self._sel = d
        self._resaltar_seleccion()
        self._mostrar_detalle(d)

    def _mostrar_detalle(self, d: date):
        nombre_mes = _meses()[d.month]
        es_hoy     = (d == self._hoy)
        sufijo     = f"  · {_cal_tx('hoy')}" if es_hoy else ""
        sep        = "de" if (ConfigApp.get("idioma") or "es") == "es" else ""
        self._det_titulo.config(
            text=f"{d.day} {sep} {nombre_mes} {d.year}{sufijo}".strip())

        for w in self._det_inner.winfo_children():
            w.destroy()

        evs = self._eventos.get(d, [])
        if not evs:
            tk.Label(self._det_inner,
                     text=_cal_tx("sin_eventos"),
                     font=("Georgia", 9, "italic"),
                     bg=self._card, fg=self._dim,
                     wraplength=220).pack(padx=8, pady=12, anchor="w")
        else:
            color_map = {
                "nuevo":    (COLOR_NUEVO,     _cal_tx("nuevo_lbl")),
                "vence":    (COLOR_VENCE_HOY, _cal_tx("vence_lbl")),
                "vencido":  (COLOR_VENCIDO,   _cal_tx("vencido_lbl")),
                "devuelto": (COLOR_DEVUELTO,  _cal_tx("devuelto_lbl")),
            }
            # Agrupar por tipo
            grupos: dict[str, list] = {}
            for ev in evs:
                grupos.setdefault(ev["tipo"], []).append(ev)

            for tipo in ["vencido", "vence", "nuevo", "devuelto"]:
                if tipo not in grupos:
                    continue
                color, etiqueta = color_map[tipo]

                # Cabecera del grupo
                hdr = tk.Frame(self._det_inner, bg=self._card)
                hdr.pack(fill="x", padx=6, pady=(10, 2))
                tk.Label(hdr, text="●", font=("Georgia", 10),
                         bg=self._card, fg=color).pack(side="left")
                tk.Label(hdr, text=f"  {etiqueta.upper()}",
                         font=("Georgia", 8, "bold"),
                         bg=self._card, fg=color).pack(side="left")

                for ev in grupos[tipo]:
                    card = tk.Frame(self._det_inner, bg=self._card2,
                                    highlightthickness=1,
                                    highlightbackground="#2a2838")
                    card.pack(fill="x", padx=6, pady=2)

                    tk.Label(card, text=ev["libro"],
                             font=("Georgia", 9, "bold"),
                             bg=self._card2, fg=self._text,
                             anchor="w", wraplength=210).pack(
                                 anchor="w", padx=8, pady=(6, 1))
                    if self.rol == "admin":
                        tk.Label(card, text=f"{_cal_tx('socio')}: {ev['socio']}",
                                 font=("Georgia", 8, "italic"),
                                 bg=self._card2, fg=self._dim).pack(
                                     anchor="w", padx=8, pady=(0, 2))
                    tk.Label(card, text=f"{_cal_tx('prestamo')} #{ev['id']}",
                             font=("Georgia", 7),
                             bg=self._card2, fg=self._dim).pack(
                                 anchor="w", padx=8, pady=(0, 6))

        # Actualizar scroll
        self._det_inner.update_idletasks()
        self._det_canvas.configure(
            scrollregion=self._det_canvas.bbox("all"))

    # ── Navegación ───────────────────────────────────────────
    def _mes_anterior(self):
        if self._mes == 1:
            self._mes = 12
            self._año -= 1
        else:
            self._mes -= 1
        self._renderizar_mes()
        # Mantener detalle si el día seleccionado está en el nuevo mes
        if self._sel.month == self._mes and self._sel.year == self._año:
            self._mostrar_detalle(self._sel)
        else:
            self._det_titulo.config(text=_cal_tx("sel_dia"))
            for w in self._det_inner.winfo_children():
                w.destroy()

    def _mes_siguiente(self):
        if self._mes == 12:
            self._mes = 1
            self._año += 1
        else:
            self._mes += 1
        self._renderizar_mes()
        if self._sel.month == self._mes and self._sel.year == self._año:
            self._mostrar_detalle(self._sel)
        else:
            self._det_titulo.config(text=_cal_tx("sel_dia"))
            for w in self._det_inner.winfo_children():
                w.destroy()

    def _ir_hoy(self):
        self._mes  = self._hoy.month
        self._año  = self._hoy.year
        self._sel  = self._hoy
        self._renderizar_mes()
        self._mostrar_detalle(self._hoy)

    # ── Ciclo de vida ────────────────────────────────────────
    def mostrar(self):
        self.frame.pack(fill="both", expand=True)
        self._renderizar_mes()
        self._seleccionar_dia(self._hoy)

    def ocultar(self):
        self.frame.pack_forget()