"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Módulo de ajustes de la aplicación. Permite al usuario
                 gestionar su cuenta (nombre, contraseña, correo, teléfono,
                 eliminar cuenta) y personalizar la apariencia (tema, acento,
                 fuente, idioma). La configuración se persiste en config.json.
Autor/a:         Luis Villegas Rivera
Fecha:           2026-03-09
Clases principales:
    - ConfigApp      : Carga, guarda y provee la configuración global.
    - SeccionAjustes : Panel tkinter de ajustes (cuenta + apariencia).
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
import hashlib
import json
import os
import re

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# ═══════════════════════════════════════════════════════
# CONFIGURACIÓN — Temas, acentos, fuentes, idiomas
# ═══════════════════════════════════════════════════════

TEMAS = {
    "oscuro": {
        "bg": "#0e0d12", "card": "#13121a", "card2": "#1a1820",
        "sidebar": "#0b0a10", "text": "#e8dfc8", "dim": "#8a7f6a",
        "sep": "#7a5f28", "error": "#c45a3a", "success": "#4a8c5a",
        "nombre": "Oscuro"
    },
    "claro": {
        "bg": "#f0ece0", "card": "#ffffff", "card2": "#f8f4ec",
        "sidebar": "#e4ddd0", "text": "#2a2018", "dim": "#6a5f50",
        "sep": "#b09060", "error": "#b03020", "success": "#3a7c4a",
        "nombre": "Claro"
    },
    "sepia": {
        "bg": "#211508", "card": "#2e1e0e", "card2": "#362416",
        "sidebar": "#180e04", "text": "#e8d8b0", "dim": "#9a8060",
        "sep": "#7a5020", "error": "#c05030", "success": "#508040",
        "nombre": "Sepia"
    },
    "noche": {
        "bg": "#080c18", "card": "#0e1628", "card2": "#141e34",
        "sidebar": "#060a14", "text": "#c8d8e8", "dim": "#60788a",
        "sep": "#2a4060", "error": "#c04050", "success": "#30786a",
        "nombre": "Noche"
    },
}

ACENTOS = {
    "dorado": {"color": "#c9a84c", "dim": "#7a5f28", "nombre": "Dorado"},
    "azul":   {"color": "#4a9acf", "dim": "#2a5a80", "nombre": "Azul"},
    "verde":  {"color": "#5aac6a", "dim": "#2a6a3a", "nombre": "Verde"},
    "malva":  {"color": "#9a6ab0", "dim": "#5a3a70", "nombre": "Malva"},
    "coral":  {"color": "#d07050", "dim": "#804030", "nombre": "Coral"},
}

FUENTES = {
    "pequeño": {"titulo": 13, "cuerpo": 9,  "entry": 10, "btn": 9,  "small": 8,  "nombre": "Pequeño"},
    "normal":  {"titulo": 16, "cuerpo": 10, "entry": 12, "btn": 10, "small": 9,  "nombre": "Normal"},
    "grande":  {"titulo": 19, "cuerpo": 12, "entry": 14, "btn": 12, "small": 11, "nombre": "Grande"},
}

