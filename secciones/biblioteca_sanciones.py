"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Módulo de sanciones y configuración de préstamos.
                 - SeccionSanciones   : Panel admin para ver, cobrar y condonar sanciones.
                 - SeccionConfigPrest : Subpanel de configuración (días, tarifa, etc.).
                 - Helpers compartidos: leer_config(), calcular_sancion(), etc.
Autor/a:         Luis Villegas Rivera
Fecha:           2026-03-09
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime, date, timedelta

from secciones.biblioteca_gestion_libros import (
    aplicar_tema,
    COLOR_BG, COLOR_CARD, COLOR_CARD2, COLOR_GOLD, COLOR_GOLD_DIM,
    COLOR_TEXT, COLOR_DIM, COLOR_ERROR, COLOR_SUCCESS,
    FONT_TITLE, FONT_LABEL, FONT_ENTRY, FONT_SMALL, FONT_BTN,
)
from secciones.biblioteca_ajustes import T


# ═══════════════════════════════════════════
# HELPERS COMPARTIDOS  (importables por otros módulos)
# ═══════════════════════════════════════════

def leer_config(db_path: str) -> dict:
    """Devuelve el dict de configuración de préstamos desde la BD."""
    defaults = {
        "max_dias":             15,
        "dias_por_dia_retraso": 2,
        "max_prestamos":        3,
        "bloquear_sancionados": 1,
        "aviso_dias_antes":     3,
    }
    try:
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()
        cur.execute("SELECT clave, valor FROM configuracion_prestamos")
        for clave, valor in cur.fetchall():
            try:
                defaults[clave] = float(valor) if "." in valor else int(valor)
            except ValueError:
                defaults[clave] = valor
        conn.close()
    except sqlite3.Error:
        pass
    return defaults


def guardar_config(db_path: str, cfg: dict) -> None:
    """Persiste el dict de configuración en la BD."""
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    for clave, valor in cfg.items():
        cur.execute(
            "INSERT INTO configuracion_prestamos (clave, valor) VALUES (?,?) "
            "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
            (clave, str(valor))
        )
    conn.commit()
    conn.close()


def calcular_dias_retraso(fecha_dev_estimada: str) -> int:
    """Devuelve los días de retraso respecto a hoy (0 si no hay retraso)."""
    try:
        limite = datetime.strptime(fecha_dev_estimada, "%Y-%m-%d")
        retraso = (datetime.now() - limite).days
        return max(0, retraso)
    except ValueError:
        return 0


def estado_prestamo(fecha_dev_estimada: str, aviso_dias: int = 3) -> str:
    """
    Devuelve el estado visual de un préstamo activo:
      'vencido'  — ya pasó la fecha límite
      'aviso'    — faltan ≤ aviso_dias días
      'ok'       — dentro del plazo
    """
    try:
        limite = datetime.strptime(fecha_dev_estimada, "%Y-%m-%d")
        dias_restantes = (limite - datetime.now()).days
        if dias_restantes < 0:
            return "vencido"
        if dias_restantes <= aviso_dias:
            return "aviso"
        return "ok"
    except ValueError:
        return "ok"


def esta_sancionado(db_path: str, id_usuario: int) -> bool:
    """
    True si el usuario tiene suspension activa HOY
    (fecha_inicio <= hoy <= fecha_fin y no anulada).
    Expira automaticamente cuando pasa fecha_fin.
    """
    hoy = date.today().isoformat()
    try:
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM sanciones "
            "WHERE id_usuario=? AND anulada=0 "
            "  AND fecha_inicio <= ? AND fecha_fin >= ?",
            (id_usuario, hoy, hoy)
        )
        n = cur.fetchone()[0]
        conn.close()
        return n > 0
    except sqlite3.Error:
        return False


def dias_suspension_restantes(db_path: str, id_usuario: int) -> int:
    """Dias que quedan de la sancion activa mas larga. 0 si no hay."""
    hoy = date.today().isoformat()
    try:
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()
        cur.execute(
            "SELECT MAX(fecha_fin) FROM sanciones "
            "WHERE id_usuario=? AND anulada=0 AND fecha_fin >= ?",
            (id_usuario, hoy)
        )
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            fin = date.fromisoformat(row[0])
            return max(0, (fin - date.today()).days + 1)
        return 0
    except sqlite3.Error:
        return 0