IDIOMAS = {
    "es": {
        "nombre": "Español",
        "cuenta": "Mi Cuenta",
        "apariencia": "Apariencia",
        "info": "Información personal",
        "seguridad": "Seguridad",
        "peligro": "Zona de peligro",
        "nombre_usuario": "Nombre de usuario",
        "correo": "Correo electrónico",
        "telefono": "Teléfono",
        "pass_actual": "Contraseña actual",
        "pass_nueva": "Nueva contraseña",
        "pass_confirmar": "Confirmar nueva contraseña",
        "guardar": "Guardar cambios",
        "cambiar_pass": "Cambiar contraseña",
        "eliminar_cuenta": "Eliminar cuenta",
        "confirm_eliminar": "Confirmar eliminación",
        "tema": "Tema de color",
        "acento": "Color de acento",
        "fuente": "Tamaño de fuente",
        "idioma": "Idioma",
        "aplicar": "Aplicar apariencia",
        "reiniciar_nota": "Los cambios de apariencia se aplican al recargar el menú.",
        "pass_requerida": "Introduce tu contraseña actual para confirmar.",
        "error_pass": "Contraseña actual incorrecta.",
        "error_nombre_vacio": "El nombre no puede estar vacío.",
        "error_nombre_existe": "Ese nombre de usuario ya existe.",
        "ok_info": "Información actualizada correctamente.",
        "ok_pass": "Contraseña cambiada correctamente.",
        "ok_apariencia": "Apariencia guardada. Recargando...",
        "eliminar_aviso": "Esta acción es irreversible.\nEscribe tu contraseña para confirmar.",
        "ok_eliminado": "Cuenta eliminada. Cerrando sesión...",
        # Menú principal
        "menu_admin_lbl":    "ADMINISTRACIÓN",
        "menu_normal_lbl":   "MI BIBLIOTECA",
        "menu_libros":       "📚  Libros",
        "menu_socios":       "👤  Socios",
        "menu_prestamos":    "🔖  Préstamos",
        "menu_catalogo":     "📚  Catálogo",
        "menu_misprestamos": "🔖  Mis préstamos",
        "menu_sanciones":    "⚖  Sanciones",
        "menu_calendario":   "📅  Calendario",
        "cab_calendario":    "📅  Calendario de Préstamos",
        "menu_facturas":     "🧾  Facturas",
        "cab_facturas":      "🧾  Facturas y Recibos",
        "cerrar_sesion":     "Cerrar sesión",
        "ajustes":           "⚙  Ajustes",
        "selecciona_seccion": "Selecciona una sección",
        "cargando":          "Cargando...",
        # Secciones
        "cab_libros":        "📚  Catálogo de Libros",
        "cab_socios":        "👤  Gestión de Socios",
        "cab_prestamos":     "🔖  Préstamos y Devoluciones",
        "cab_catalogo":      "📚  Catálogo",
        "cab_misprestamos":  "🔖  Mis Préstamos",
        "solo_lectura":      "(solo lectura)",
        "añadir_libro":      "AÑADIR LIBRO",
        "detalle_socio":     "DETALLE DEL SOCIO",
        "nuevo_prestamo":    "NUEVO PRÉSTAMO",
        "devolucion_hdr":    "DEVOLUCIÓN",
        "solicitar_prestamo":"SOLICITAR PRÉSTAMO",
        "btn_añadir":        "＋  Agregar libro",
        "btn_eliminar_sel":  "✕  Eliminar seleccionado",
        "btn_eliminar_socio":"✕  Eliminar socio",
        "btn_prestamo":      "＋  Registrar préstamo",
        "btn_devolucion":    "↩  Registrar devolución",
        "btn_solicitar":     "＋  Solicitar préstamo",
        "sel_prestamo_tabla":"Selecciona un préstamo activo en la tabla",
        "solo_disponibles":  "Solo disponibles",
        "solo_activos":      "Solo préstamos activos",
        "lbl_socio":         "Socio",
        "lbl_libro":         "Libro",
        "lbl_isbn":          "ISBN del libro",
        "mis_activos":       "Mis préstamos activos",
        "tu_id":             "Tu ID de socio",
        "usa_isbn":          "Usa el ISBN del catálogo para solicitar un préstamo.",
    },
    "en": {
        "nombre": "English",
        "cuenta": "My Account",
        "apariencia": "Appearance",
        "info": "Personal information",
        "seguridad": "Security",
        "peligro": "Danger zone",
        "nombre_usuario": "Username",
        "correo": "Email address",
        "telefono": "Phone",
        "pass_actual": "Current password",
        "pass_nueva": "New password",
        "pass_confirmar": "Confirm new password",
        "guardar": "Save changes",
        "cambiar_pass": "Change password",
        "eliminar_cuenta": "Delete account",
        "confirm_eliminar": "Confirm deletion",
        "tema": "Color theme",
        "acento": "Accent color",
        "fuente": "Font size",
        "idioma": "Language",
        "aplicar": "Apply appearance",
        "reiniciar_nota": "Appearance changes take effect after reloading the menu.",
        "pass_requerida": "Enter your current password to confirm.",
        "error_pass": "Incorrect current password.",
        "error_nombre_vacio": "Username cannot be empty.",
        "error_nombre_existe": "That username already exists.",
        "ok_info": "Information updated successfully.",
        "ok_pass": "Password changed successfully.",
        "ok_apariencia": "Appearance saved. Reloading...",
        "eliminar_aviso": "This action is irreversible.\nEnter your password to confirm.",
        "ok_eliminado": "Account deleted. Logging out...",
        # Main menu
        "menu_admin_lbl":    "ADMINISTRATION",
        "menu_normal_lbl":   "MY LIBRARY",
        "menu_libros":       "📚  Books",
        "menu_socios":       "👤  Members",
        "menu_prestamos":    "🔖  Loans",
        "menu_sanciones":    "⚖  Sanctions",
        "menu_calendario":   "📅  Calendar",
        "cab_calendario":    "📅  Loans Calendar",
        "menu_facturas":     "🧾  Invoices",
        "cab_facturas":      "🧾  Invoices & Receipts",
        "menu_catalogo":     "📚  Catalogue",
        "menu_misprestamos": "🔖  My loans",
        "cerrar_sesion":     "Log out",
        "ajustes":           "⚙  Settings",
        "selecciona_seccion": "Select a section",
        "cargando":          "Loading...",
        # Sections
        "cab_libros":        "📚  Book Catalogue",
        "cab_socios":        "👤  Member Management",
        "cab_prestamos":     "🔖  Loans & Returns",
        "cab_catalogo":      "📚  Catalogue",
        "cab_misprestamos":  "🔖  My Loans",
        "solo_lectura":      "(read only)",
        "añadir_libro":      "ADD BOOK",
        "detalle_socio":     "MEMBER DETAIL",
        "nuevo_prestamo":    "NEW LOAN",
        "devolucion_hdr":    "RETURN",
        "solicitar_prestamo":"REQUEST LOAN",
        "btn_añadir":        "＋  Add book",
        "btn_eliminar_sel":  "✕  Delete selected",
        "btn_eliminar_socio":"✕  Delete member",
        "btn_prestamo":      "＋  Register loan",
        "btn_devolucion":    "↩  Register return",
        "btn_solicitar":     "＋  Request loan",
        "sel_prestamo_tabla":"Select an active loan from the table",
        "solo_disponibles":  "Available only",
        "solo_activos":      "Active loans only",
        "lbl_socio":         "Member",
        "lbl_libro":         "Book",
        "lbl_isbn":          "Book ISBN",
        "mis_activos":       "My active loans",
        "tu_id":             "Your member ID",
        "usa_isbn":          "Use the catalogue ISBN to request a loan.",
    },
}