def registrar_sancion(db_path: str, id_prestamo: int, id_usuario: int,
                      dias_retraso: int, factor: int = 2) -> int:
    """
    Crea una sancion de suspension automaticamente.
    dias_suspension = dias_retraso * factor.
    La sancion comienza hoy y termina en dias_suspension dias.
    No duplica si ya existe una para ese prestamo.
    Devuelve los dias de suspension aplicados.
    """
    dias_suspension = dias_retraso * factor
    hoy = date.today()
    fecha_inicio = hoy.isoformat()
    fecha_fin    = (hoy + timedelta(days=dias_suspension - 1)).isoformat()
    try:
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()
        cur.execute("SELECT id_sancion FROM sanciones WHERE id_prestamo=?",
                    (id_prestamo,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO sanciones "
                "(id_prestamo, id_usuario, dias_retraso, dias_suspension, "
                " fecha_inicio, fecha_fin) "
                "VALUES (?,?,?,?,?,?)",
                (id_prestamo, id_usuario, dias_retraso,
                 dias_suspension, fecha_inicio, fecha_fin)
            )
            conn.commit()
        conn.close()
    except sqlite3.Error:
        pass
    return dias_suspension


# ═══════════════════════════════════════════
# PANEL ADMIN — Sanciones
# ═══════════════════════════════════════════
COLOR_WARN = "#b8a230"   # amarillo/aviso



COLOR_WARN = "#b8a230"   # amarillo/aviso — exportado a otros modulos


# ===========================================
# PANEL ADMIN — Solo consulta, sin acciones manuales
# ===========================================
class SeccionSanciones:
    """
    Panel administrativo con dos pestanas:
      1. Sanciones activas e historial (lectura + anular en caso extremo).
      2. Configuracion de prestamos y reglas de suspension.
    """

    def __init__(self, parent: tk.Widget, db_path: str, usuario: str):
        aplicar_tema()
        self.db_path = db_path
        self.usuario = usuario
        self.frame   = tk.Frame(parent, bg=COLOR_BG)
        self._build_ui()

    def _build_ui(self):
        cab = tk.Frame(self.frame, bg=COLOR_CARD, height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text="⚦–  Sanciones y Configuracion",
                 font=FONT_TITLE, bg=COLOR_CARD, fg=COLOR_GOLD
                 ).pack(side="left", padx=24, pady=12)
        tk.Frame(self.frame, height=1, bg=COLOR_GOLD_DIM).pack(fill="x")

        nb_style = ttk.Style()
        nb_style.configure("Bib.TNotebook",     background=COLOR_BG, borderwidth=0)
        nb_style.configure("Bib.TNotebook.Tab",
                           background=COLOR_CARD, foreground=COLOR_DIM,
                           font=("Georgia", 10, "bold"), padding=[16, 6])
        nb_style.map("Bib.TNotebook.Tab",
                     background=[("selected", COLOR_GOLD_DIM)],
                     foreground=[("selected", COLOR_TEXT)])

        nb = ttk.Notebook(self.frame, style="Bib.TNotebook")
        nb.pack(fill="both", expand=True, padx=16, pady=12)

        tab_sanc = tk.Frame(nb, bg=COLOR_BG)
        tab_cfg  = tk.Frame(nb, bg=COLOR_BG)
        nb.add(tab_sanc, text="  Sanciones  ")
        nb.add(tab_cfg,  text="  Configuracion  ")

        self._build_tab_sanciones(tab_sanc)
        self._build_tab_config(tab_cfg)

    def _estado_sancion(self, fecha_inicio, fecha_fin, anulada):
        if anulada:
            return "Anulada"
        hoy = date.today().isoformat()
        if fecha_fin < hoy:
            return "Expirada"
        if fecha_inicio > hoy:
            return "Pendiente"
        return "Activa"

    def _build_tab_sanciones(self, parent):
        body = tk.Frame(parent, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)

        left = tk.Frame(body, bg=COLOR_CARD, width=260,
                        highlightthickness=1, highlightbackground=COLOR_GOLD_DIM)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        tk.Label(left, text="DETALLE",
                 font=("Georgia", 9, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w", padx=18, pady=(18, 4))
        tk.Frame(left, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=18)

        self._det = {}
        for key, lbl in [("id","ID"), ("socio","Socio"), ("prestamo","Prestamo"),
                         ("retraso","Dias retraso"), ("suspension","Dias suspension"),
                         ("inicio","Inicio"), ("fin","Fin suspension"), ("estado","Estado")]:
            tk.Label(left, text=lbl, font=FONT_SMALL,
                     bg=COLOR_CARD, fg=COLOR_DIM).pack(anchor="w", padx=18, pady=(8,0))
            v = tk.Label(left, text="--", font=("Georgia", 10),
                         bg=COLOR_CARD, fg=COLOR_TEXT, anchor="w", wraplength=220)
            v.pack(anchor="w", padx=18)
            self._det[key] = v

        tk.Frame(left, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=18, pady=(14,0))
        tk.Label(left, text="Las sanciones se aplican y\nexpiran automaticamente.\nNo se requiere intervencion.",
                 font=("Georgia", 8, "italic"), bg=COLOR_CARD, fg=COLOR_DIM,
                 justify="left").pack(padx=18, pady=(10,0), anchor="w")

        self._msg_s = tk.Label(left, text="", font=("Georgia", 9, "italic"),
                               bg=COLOR_CARD, fg=COLOR_ERROR, wraplength=230)
        self._msg_s.pack(padx=18, pady=(10,0), anchor="w")

        btn_anular = tk.Button(left, text="Anular sancion (casos excepcionales)",
                               font=("Georgia", 8, "bold"), bg="#1a1010", fg="#8a4a4a",
                               activebackground="#3a1010", activeforeground=COLOR_TEXT,
                               relief="flat", bd=0, cursor="hand2",
                               command=self._anular_sancion)
        btn_anular.pack(fill="x", padx=18, pady=(12, 20), ipady=6)

        right = tk.Frame(body, bg=COLOR_BG)
        right.pack(side="left", fill="both", expand=True)

        filt = tk.Frame(right, bg=COLOR_BG)
        filt.pack(fill="x", pady=(0, 8))
        self._filtro_estado = tk.StringVar(value="activas")
        for txt, val in [("Activas","activas"), ("Historial","historial"), ("Todas","todas")]:
            tk.Radiobutton(filt, text=txt, variable=self._filtro_estado, value=val,
                           font=FONT_SMALL, bg=COLOR_BG, fg=COLOR_TEXT,
                           selectcolor=COLOR_CARD, activebackground=COLOR_BG,
                           command=self._cargar_tabla_sanciones).pack(side="left", padx=(0,10))
        tk.Label(filt, text="  🔍", font=("Georgia", 11),
                 bg=COLOR_BG, fg=COLOR_DIM).pack(side="left")
        self._busq_s = tk.StringVar()
        self._busq_s.trace_add("write", lambda *_: self._cargar_tabla_sanciones())
        tk.Entry(filt, textvariable=self._busq_s, font=("Georgia", 11),
                 bg=COLOR_CARD2, fg=COLOR_TEXT, insertbackground=COLOR_GOLD,
                 relief="flat", highlightthickness=1, highlightbackground=COLOR_GOLD_DIM
                 ).pack(side="left", fill="x", expand=True, ipady=5, padx=(4,0))

        ley = tk.Frame(right, bg=COLOR_BG)
        ley.pack(fill="x", pady=(0, 6))
        for color, txt in [(COLOR_ERROR,"Activa"), (COLOR_WARN,"Pendiente"),
                           (COLOR_SUCCESS,"Expirada"), (COLOR_DIM,"Anulada")]:
            tk.Label(ley, text="\u25a0", font=("Georgia", 10),
                     bg=COLOR_BG, fg=color).pack(side="left")
            tk.Label(ley, text=f" {txt}   ", font=FONT_SMALL,
                     bg=COLOR_BG, fg=COLOR_DIM).pack(side="left")

        cols = ("ID","Socio","Prest.","Retraso","Suspension","Inicio","Fin","Estado")
        ts = ttk.Style()
        ts.configure("Bib.Treeview", background=COLOR_CARD2, foreground=COLOR_TEXT,
                     fieldbackground=COLOR_CARD2, rowheight=26, font=("Georgia", 10))
        ts.configure("Bib.Treeview.Heading", background=COLOR_CARD, foreground=COLOR_GOLD,
                     font=("Georgia", 9, "bold"), relief="flat")
        ts.map("Bib.Treeview", background=[("selected", COLOR_GOLD_DIM)])

        tf = tk.Frame(right, bg=COLOR_BG)
        tf.pack(fill="both", expand=True)
        self.tree_s = ttk.Treeview(tf, columns=cols, show="headings",
                                   style="Bib.Treeview", selectmode="browse")
        for col, w in zip(cols, [40,150,60,70,90,95,95,80]):
            self.tree_s.heading(col, text=col)
            self.tree_s.column(col, width=w, minwidth=40)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree_s.yview)
        self.tree_s.configure(yscrollcommand=vsb.set)
        self.tree_s.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree_s.bind("<<TreeviewSelect>>", self._on_select_sancion)
        self._cargar_tabla_sanciones()

    def _cargar_tabla_sanciones(self):
        for r in self.tree_s.get_children():
            self.tree_s.delete(r)
        filtro = f"%{self._busq_s.get().strip()}%"
        estado = self._filtro_estado.get()
        hoy    = date.today().isoformat()
        q = """
            SELECT s.id_sancion, u.nombre, s.id_prestamo,
                   s.dias_retraso, s.dias_suspension,
                   s.fecha_inicio, s.fecha_fin, s.anulada
            FROM sanciones s
            JOIN usuarios u ON s.id_usuario = u.id_usuario
            WHERE (u.nombre LIKE ? OR CAST(s.id_prestamo AS TEXT) LIKE ?)
        """
        params = [filtro, filtro]
        if estado == "activas":
            q += f" AND s.anulada=0 AND s.fecha_inicio<='{hoy}' AND s.fecha_fin>='{hoy}'"
        elif estado == "historial":
            q += f" AND (s.anulada=1 OR s.fecha_fin<'{hoy}')"
        q += " ORDER BY s.id_sancion DESC"
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute(q, params)
            for fila in cur.fetchall():
                est = self._estado_sancion(fila[5], fila[6], fila[7])
                tag = {"Activa":"activa","Pendiente":"pendiente",
                       "Expirada":"expirada","Anulada":"anulada"}.get(est,"")
                vals = [fila[0], fila[1], fila[2],
                        f"{fila[3]}d", f"{fila[4]}d",
                        fila[5], fila[6], est]
                self.tree_s.insert("", "end", values=vals, tags=(tag,))
            self.tree_s.tag_configure("activa",    foreground=COLOR_ERROR)
            self.tree_s.tag_configure("pendiente", foreground=COLOR_WARN)
            self.tree_s.tag_configure("expirada",  foreground=COLOR_SUCCESS)
            self.tree_s.tag_configure("anulada",   foreground=COLOR_DIM)
            conn.close()
        except sqlite3.Error as e:
            self._msg_s.config(text=f"Error BD: {e}", fg=COLOR_ERROR)

    def _on_select_sancion(self, _=None):
        sel = self.tree_s.selection()
        if not sel: return
        v = self.tree_s.item(sel[0], "values")
        self._det["id"].config(text=v[0])
        self._det["socio"].config(text=v[1])
        self._det["prestamo"].config(text=f"#{v[2]}")
        self._det["retraso"].config(text=v[3])
        self._det["suspension"].config(text=v[4])
        self._det["inicio"].config(text=v[5])
        self._det["fin"].config(text=v[6])
        color = {"Activa":COLOR_ERROR,"Pendiente":COLOR_WARN,
                 "Expirada":COLOR_SUCCESS,"Anulada":COLOR_DIM}.get(v[7], COLOR_TEXT)
        self._det["estado"].config(text=v[7], fg=color)
        self._msg_s.config(text="")

    def _anular_sancion(self):
        sel = self.tree_s.selection()
        if not sel:
            self._msg_s.config(text="Selecciona una sancion.", fg=COLOR_ERROR)
            return
        v = self.tree_s.item(sel[0], "values")
        if v[7] in ("Expirada", "Anulada"):
            self._msg_s.config(text=f"Esta sancion ya esta {v[7].lower()}.", fg=COLOR_ERROR)
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("UPDATE sanciones SET anulada=1 WHERE id_sancion=?", (v[0],))
            conn.commit()
            conn.close()
            self._msg_s.config(text="Sancion anulada.", fg=COLOR_SUCCESS)
            self._cargar_tabla_sanciones()
            for k in self._det: self._det[k].config(text="--")
        except sqlite3.Error as e:
            self._msg_s.config(text=f"Error BD: {e}", fg=COLOR_ERROR)

    def _build_tab_config(self, parent):
        cfg = leer_config(self.db_path)
        outer = tk.Frame(parent, bg=COLOR_BG)
        outer.pack(fill="both", expand=True, padx=20, pady=20)
        card = tk.Frame(outer, bg=COLOR_CARD,
                        highlightthickness=1, highlightbackground=COLOR_GOLD_DIM)
        card.pack(anchor="n", fill="x")

        tk.Label(card, text="PARAMETROS DE PRESTAMO",
                 font=("Georgia", 9, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w", padx=24, pady=(20, 4))
        tk.Frame(card, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=24)

        self._cfg_vars = {}
        campos = [
            ("max_dias", "Dias maximos de prestamo",
             "Numero de dias que un socio puede tener un libro.", "int"),
            ("dias_por_dia_retraso", "Dias de suspension por cada dia de retraso",
             "Ejemplo: con valor 2, devolver 3 dias tarde = 6 dias sin poder pedir libros.", "int"),
            ("max_prestamos", "Maximo de prestamos simultaneos",
             "Un socio no puede tener mas libros que este numero a la vez.", "int"),
            ("aviso_dias_antes", "Dias de antelacion para aviso de vencimiento",
             "Los prestamos proximos a vencer se marcan en amarillo.", "int"),
            ("bloquear_sancionados", "Bloquear socios con suspension activa",
             "Si esta activo, los socios en periodo de suspension no pueden pedir libros.", "bool"),
        ]
        for clave, titulo, desc, tipo in campos:
            row = tk.Frame(card, bg=COLOR_CARD)
            row.pack(fill="x", padx=24, pady=(14, 0))
            tk.Label(row, text=titulo, font=("Georgia", 10, "bold"),
                     bg=COLOR_CARD, fg=COLOR_TEXT, anchor="w").pack(fill="x")
            tk.Label(row, text=desc, font=("Georgia", 8, "italic"),
                     bg=COLOR_CARD, fg=COLOR_DIM, anchor="w", wraplength=480).pack(fill="x")
            if tipo == "bool":
                var = tk.IntVar(value=int(cfg.get(clave, 1)))
                self._cfg_vars[clave] = ("bool", var)
                tk.Checkbutton(row, text="Activado", variable=var,
                               font=("Georgia", 10), bg=COLOR_CARD, fg=COLOR_TEXT,
                               selectcolor=COLOR_CARD2, activebackground=COLOR_CARD,
                               onvalue=1, offvalue=0).pack(anchor="w", pady=(4, 0))
            else:
                var = tk.StringVar(value=str(cfg.get(clave, "")))
                self._cfg_vars[clave] = (tipo, var)
                tk.Entry(row, textvariable=var, font=("Georgia", 12), width=10,
                         bg=COLOR_CARD2, fg=COLOR_TEXT, insertbackground=COLOR_GOLD,
                         relief="flat", highlightthickness=1,
                         highlightbackground=COLOR_GOLD_DIM, highlightcolor=COLOR_GOLD
                         ).pack(anchor="w", ipady=5, pady=(4, 0))

        tk.Frame(card, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=24, pady=(18,0))
        self._msg_cfg = tk.Label(card, text="", font=("Georgia", 9, "italic"),
                                 bg=COLOR_CARD, fg=COLOR_SUCCESS, wraplength=480)
        self._msg_cfg.pack(padx=24, pady=(10, 0), anchor="w")
        btn = tk.Button(card, text="Guardar configuracion",
                        font=FONT_BTN, bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
                        activebackground=COLOR_GOLD, activeforeground="#000",
                        relief="flat", bd=0, cursor="hand2",
                        command=self._guardar_config)
        btn.pack(fill="x", padx=24, pady=(10, 24), ipady=9)
        btn.bind("<Enter>", lambda _: btn.config(bg=COLOR_GOLD, fg="#000"))
        btn.bind("<Leave>", lambda _: btn.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))

    def _guardar_config(self):
        nuevos = {}
        for clave, (tipo, var) in self._cfg_vars.items():
            raw = var.get()
            try:
                v = int(raw) if tipo == "int" else int(raw) if tipo == "bool" else raw
                if tipo == "int" and v < 1: raise ValueError
                nuevos[clave] = v
            except ValueError:
                self._msg_cfg.config(
                    text=f"Valor invalido para '{clave}'. Debe ser entero positivo.",
                    fg=COLOR_ERROR)
                return
        try:
            guardar_config(self.db_path, nuevos)
            self._msg_cfg.config(text="Configuracion guardada.", fg=COLOR_SUCCESS)
        except Exception as e:
            self._msg_cfg.config(text=f"Error: {e}", fg=COLOR_ERROR)

    def mostrar(self):
        self.frame.pack(fill="both", expand=True)
        self._cargar_tabla_sanciones()

    def ocultar(self):
        self.frame.pack_forget()