DEFAULTS = {
    "tema":    "oscuro",
    "acento":  "dorado",
    "fuente":  "normal",
    "idioma":  "es",
}


# ═══════════════════════════════════════════
# Función de traducción global
# ═══════════════════════════════════════════
def T(clave: str, fallback: str = "") -> str:
    """
    Devuelve la cadena traducida al idioma activo.
    Uso: T("guardar") → "Save changes" / "Guardar cambios"
    Nota: ConfigApp se define después — se resuelve en tiempo de ejecución.
    """
    try:
        idioma = _leer_idioma()
        return IDIOMAS.get(idioma, IDIOMAS["es"]).get(clave, fallback or clave)
    except Exception:
        return fallback or clave


def _leer_idioma() -> str:
    """Lee el idioma del config.json sin depender de ConfigApp (evita circular)."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("idioma", "es")
    except Exception:
        return "es"


# ═══════════════════════════════════════════
# CLASE ConfigApp
# ═══════════════════════════════════════════
class ConfigApp:
    """
    Gestiona la configuración persistente de la aplicación.
    Lee y escribe config.json en la raíz del proyecto.
    """
    _datos: dict = None

    @classmethod
    def cargar(cls) -> dict:
        if cls._datos is None:
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cargado = json.load(f)
                # Rellenar claves que falten con defaults
                cls._datos = {**DEFAULTS, **cargado}
            except (FileNotFoundError, json.JSONDecodeError):
                cls._datos = dict(DEFAULTS)
        return cls._datos

    @classmethod
    def guardar(cls, datos: dict) -> None:
        cls._datos = {**DEFAULTS, **datos}
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cls._datos, f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise IOError(f"No se pudo guardar la configuración: {e}")

    @classmethod
    def get(cls, clave: str):
        return cls.cargar().get(clave, DEFAULTS.get(clave))

    @classmethod
    def colores(cls) -> dict:
        """Devuelve el dict de colores del tema activo con el acento aplicado."""
        tema   = cls.get("tema")
        acento = cls.get("acento")
        c = dict(TEMAS.get(tema, TEMAS["oscuro"]))
        ac = ACENTOS.get(acento, ACENTOS["dorado"])
        c["acento"]     = ac["color"]
        c["acento_dim"] = ac["dim"]
        return c

    @classmethod
    def fuentes(cls) -> dict:
        return FUENTES.get(cls.get("fuente"), FUENTES["normal"])

    @classmethod
    def txt(cls) -> dict:
        return IDIOMAS.get(cls.get("idioma"), IDIOMAS["es"])

    @classmethod
    def invalidar(cls):
        """Fuerza recarga desde disco en próximo acceso."""
        cls._datos = None


# ── Utilidades ───────────────────────────────────────────────
def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _validar_pass(p: str) -> bool:
    return (len(p) >= 8
            and bool(re.search(r"[A-Z]", p))
            and bool(re.search(r"[a-z]", p))
            and bool(re.search(r"[0-9]", p))
            and bool(re.search(r'[!@#$%^&*(),.?\":{}|<>]', p)))


# ═══════════════════════════════════════════
# SECCIÓN TKINTER — Ajustes
# ═══════════════════════════════════════════
class SeccionAjustes:
    """
    Panel de ajustes con dos pestañas:
      - Mi Cuenta   : nombre, correo, teléfono, contraseña, eliminar cuenta.
      - Apariencia  : tema, acento, tamaño fuente, idioma.
    """

    def __init__(self, parent: tk.Widget, db_path: str,
                 usuario: str, rol: str = "normal",
                 on_apply=None):
        self.db_path  = db_path
        self.usuario  = usuario
        self.rol      = rol
        self.on_apply = on_apply   # callable(accion, **kwargs)

        self._c  = ConfigApp.colores()
        self._f  = ConfigApp.fuentes()
        self._tx = ConfigApp.txt()

        self.frame = tk.Frame(parent, bg=self._c["bg"])
        self._panel_activo = None
        self._build_ui()

    # ── UI principal ─────────────────────────────────────────
    def _build_ui(self):
        c, f, tx = self._c, self._f, self._tx

        # Cabecera
        cab = tk.Frame(self.frame, bg=c["card"], height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text="⚙  Ajustes",
                 font=("Georgia", f["titulo"], "bold"),
                 bg=c["card"], fg=c["acento"]).pack(side="left", padx=24, pady=12)
        tk.Frame(self.frame, height=1, bg=c["sep"]).pack(fill="x")

        body = tk.Frame(self.frame, bg=c["bg"])
        body.pack(fill="both", expand=True)

        # ── Tabs laterales ──
        tabs = tk.Frame(body, bg=c["sidebar"], width=170)
        tabs.pack(side="left", fill="y")
        tabs.pack_propagate(False)

        tk.Label(tabs, text="AJUSTES",
                 font=("Georgia", 8, "bold"),
                 bg=c["sidebar"], fg=c["dim"]).pack(anchor="w", padx=20, pady=(20, 8))
        tk.Frame(tabs, height=1, bg=c["sep"]).pack(fill="x", padx=14, pady=(0, 8))

        self._tab_btns = {}
        tabs_def = [
            ("cuenta",     f"👤  {tx['cuenta']}"),
            ("apariencia", f"🎨  {tx['apariencia']}"),
        ]
        for key, label in tabs_def:
            btn = tk.Button(
                tabs, text=label,
                font=("Georgia", f["btn"]), bg=c["sidebar"], fg=c["dim"],
                activebackground=c["card"], activeforeground=c["text"],
                relief="flat", bd=0, cursor="hand2", anchor="w", padx=20, pady=10)
            btn.config(command=lambda k=key, b=btn: self._switch_tab(k, b))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=c["card"])
                     if b is not self._btn_tab_activo else None)
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=c["sidebar"])
                     if b is not self._btn_tab_activo else None)
            btn.pack(fill="x")
            self._tab_btns[key] = btn

        self._btn_tab_activo = None

        # ── Área de contenido ──
        self._area = tk.Frame(body, bg=c["bg"])
        self._area.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # Construir paneles
        self._panel_cuenta     = self._build_panel_cuenta()
        self._panel_apariencia = self._build_panel_apariencia()

        # Abrir pestaña cuenta por defecto
        self._switch_tab("cuenta", self._tab_btns["cuenta"])

    def _switch_tab(self, key, boton):
        if self._panel_activo:
            self._panel_activo.pack_forget()
        if self._btn_tab_activo:
            self._btn_tab_activo.config(bg=self._c["sidebar"], fg=self._c["dim"])
        boton.config(bg=self._c["card"], fg=self._c["acento"])
        self._btn_tab_activo = boton

        if key == "cuenta":
            self._panel_activo = self._panel_cuenta
        else:
            self._panel_activo = self._panel_apariencia

        self._panel_activo.pack(fill="both", expand=True)
        self._limpiar_msgs()

    # ─────────────────────────────────────────────────────────
    # PANEL CUENTA
    # ─────────────────────────────────────────────────────────
    def _build_panel_cuenta(self) -> tk.Frame:
        c, f, tx = self._c, self._f, self._tx
        panel = tk.Frame(self._area, bg=c["bg"])

        # Canvas + scrollbar para manejar el contenido
        canvas = tk.Canvas(panel, bg=c["bg"], highlightthickness=0, bd=0)
        vsb    = ttk.Scrollbar(panel, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=c["bg"])
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))

        pad = 32

        # ── Sección: Información personal ──
        self._section_header(inner, f"👤  {tx['info']}", pad)

        # Nombre
        tk.Label(inner, text=tx["nombre_usuario"],
                 font=("Georgia", f["small"], "bold"),
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", padx=pad, pady=(12, 0))
        self._e_nombre = self._entry(inner, pad)
        self._e_nombre.insert(0, self.usuario)

        # Correo
        tk.Label(inner, text=tx["correo"],
                 font=("Georgia", f["small"], "bold"),
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", padx=pad, pady=(10, 0))
        self._e_correo = self._entry(inner, pad)

        # Teléfono
        tk.Label(inner, text=tx["telefono"],
                 font=("Georgia", f["small"], "bold"),
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", padx=pad, pady=(10, 0))
        self._e_telefono = self._entry(inner, pad)

        # Mensaje info
        self._msg_info = tk.Label(inner, text="",
                                  font=("Georgia", f["small"], "italic"),
                                  bg=c["bg"], fg=c["error"], wraplength=420)
        self._msg_info.pack(anchor="w", padx=pad, pady=(8, 0))

        # Botón guardar info
        btn_info = self._boton(inner, f"💾  {tx['guardar']}", pad,
                               command=self._guardar_info)
        btn_info.pack(fill="x", padx=pad, pady=(10, 0), ipady=7)

        # ── Separador ──
        tk.Frame(inner, height=1, bg=c["sep"]).pack(
            fill="x", padx=pad, pady=(28, 0))

        # ── Sección: Seguridad ──
        self._section_header(inner, f"🔒  {tx['seguridad']}", pad)

        tk.Label(inner, text=tx["pass_actual"],
                 font=("Georgia", f["small"], "bold"),
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", padx=pad, pady=(12, 0))
        self._e_pass_actual = self._entry(inner, pad, show="•")

        tk.Label(inner, text=tx["pass_nueva"],
                 font=("Georgia", f["small"], "bold"),
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", padx=pad, pady=(10, 0))
        self._e_pass_nueva = self._entry(inner, pad, show="•")

        tk.Label(inner, text=tx["pass_confirmar"],
                 font=("Georgia", f["small"], "bold"),
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", padx=pad, pady=(10, 0))
        self._e_pass_confirm = self._entry(inner, pad, show="•")

        self._msg_pass = tk.Label(inner, text="",
                                  font=("Georgia", f["small"], "italic"),
                                  bg=c["bg"], fg=c["error"], wraplength=420)
        self._msg_pass.pack(anchor="w", padx=pad, pady=(8, 0))

        btn_pass = self._boton(inner, f"🔑  {tx['cambiar_pass']}", pad,
                               command=self._cambiar_pass)
        btn_pass.pack(fill="x", padx=pad, pady=(10, 0), ipady=7)

        # ── Separador ──
        tk.Frame(inner, height=1, bg=c["sep"]).pack(
            fill="x", padx=pad, pady=(28, 0))

        # ── Sección: Zona de peligro ──
        self._section_header(inner, f"⚠  {tx['peligro']}", pad, danger=True)

        tk.Label(inner, text=tx["eliminar_aviso"],
                 font=("Georgia", f["small"], "italic"),
                 bg=c["bg"], fg=c["dim"], wraplength=420, justify="left"
                 ).pack(anchor="w", padx=pad, pady=(8, 0))

        tk.Label(inner, text=tx["pass_actual"],
                 font=("Georgia", f["small"], "bold"),
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", padx=pad, pady=(10, 0))
        self._e_pass_eliminar = self._entry(inner, pad, show="•")

        self._msg_eliminar = tk.Label(inner, text="",
                                      font=("Georgia", f["small"], "italic"),
                                      bg=c["bg"], fg=c["error"], wraplength=420)
        self._msg_eliminar.pack(anchor="w", padx=pad, pady=(8, 0))

        btn_del = tk.Button(
            inner, text=f"🗑  {tx['eliminar_cuenta']}",
            font=("Georgia", f["btn"], "bold"),
            bg="#2a1010", fg="#d07070",
            activebackground=c["error"], activeforeground=c["text"],
            relief="flat", bd=0, cursor="hand2",
            command=self._eliminar_cuenta)
        btn_del.pack(fill="x", padx=pad, pady=(8, 32), ipady=7)

        # Rellenar campos desde BD
        self._cargar_datos_cuenta()

        return panel

    def _cargar_datos_cuenta(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute(
                "SELECT correo, telefono FROM usuarios WHERE nombre = ?",
                (self.usuario,))
            row = cur.fetchone()
            conn.close()
            if row:
                self._e_correo.delete(0, "end")
                self._e_correo.insert(0, row[0] or "")
                self._e_telefono.delete(0, "end")
                self._e_telefono.insert(0, row[1] or "")
        except sqlite3.Error:
            pass

    # ─────────────────────────────────────────────────────────
    # PANEL APARIENCIA
    # ─────────────────────────────────────────────────────────
    def _build_panel_apariencia(self) -> tk.Frame:
        c, f, tx = self._c, self._f, self._tx
        cfg = ConfigApp.cargar()

        panel = tk.Frame(self._area, bg=c["bg"])

        canvas = tk.Canvas(panel, bg=c["bg"], highlightthickness=0, bd=0)
        vsb    = ttk.Scrollbar(panel, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=c["bg"])
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))

        pad = 32

        # ── Tema ──
        self._section_header(inner, f"🎨  {tx['tema']}", pad)
        self._var_tema = tk.StringVar(value=cfg.get("tema", "oscuro"))

        temas_frame = tk.Frame(inner, bg=c["bg"])
        temas_frame.pack(anchor="w", padx=pad, pady=(12, 0))
        for key, t in TEMAS.items():
            self._tema_card(temas_frame, key, t, self._var_tema)

        # ── Color de acento ──
        tk.Frame(inner, height=1, bg=c["sep"]).pack(
            fill="x", padx=pad, pady=(24, 0))
        self._section_header(inner, f"🔵  {tx['acento']}", pad)
        self._var_acento = tk.StringVar(value=cfg.get("acento", "dorado"))

        acentos_frame = tk.Frame(inner, bg=c["bg"])
        acentos_frame.pack(anchor="w", padx=pad, pady=(12, 0))
        for key, a in ACENTOS.items():
            self._acento_circulo(acentos_frame, key, a, self._var_acento)

        # ── Tamaño fuente ──
        tk.Frame(inner, height=1, bg=c["sep"]).pack(
            fill="x", padx=pad, pady=(24, 0))
        self._section_header(inner, f"🔤  {tx['fuente']}", pad)
        self._var_fuente = tk.StringVar(value=cfg.get("fuente", "normal"))

        fuente_frame = tk.Frame(inner, bg=c["bg"])
        fuente_frame.pack(anchor="w", padx=pad, pady=(12, 0))
        for key, fnt in FUENTES.items():
            rb = tk.Radiobutton(
                fuente_frame, text=fnt["nombre"],
                variable=self._var_fuente, value=key,
                font=("Georgia", f["cuerpo"]),
                bg=c["bg"], fg=c["text"], selectcolor=c["card"],
                activebackground=c["bg"], activeforeground=c["acento"],
                indicatoron=True, cursor="hand2")
            rb.pack(side="left", padx=(0, 24))

        # ── Idioma ──
        tk.Frame(inner, height=1, bg=c["sep"]).pack(
            fill="x", padx=pad, pady=(24, 0))
        self._section_header(inner, f"🌐  {tx['idioma']}", pad)
        self._var_idioma = tk.StringVar(value=cfg.get("idioma", "es"))

        idioma_frame = tk.Frame(inner, bg=c["bg"])
        idioma_frame.pack(anchor="w", padx=pad, pady=(12, 0))
        for key, idm in IDIOMAS.items():
            rb = tk.Radiobutton(
                idioma_frame, text=idm["nombre"],
                variable=self._var_idioma, value=key,
                font=("Georgia", f["cuerpo"]),
                bg=c["bg"], fg=c["text"], selectcolor=c["card"],
                activebackground=c["bg"], activeforeground=c["acento"],
                indicatoron=True, cursor="hand2")
            rb.pack(side="left", padx=(0, 24))

        # ── Nota y botón aplicar ──
        tk.Frame(inner, height=1, bg=c["sep"]).pack(
            fill="x", padx=pad, pady=(24, 0))

        self._msg_apariencia = tk.Label(
            inner, text="",
            font=("Georgia", f["small"], "italic"),
            bg=c["bg"], fg=c["error"], wraplength=500)
        self._msg_apariencia.pack(anchor="w", padx=pad, pady=(16, 0))

        tk.Label(inner, text=tx["reiniciar_nota"],
                 font=("Georgia", f["small"], "italic"),
                 bg=c["bg"], fg=c["dim"], wraplength=500
                 ).pack(anchor="w", padx=pad, pady=(6, 0))

        btn_ap = self._boton(inner, f"✓  {tx['aplicar']}", pad,
                             command=self._aplicar_apariencia)
        btn_ap.pack(fill="x", padx=pad, pady=(14, 32), ipady=9)

        return panel

    # ── Widgets helpers ──────────────────────────────────────
    def _section_header(self, parent, texto, pad, danger=False):
        c, f = self._c, self._f
        fg = self._c["error"] if danger else self._c["acento"]
        tk.Label(parent, text=texto,
                 font=("Georgia", f["cuerpo"] + 1, "bold"),
                 bg=c["bg"], fg=fg).pack(anchor="w", padx=pad, pady=(20, 0))

    def _entry(self, parent, pad, show=None):
        c, f = self._c, self._f
        e = tk.Entry(parent,
                     font=("Georgia", f["entry"]),
                     bg=c["card2"], fg=c["text"],
                     insertbackground=c["acento"],
                     relief="flat", highlightthickness=1,
                     highlightbackground=c["sep"],
                     highlightcolor=c["acento"],
                     show=show or "")
        e.pack(fill="x", padx=pad, ipady=6, pady=(3, 0))
        e.bind("<FocusIn>",  lambda _: e.config(highlightbackground=c["acento"]))
        e.bind("<FocusOut>", lambda _: e.config(highlightbackground=c["sep"]))
        return e

    def _boton(self, parent, texto, pad, command=None):
        c, f = self._c, self._f
        btn = tk.Button(parent, text=texto,
                        font=("Georgia", f["btn"], "bold"),
                        bg=c["acento_dim"], fg=c["text"],
                        activebackground=c["acento"], activeforeground="#000",
                        relief="flat", bd=0, cursor="hand2",
                        command=command)
        btn.bind("<Enter>", lambda _: btn.config(bg=c["acento"], fg="#000"))
        btn.bind("<Leave>", lambda _: btn.config(bg=c["acento_dim"], fg=c["text"]))
        return btn

    def _tema_card(self, parent, key, tema, var):
        c, f = self._c, self._f
        frame = tk.Frame(parent, bg=c["bg"], cursor="hand2")
        frame.pack(side="left", padx=(0, 16))

        # Previsualización
        preview = tk.Frame(frame, bg=tema["bg"], width=70, height=44,
                           highlightthickness=2,
                           highlightbackground=c["sep"])
        preview.pack()
        preview.pack_propagate(False)
        tk.Frame(preview, bg=tema["card"], height=14).pack(fill="x")
        dot_row = tk.Frame(preview, bg=tema["bg"])
        dot_row.pack(fill="x", padx=6, pady=4)
        for col in [tema.get("acento", c["acento"]), tema["dim"], tema["dim"]]:
            tk.Frame(dot_row, bg=col, width=8, height=8).pack(side="left", padx=2)

        # Radio
        rb = tk.Radiobutton(
            frame, text=tema["nombre"],
            variable=var, value=key,
            font=("Georgia", f["small"]),
            bg=c["bg"], fg=c["text"], selectcolor=c["card"],
            activebackground=c["bg"], activeforeground=c["acento"],
            cursor="hand2")
        rb.pack()

        def _highlight(*_):
            sel = var.get()
            preview.config(highlightbackground=c["acento"] if sel == key else c["sep"])

        var.trace_add("write", _highlight)
        _highlight()
        preview.bind("<Button-1>", lambda _: var.set(key))
        frame.bind("<Button-1>",   lambda _: var.set(key))

    def _acento_circulo(self, parent, key, acento, var):
        c, f = self._c, self._f
        frame = tk.Frame(parent, bg=c["bg"], cursor="hand2")
        frame.pack(side="left", padx=(0, 16))

        circulo = tk.Canvas(frame, width=32, height=32,
                            bg=c["bg"], highlightthickness=0)
        circulo.pack()
        circulo.create_oval(2, 2, 30, 30, fill=acento["color"], outline="")

        rb = tk.Radiobutton(
            frame, text=acento["nombre"],
            variable=var, value=key,
            font=("Georgia", f["small"]),
            bg=c["bg"], fg=c["text"], selectcolor=c["card"],
            activebackground=c["bg"], activeforeground=c["acento"],
            cursor="hand2")
        rb.pack()

        def _ring(*_):
            sel = var.get()
            circulo.delete("ring")
            if sel == key:
                circulo.create_oval(0, 0, 32, 32,
                                    outline=c["acento"], width=2, tags="ring")
        var.trace_add("write", _ring)
        _ring()
        circulo.bind("<Button-1>", lambda _: var.set(key))
        frame.bind("<Button-1>",   lambda _: var.set(key))

    # ── Lógica de cuenta ─────────────────────────────────────
    def _limpiar_msgs(self):
        for attr in ("_msg_info", "_msg_pass", "_msg_eliminar", "_msg_apariencia"):
            lbl = getattr(self, attr, None)
            if lbl:
                try: lbl.config(text="")
                except: pass

    def _verificar_pass_actual(self, campo_entry) -> bool:
        """Verifica la contraseña actual del usuario. Devuelve True si es correcta."""
        pw = campo_entry.get()
        if not pw:
            return None  # vacío
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT password FROM usuarios WHERE nombre = ?",
                        (self.usuario,))
            row = cur.fetchone()
            conn.close()
            return row and row[0] == _hash(pw)
        except sqlite3.Error:
            return False

    def _guardar_info(self):
        self._msg_info.config(text="")
        tx = self._tx

        nuevo_nombre = self._e_nombre.get().strip()
        nuevo_correo = self._e_correo.get().strip()
        nuevo_tel    = self._e_telefono.get().strip()

        if not nuevo_nombre:
            self._msg_info.config(text=tx["error_nombre_vacio"],
                                  fg=self._c["error"])
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()

            # Comprobar si el nombre ya existe (y no es el propio)
            if nuevo_nombre != self.usuario:
                cur.execute("SELECT id_usuario FROM usuarios WHERE nombre = ?",
                            (nuevo_nombre,))
                if cur.fetchone():
                    self._msg_info.config(text=tx["error_nombre_existe"],
                                          fg=self._c["error"])
                    conn.close()
                    return

            cur.execute("""
                UPDATE usuarios
                SET nombre = ?, correo = ?, telefono = ?
                WHERE nombre = ?
            """, (nuevo_nombre, nuevo_correo or None,
                  nuevo_tel or None, self.usuario))
            conn.commit()
            conn.close()

            self._msg_info.config(text=tx["ok_info"], fg=self._c["success"])

            # Si cambió el nombre, recargar menú con nuevo nombre
            if nuevo_nombre != self.usuario:
                self.frame.after(900, lambda: self.on_apply and
                                 self.on_apply(accion="cambiar_usuario",
                                               nuevo_usuario=nuevo_nombre))

        except sqlite3.Error as e:
            self._msg_info.config(text=f"Error BD: {e}", fg=self._c["error"])

    def _cambiar_pass(self):
        self._msg_pass.config(text="")
        tx = self._tx
        c  = self._c

        ok = self._verificar_pass_actual(self._e_pass_actual)
        if ok is None:
            self._msg_pass.config(
                text=tx["pass_requerida"], fg=c["error"])
            return
        if not ok:
            self._msg_pass.config(text=tx["error_pass"], fg=c["error"])
            return

        nueva    = self._e_pass_nueva.get()
        confirma = self._e_pass_confirm.get()

        if nueva != confirma:
            self._msg_pass.config(
                text="Las contraseñas no coinciden.", fg=c["error"])
            return
        if not _validar_pass(nueva):
            self._msg_pass.config(
                text="La nueva contraseña no cumple los requisitos de seguridad.\n"
                     "(Mín. 8 caracteres, mayúscula, minúscula, número y símbolo)",
                fg=c["error"])
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute(
                "UPDATE usuarios SET password = ? WHERE nombre = ?",
                (_hash(nueva), self.usuario))
            conn.commit()
            conn.close()
            self._msg_pass.config(text=tx["ok_pass"], fg=c["success"])
            self._e_pass_actual.delete(0, "end")
            self._e_pass_nueva.delete(0, "end")
            self._e_pass_confirm.delete(0, "end")
        except sqlite3.Error as e:
            self._msg_pass.config(text=f"Error BD: {e}", fg=c["error"])

    def _eliminar_cuenta(self):
        self._msg_eliminar.config(text="")
        tx, c = self._tx, self._c

        ok = self._verificar_pass_actual(self._e_pass_eliminar)
        if ok is None:
            self._msg_eliminar.config(text=tx["pass_requerida"], fg=c["error"])
            return
        if not ok:
            self._msg_eliminar.config(text=tx["error_pass"], fg=c["error"])
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            # Comprobar préstamos activos
            cur.execute("""
                SELECT COUNT(*) FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                WHERE u.nombre = ? AND p.devuelto = 0
            """, (self.usuario,))
            if cur.fetchone()[0] > 0:
                self._msg_eliminar.config(
                    text="No puedes eliminar tu cuenta mientras tengas\n"
                         "préstamos activos. Devuelve los libros primero.",
                    fg=c["error"])
                conn.close()
                return
            cur.execute("DELETE FROM usuarios WHERE nombre = ?", (self.usuario,))
            conn.commit()
            conn.close()
            self._msg_eliminar.config(text=tx["ok_eliminado"], fg=c["success"])
            self.frame.after(1200, lambda: self.on_apply and
                             self.on_apply(accion="logout"))
        except sqlite3.Error as e:
            self._msg_eliminar.config(text=f"Error BD: {e}", fg=c["error"])

    # ── Lógica de apariencia ─────────────────────────────────
    def _aplicar_apariencia(self):
        tx, c = self._tx, self._c
        nuevos = {
            "tema":   self._var_tema.get(),
            "acento": self._var_acento.get(),
            "fuente": self._var_fuente.get(),
            "idioma": self._var_idioma.get(),
        }
        try:
            ConfigApp.guardar(nuevos)
            ConfigApp.invalidar()
            self._msg_apariencia.config(text=tx["ok_apariencia"], fg=c["success"])
            self.frame.after(800, lambda: self.on_apply and
                             self.on_apply(accion="recargar", tab="apariencia"))
        except IOError as e:
            self._msg_apariencia.config(text=str(e), fg=c["error"])

    # ── Ciclo de vida ─────────────────────────────────────────
    def abrir_tab(self, key: str):
        """Abre una pestaña concreta ('cuenta' o 'apariencia')."""
        if hasattr(self, "_tab_btns") and key in self._tab_btns:
            self._switch_tab(key, self._tab_btns[key])

    def mostrar(self):
        self.frame.pack(fill="both", expand=True)

    def ocultar(self):
        self.frame.pack_forget()