import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageFont
import sqlite3
import os
import re
import hashlib
import threading
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()  # Carga las variables de .env

from biblioteca_main_LuisVillegas import MenuPrincipal
from secciones.biblioteca_ajustes import ConfigApp

# ── Traducciones login ────────────────────────────────
_LOGIN_TX = {
    "es": {
        "titulo":       "El Archivo de los Mundos",
        "subtitulo":    "Sistema de préstamos · Acceso privado",
        "tab_login":    "INICIAR SESIÓN",
        "tab_reg":      "REGISTRARSE",
        "campo_user":   "Usuario",
        "campo_pass":   "Contraseña",
        "campo_conf":   "Confirmar contraseña",
        "campo_correo": "Correo electrónico",
        "campo_tel":    "Teléfono (opcional)",
        "btn_login":    "Iniciar sesión",
        "btn_reg":      "Registrarse",
        "olvide":       "¿Olvidaste tu contraseña?",
        "footer":       "El Archivo de los Mundos · Biblioteca privada",
        "crear_cuenta": "Crear cuenta",
        "pass_incorr":  "Contraseña incorrecta.",
        "req_len":      "Mínimo 8 caracteres",
        "req_upper":    "Una letra mayúscula",
        "req_lower":    "Una letra minúscula",
        "req_num":      "Un número",
        "req_special":  "Un carácter especial (!@#$...)",
        "f1": "Muy débil", "f2": "Débil",
        "f3": "Moderada",  "f4": "Fuerte", "f5": "Inquebrantable",
    },
    "en": {
        "titulo":       "El Archivo de los Mundos",
        "subtitulo":    "Loan system · Private access",
        "tab_login":    "LOG IN",
        "tab_reg":      "REGISTER",
        "campo_user":   "Username",
        "campo_pass":   "Password",
        "campo_conf":   "Confirm password",
        "campo_correo": "Email address",
        "campo_tel":    "Phone (optional)",
        "btn_login":    "Log in",
        "btn_reg":      "Register",
        "olvide":       "Forgot your password?",
        "footer":       "El Archivo de los Mundos · Private library",
        "crear_cuenta": "Create account",
        "pass_incorr":  "Wrong password.",
        "req_len":      "At least 8 characters",
        "req_upper":    "One uppercase letter",
        "req_lower":    "One lowercase letter",
        "req_num":      "One number",
        "req_special":  "One special character (!@#$...)",
        "f1": "Very weak", "f2": "Weak",
        "f3": "Moderate",  "f4": "Strong", "f5": "Unbreakable",
    },
}

def _tx(clave: str) -> str:
    """Devuelve el texto de login en el idioma guardado."""
    idioma = ConfigApp.get("idioma") or "es"
    return _LOGIN_TX.get(idioma, _LOGIN_TX["es"]).get(clave, clave)


# -------------------
# Rutas
# -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bbdd", "El_Archivo_de_los_Mundos.bbdd")
SQL_CREATE_PATH = os.path.join(BASE_DIR, "bbdd", "createbbdd.sql")
IMG_FOLDER = os.path.join(BASE_DIR, "img")

ICON_PATH        = os.path.join(IMG_FOLDER, "icono.ico")
BG_LOGIN         = os.path.join(IMG_FOLDER, "login.jpg")
BG_MENU          = os.path.join(IMG_FOLDER, "fondo_menu.jpg")
USER_ICON_PATH   = os.path.join(IMG_FOLDER, "user.png")
PASS_ICON_PATH   = os.path.join(IMG_FOLDER, "contraseña.png")
TOGGLE_PASS_INV  = os.path.join(IMG_FOLDER, "ver_contraseña_inactivo.png")
TOGGLE_PASS_ACT  = os.path.join(IMG_FOLDER, "ver_contraseña_activo.png")

# Colores y fuentes (constantes de diseño)
COLOR_BG        = "#0e0d12"
COLOR_CARD      = "#13121a"
COLOR_GOLD      = "#c9a84c"
COLOR_GOLD_DIM  = "#7a5f28"
COLOR_TEXT      = "#e8dfc8"
COLOR_DIM       = "#8a7f6a"
COLOR_ERROR     = "#c45a3a"
COLOR_SUCCESS   = "#4a8c5a"
COLOR_WARNING   = "#b8a230"
COLOR_ENTRY_BG  = "#1a1820"
COLOR_ENTRY_FG  = "#e8dfc8"
FONT_TITLE  = ("Georgia", 20, "bold")
FONT_LABEL  = ("Georgia", 10)
FONT_ENTRY  = ("Georgia", 13)
FONT_BTN    = ("Georgia", 12, "bold")
FONT_SMALL  = ("Georgia", 9)
FONT_MSG    = ("Georgia", 10, "italic")

# -------------------
# Hash de contraseña (seguridad básica)
# -------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# -------------------
# Crear bbdd si no existe
# -------------------
os.makedirs(os.path.join(BASE_DIR, "bbdd"), exist_ok=True)
def _tablas_existen() -> bool:
    """Comprueba que la tabla usuarios exista en la BD."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        existe = cur.fetchone() is not None
        conn.close()
        return existe
    except Exception:
        return False

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

if not _tablas_existen():
    if os.path.exists(SQL_CREATE_PATH):
        print("Creando BBDD...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        with open(SQL_CREATE_PATH, "r", encoding="utf-8") as f:
            cursor.executescript(f.read())
        conn.commit()
        conn.close()
        print("BBDD creada.")
    else:
        # Crear estructura mínima si no hay .sql
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                correo TEXT UNIQUE,
                telefono TEXT,
                password TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'normal'
            )
        """)
        conn.commit()
        conn.close()

# -------------------
# Validación contraseña
# -------------------
def validar_contraseña(password: str) -> dict:
    return {
        "longitud":  len(password) >= 8,
        "mayuscula": bool(re.search(r"[A-Z]", password)),
        "minuscula": bool(re.search(r"[a-z]", password)),
        "numero":    bool(re.search(r"[0-9]", password)),
        "especial":  bool(re.search(r'[!@#$%^&*(),.?\":{}|<>]', password)),
    }

def contraseña_es_valida(password: str) -> bool:
    return all(validar_contraseña(password).values())

def fuerza_contraseña(password: str) -> tuple:
    checks = validar_contraseña(password)
    score = sum(checks.values())
    niveles = {
        0: ("",           COLOR_DIM),
        1: (_tx("f1"),   COLOR_ERROR),
        2: (_tx("f2"),   COLOR_ERROR),
        3: (_tx("f3"),   COLOR_WARNING),
        4: (_tx("f4"),   COLOR_GOLD),
        5: (_tx("f5"),   COLOR_SUCCESS),
    }
    return niveles[score]

# -------------------
# Envío de correo de verificación
# -------------------
def generar_codigo() -> str:
    return str(random.randint(100000, 999999))

def verificar_correo_smtp(correo: str) -> tuple:
    """
    Comprueba si el correo probablemente existe haciendo RCPT TO
    sin llegar a enviar nada. Devuelve (True, "") o (False, motivo).
    Funciona con la mayoría de servidores; algunos bloquean la comprobación.
    """
    import dns.resolver
    try:
        dominio = correo.split("@")[1]
        registros_mx = dns.resolver.resolve(dominio, "MX")
        mx_host = sorted(registros_mx, key=lambda r: r.preference)[0].exchange.to_text().rstrip(".")
    except Exception:
        return False, f"No se encontró el dominio del correo '{correo.split('@')[1] if '@' in correo else correo}'."

    remitente_probe = os.getenv("MAIL_USER", "probe@example.com")
    try:
        with smtplib.SMTP(mx_host, 25, timeout=6) as srv:
            srv.ehlo("verificacion.local")
            srv.mail(remitente_probe)
            code, _ = srv.rcpt(correo)
            if code == 250:
                return True, ""
            else:
                return False, f"El correo «{correo}» no existe o no acepta mensajes."
    except smtplib.SMTPRecipientsRefused:
        return False, f"El correo «{correo}» no existe o no acepta mensajes."
    except Exception:
        # Si el servidor bloquea la comprobación, dejamos pasar (falso negativo preferible)
        return True, ""


def enviar_codigo_verificacion(destinatario: str, codigo: str) -> tuple:
    """
    Envía un código de 6 dígitos al correo indicado via Gmail.
    Devuelve (True, "") si ok, (False, mensaje_error) si falla.
    """
    remitente = os.getenv("MAIL_USER", "")
    clave     = os.getenv("MAIL_PASS", "")
    nombre    = os.getenv("MAIL_NAME", "El Archivo de los Mundos")

    if not remitente or not clave:
        return False, ("No se encontraron las credenciales de correo.\n"
                       "Revisa el fichero .env (MAIL_USER y MAIL_PASS).")
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Código de verificación — El Archivo de los Mundos"
        msg["From"]    = f"{nombre} <{remitente}>"
        msg["To"]      = destinatario

        cuerpo_texto = (
            f"Tu código de verificación es: {codigo}\n\n"
            "Introdúcelo en la aplicación para completar tu registro.\n"
            "Caduca en 10 minutos."
        )
        cuerpo_html = f"""
        <html><body style="font-family:Georgia,serif;background:#0e0d12;color:#e8dfc8;padding:32px;">
          <div style="max-width:420px;margin:auto;background:#13121a;border:1px solid #7a5f28;
                      border-radius:4px;padding:36px;">
            <h2 style="color:#c9a84c;letter-spacing:2px;">El Archivo de los Mundos</h2>
            <p style="color:#8a7f6a;font-style:italic;">Biblioteca · Verificación de cuenta</p>
            <hr style="border-color:#7a5f28;margin:20px 0">
            <p>Tu código de verificación es:</p>
            <div style="font-size:36px;font-weight:bold;color:#c9a84c;
                        letter-spacing:12px;text-align:center;padding:16px 0;">
              {codigo}
            </div>
            <p style="color:#8a7f6a;font-size:13px;">Caduca en 10 minutos.</p>
          </div>
        </body></html>
        """
        msg.attach(MIMEText(cuerpo_texto, "plain"))
        msg.attach(MIMEText(cuerpo_html,  "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(remitente, clave)
            servidor.sendmail(remitente, destinatario, msg.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, ("Error de autenticación con Gmail.\n"
                       "Comprueba que usas una contraseña de aplicación válida.")
    except smtplib.SMTPException as e:
        return False, f"Error al enviar el correo: {e}"
    except Exception as e:
        return False, f"Error inesperado: {e}"


# -------------------
# Cargar imagen con fallback
# -------------------
def load_img(path, size):
    try:
        img = Image.open(path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# -------------------
# Crear imagen de fondo degradado (fallback si no hay jpg)
# -------------------
def crear_fondo(width, height, dark=True):
    img = Image.new("RGB", (width, height), "#060608" if dark else "#0a0912")
    draw = ImageDraw.Draw(img)
    # Viñeta
    for i in range(min(width, height) // 2):
        alpha = int(30 * (1 - i / (min(width, height) / 2)))
        draw.rectangle([i, i, width - i, height - i], outline=f"#{alpha:02x}{alpha:02x}{alpha:02x}")
    return ImageTk.PhotoImage(img)

# -------------------
# Tooltip sencillo
# -------------------
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tip, text=self.text, bg="#1a1820", fg=COLOR_DIM,
                       font=FONT_SMALL, relief="flat", bd=1,
                       padx=8, pady=4, wraplength=240, justify="left")
        lbl.pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ===================================================
# DIÁLOGO CUSTOM (reemplaza messagebox)
# ===================================================
class Dialogo(tk.Toplevel):
    """
    Diálogo modal estilizado.
    tipo: "yesno" → devuelve True/False via self.resultado
          "info"  → solo botón Aceptar
          "error" → solo botón Aceptar (en rojo)
    """
    def __init__(self, parent, titulo, mensaje, tipo="yesno",
                 btn_si="Sí", btn_no="Cancelar"):
        super().__init__(parent)
        self.resultado = False
        self.overrideredirect(True)          # sin bordes del SO
        self.configure(bg=COLOR_CARD)
        self.resizable(False, False)
        self.grab_set()                      # modal

        borde = tk.Frame(self, bg=COLOR_GOLD_DIM, bd=0)
        borde.pack(fill="both", expand=True, padx=1, pady=1)

        inner = tk.Frame(borde, bg=COLOR_CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Icono + título
        icono = {"yesno": "?", "info": "i", "error": "✕"}.get(tipo, "i")
        ic_color = {"yesno": COLOR_GOLD, "info": COLOR_GOLD, "error": COLOR_ERROR}.get(tipo, COLOR_GOLD)

        top = tk.Frame(inner, bg=COLOR_CARD)
        top.pack(fill="x", padx=24, pady=(22, 0))
        tk.Label(top, text=icono, font=("Georgia", 20, "bold"),
                 bg=COLOR_CARD, fg=ic_color, width=2).pack(side="left")
        tk.Label(top, text=titulo, font=("Georgia", 13, "bold"),
                 bg=COLOR_CARD, fg=COLOR_GOLD).pack(side="left", padx=(10, 0))

        # Separador
        tk.Frame(inner, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=24, pady=(12, 0))

        # Mensaje
        tk.Label(inner, text=mensaje, font=("Georgia", 11),
                 bg=COLOR_CARD, fg=COLOR_TEXT,
                 wraplength=320, justify="left").pack(padx=28, pady=(14, 6), anchor="w")

        # Botones
        btn_frame = tk.Frame(inner, bg=COLOR_CARD)
        btn_frame.pack(fill="x", padx=24, pady=(10, 22))

        if tipo in ("info", "error"):
            b = tk.Button(btn_frame, text="Aceptar",
                          font=("Georgia", 10, "bold"),
                          bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
                          activebackground=COLOR_GOLD, activeforeground="#000",
                          relief="flat", bd=0, cursor="hand2",
                          command=self._aceptar)
            b.pack(side="right", ipadx=18, ipady=6)
            b.bind("<Enter>", lambda _: b.config(bg=COLOR_GOLD, fg="#000"))
            b.bind("<Leave>", lambda _: b.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))
        else:
            b_no = tk.Button(btn_frame, text=btn_no,
                             font=("Georgia", 10),
                             bg=COLOR_CARD, fg=COLOR_DIM,
                             activebackground="#1e1c25", activeforeground=COLOR_TEXT,
                             relief="flat", bd=1, cursor="hand2",
                             highlightbackground=COLOR_GOLD_DIM,
                             command=self._cancelar)
            b_no.pack(side="right", ipadx=14, ipady=6, padx=(8, 0))

            b_si = tk.Button(btn_frame, text=btn_si,
                             font=("Georgia", 10, "bold"),
                             bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
                             activebackground=COLOR_GOLD, activeforeground="#000",
                             relief="flat", bd=0, cursor="hand2",
                             command=self._aceptar)
            b_si.pack(side="right", ipadx=18, ipady=6)
            b_si.bind("<Enter>", lambda _: b_si.config(bg=COLOR_GOLD, fg="#000"))
            b_si.bind("<Leave>", lambda _: b_si.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))

        # Centrar sobre la ventana padre
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        dw = self.winfo_width()
        dh = self.winfo_height()
        self.geometry(f"+{px + pw//2 - dw//2}+{py + ph//2 - dh//2}")

        self.bind("<Return>", lambda _: self._aceptar())
        self.bind("<Escape>", lambda _: self._cancelar())
        self.wait_window()

    def _aceptar(self):
        self.resultado = True
        self.destroy()

    def _cancelar(self):
        self.resultado = False
        self.destroy()


def dialogo_yesno(parent, titulo, mensaje, btn_si="Sí", btn_no="Cancelar"):
    return Dialogo(parent, titulo, mensaje, tipo="yesno",
                   btn_si=btn_si, btn_no=btn_no).resultado

def dialogo_info(parent, titulo, mensaje):
    Dialogo(parent, titulo, mensaje, tipo="info")

def dialogo_error(parent, titulo, mensaje):
    Dialogo(parent, titulo, mensaje, tipo="error")

# ===================================================
# DIÁLOGO DE VERIFICACIÓN POR CORREO
# ===================================================
class DialogoVerificacion(tk.Toplevel):
    """
    Muestra un campo para introducir el código de 6 dígitos.
    self.verificado = True si el código coincide.
    """
    def __init__(self, parent, correo: str, codigo: str):
        super().__init__(parent)
        self.codigo_correcto = codigo
        self.verificado = False
        self.intentos   = 0
        self.MAX_INTENTOS = 3

        self.overrideredirect(True)
        self.configure(bg=COLOR_CARD)
        self.grab_set()

        borde = tk.Frame(self, bg=COLOR_GOLD_DIM)
        borde.pack(fill="both", expand=True, padx=1, pady=1)
        inner = tk.Frame(borde, bg=COLOR_CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Cabecera
        tk.Label(inner, text="Verificación de correo",
                 font=("Georgia", 13, "bold"), bg=COLOR_CARD, fg=COLOR_GOLD
                 ).pack(pady=(22, 0), padx=28, anchor="w")
        tk.Frame(inner, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=24, pady=(10, 0))

        # Texto informativo
        correo_corto = correo if len(correo) <= 32 else correo[:29] + "..."
        tk.Label(inner,
                 text=f"Se ha enviado un código de 6 dígitos a:\n{correo_corto}",
                 font=("Georgia", 10), bg=COLOR_CARD, fg=COLOR_TEXT,
                 justify="left", wraplength=320
                 ).pack(padx=28, pady=(14, 4), anchor="w")
        tk.Label(inner, text="Introduce el código recibido:",
                 font=("Georgia", 9, "italic"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(padx=28, anchor="w")

        # Entry código
        self.codigo_var = tk.StringVar()
        self.codigo_var.trace_add("write", self._limitar_digitos)
        self.entry = tk.Entry(inner, textvariable=self.codigo_var,
                              font=("Georgia", 22, "bold"),
                              bg=COLOR_ENTRY_BG, fg=COLOR_GOLD,
                              insertbackground=COLOR_GOLD,
                              justify="center", width=10,
                              relief="flat", bd=0, highlightthickness=1,
                              highlightbackground=COLOR_GOLD_DIM,
                              highlightcolor=COLOR_GOLD)
        self.entry.pack(padx=28, pady=(8, 4), ipady=8)
        self.entry.focus_set()

        # Mensaje de error
        self.msg_lbl = tk.Label(inner, text="", font=("Georgia", 9, "italic"),
                                bg=COLOR_CARD, fg=COLOR_ERROR, wraplength=320)
        self.msg_lbl.pack(padx=28, pady=(0, 4), anchor="w")

        # Botones
        btn_frame = tk.Frame(inner, bg=COLOR_CARD)
        btn_frame.pack(fill="x", padx=24, pady=(6, 22))

        b_cancelar = tk.Button(btn_frame, text="Cancelar",
                               font=("Georgia", 10), bg=COLOR_CARD, fg=COLOR_DIM,
                               relief="flat", bd=1, cursor="hand2",
                               highlightbackground=COLOR_GOLD_DIM,
                               command=self._cancelar)
        b_cancelar.pack(side="right", ipadx=12, ipady=6, padx=(8, 0))

        b_verificar = tk.Button(btn_frame, text="Verificar",
                                font=("Georgia", 10, "bold"),
                                bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
                                activebackground=COLOR_GOLD, activeforeground="#000",
                                relief="flat", bd=0, cursor="hand2",
                                command=self._verificar)
        b_verificar.pack(side="right", ipadx=18, ipady=6)
        b_verificar.bind("<Enter>", lambda _: b_verificar.config(bg=COLOR_GOLD, fg="#000"))
        b_verificar.bind("<Leave>", lambda _: b_verificar.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))

        # Centrar
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        dw, dh = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + pw//2 - dw//2}+{py + ph//2 - dh//2}")

        self.entry.bind("<Return>", lambda _: self._verificar())
        self.bind("<Escape>", lambda _: self._cancelar())
        self.wait_window()

    def _limitar_digitos(self, *_):
        if getattr(self, "_limitar_activo", False):
            return
        self._limitar_activo = True
        val = self.codigo_var.get()
        val = re.sub(r"[^0-9]", "", val)[:6]
        self.codigo_var.set(val)
        self._limitar_activo = False

    def _verificar(self):
        introducido = self.codigo_var.get().strip()
        if len(introducido) < 6:
            self.msg_lbl.config(text="El código tiene 6 dígitos.")
            return
        if introducido == self.codigo_correcto:
            self.verificado = True
            self.destroy()
        else:
            self.intentos += 1
            restantes = self.MAX_INTENTOS - self.intentos
            if restantes <= 0:
                self.msg_lbl.config(text="Demasiados intentos fallidos. Regístrate de nuevo.")
                self.after(1500, self._cancelar)
            else:
                self.msg_lbl.config(
                    text=f"Código incorrecto. Te quedan {restantes} intento(s)."
                )
            self.entry.config(highlightbackground=COLOR_ERROR)
            self.codigo_var.set("")

    def _cancelar(self):
        self.verificado = False
        self.destroy()


# ===================================================
# APLICACIÓN PRINCIPAL
# ===================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # --- Ventana ---
        self.title("El Archivo de los Mundos")
        self._aplicar_tema_login()
        self.resizable(False, False)

        # Icono
        try:
            self.iconbitmap(ICON_PATH)
        except Exception:
            pass

        # Pantalla completa
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.state("zoomed")

        self.sw = sw
        self.sh = sh

        # Estado
        self.modo = tk.StringVar(value="login")   # login | register
        self.show_pass = False
        self.usuario_activo = None

        # --- Fondo ---
        self._bg_label = tk.Label(self, bd=0)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._set_fondo(menu=False)

        # --- Construir UI ---
        self._build_login_card()

        # Bind Enter
        self.bind("<Return>", lambda _: self._on_submit())
        self.bind("<Escape>", lambda _: self._cerrar_dialogo_si_existe())

    # ── Tema login ─────────────────────────────────────
    def _aplicar_tema_login(self):
        """Lee el tema guardado y sobreescribe los colores globales del login."""
        c = ConfigApp.colores()
        self.configure(bg=c["bg"])
        global COLOR_BG, COLOR_CARD, COLOR_GOLD, COLOR_GOLD_DIM
        global COLOR_TEXT, COLOR_DIM, COLOR_ENTRY_BG, COLOR_ENTRY_FG
        COLOR_BG       = c["bg"]
        COLOR_CARD     = c["card"]
        COLOR_GOLD     = c["acento"]
        COLOR_GOLD_DIM = c["acento_dim"]
        COLOR_TEXT     = c["text"]
        COLOR_DIM      = c["dim"]
        COLOR_ENTRY_BG = c.get("card2", c["card"])
        COLOR_ENTRY_FG = c["text"]

    # ── Fondo ──────────────────────────────────────────
    def _set_fondo(self, menu=False):
        path = BG_MENU if menu else BG_LOGIN
        try:
            img = Image.open(path).convert("RGB")
            img = img.resize((self.sw, self.sh), Image.Resampling.LANCZOS)
            # Oscurecer ligeramente
            overlay = Image.new("RGB", (self.sw, self.sh), "#000000")
            img = Image.blend(img, overlay, alpha=0.35)
            photo = ImageTk.PhotoImage(img)
        except Exception:
            photo = crear_fondo(self.sw, self.sh, dark=not menu)
        self._bg_label.config(image=photo)
        self._bg_label.image = photo

    # ── Card de login ───────────────────────────────────
    def _build_login_card(self):
        card_w = 420
        pad = 36

        # Frame principal — sin altura fija, se autoajusta al contenido
        self.card = tk.Frame(self, bg=COLOR_CARD, bd=0, highlightthickness=1,
                             highlightbackground=COLOR_GOLD_DIM, width=card_w,
                             padx=0, pady=4)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        self.card.pack_propagate(True)

        # ── Título ──
        tk.Label(self.card, text="El Archivo de los Mundos",
                 font=FONT_TITLE, bg=COLOR_CARD, fg=COLOR_GOLD).pack(pady=(pad, 2), padx=pad)
        tk.Label(self.card, text=_tx("subtitulo"),
                 font=("Georgia", 9, "italic"), bg=COLOR_CARD, fg=COLOR_DIM).pack(padx=pad)

        # Separador
        sep = tk.Frame(self.card, height=1, bg=COLOR_GOLD_DIM)
        sep.pack(fill="x", padx=pad, pady=(14, 18))

        # ── Tabs ──
        tabs_frame = tk.Frame(self.card, bg=COLOR_CARD)
        tabs_frame.pack(fill="x", padx=pad, pady=(0, 18))

        self.tab_login_btn = tk.Button(
            tabs_frame, text=_tx("tab_login"),
            font=("Georgia", 10, "bold"), bd=0, relief="flat", cursor="hand2",
            command=lambda: self._switch_modo("login"))
        self.tab_reg_btn = tk.Button(
            tabs_frame, text=_tx("tab_reg"),
            font=("Georgia", 10, "bold"), bd=0, relief="flat", cursor="hand2",
            command=lambda: self._switch_modo("register"))
        self.tab_login_btn.pack(side="left", expand=True, fill="x", ipady=6)
        self.tab_reg_btn.pack(side="left", expand=True, fill="x", ipady=6)
        self._actualizar_tabs()

        # ── Mensaje de estado ──
        self.msg_label = tk.Label(self.card, text="", font=FONT_MSG,
                                  bg=COLOR_CARD, fg=COLOR_ERROR,
                                  wraplength=card_w - pad * 2, justify="left")
        self.msg_label.pack(fill="x", padx=pad, pady=(0, 6))

        # ── Campo usuario ──
        self._campo(self.card, _tx("campo_user"), pad)
        user_frame = tk.Frame(self.card, bg=COLOR_CARD)
        user_frame.pack(fill="x", padx=pad, pady=(4, 12))

        u_icon = load_img(USER_ICON_PATH, (22, 22))
        if u_icon:
            lbl = tk.Label(user_frame, image=u_icon, bg=COLOR_CARD)
            lbl.image = u_icon
            lbl.pack(side="left", padx=(0, 6))

        self.user_entry = tk.Entry(user_frame, font=FONT_ENTRY,
                                   bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG,
                                   insertbackground=COLOR_GOLD,
                                   relief="flat", bd=0, highlightthickness=1,
                                   highlightbackground=COLOR_GOLD_DIM,
                                   highlightcolor=COLOR_GOLD)
        self.user_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 2))
        self.user_entry.bind("<FocusIn>",  lambda _: self._focus_entry(self.user_entry, True))
        self.user_entry.bind("<FocusOut>", lambda _: self._focus_entry(self.user_entry, False))
        self.user_entry.bind("<KeyRelease>", lambda _: self._limpiar_msg())
        # Espaciador invisible para igualar la anchura con el campo contraseña (que tiene el botón ojo)
        tk.Frame(user_frame, width=28, bg=COLOR_CARD).pack(side="left")

        # ── Campo contraseña ──
        self._campo(self.card, _tx("campo_pass"), pad)
        pass_frame = tk.Frame(self.card, bg=COLOR_CARD)
        pass_frame.pack(fill="x", padx=pad, pady=(4, 6))

        p_icon = load_img(PASS_ICON_PATH, (22, 22))
        if p_icon:
            lbl2 = tk.Label(pass_frame, image=p_icon, bg=COLOR_CARD)
            lbl2.image = p_icon
            lbl2.pack(side="left", padx=(0, 6))

        self.pass_entry = tk.Entry(pass_frame, font=FONT_ENTRY, show="●",
                                   bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG,
                                   insertbackground=COLOR_GOLD,
                                   relief="flat", bd=0, highlightthickness=1,
                                   highlightbackground=COLOR_GOLD_DIM,
                                   highlightcolor=COLOR_GOLD)
        self.pass_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.pass_entry.bind("<FocusIn>",  lambda _: self._focus_entry(self.pass_entry, True))
        self.pass_entry.bind("<FocusOut>", lambda _: self._focus_entry(self.pass_entry, False))
        self.pass_entry.bind("<KeyRelease>", self._on_pass_keyrelease)

        # Botón mostrar/ocultar
        self._show_img_inv = load_img(TOGGLE_PASS_INV, (22, 22))
        self._show_img_act = load_img(TOGGLE_PASS_ACT, (22, 22))
        toggle_kwargs = dict(bg=COLOR_CARD, bd=0, relief="flat",
                             cursor="hand2", command=self._toggle_pass)
        if self._show_img_inv:
            self.toggle_btn = tk.Button(pass_frame, image=self._show_img_inv, **toggle_kwargs)
        else:
            self.toggle_btn = tk.Button(pass_frame, text="👁", fg=COLOR_DIM,
                                        font=("Arial", 12), **toggle_kwargs)
        self.toggle_btn.pack(side="left", padx=(6, 0))
        Tooltip(self.toggle_btn, "Mostrar / ocultar contraseña")

        # ── Indicador de fuerza ──
        self.strength_frame = tk.Frame(self.card, bg=COLOR_CARD)
        # Se empaqueta aquí para fijar el orden; luego se oculta
        self.strength_frame.pack(fill="x", padx=pad, pady=(2, 4))

        self.strength_bar_bg = tk.Frame(self.strength_frame, bg="#1e1c25", height=6)
        self.strength_bar_bg.pack(fill="x")
        self.strength_bar = tk.Frame(self.strength_bar_bg, bg=COLOR_ERROR, height=6)
        self.strength_bar.place(x=0, y=0, relheight=1, relwidth=0)

        self.strength_lbl = tk.Label(self.strength_frame, text="",
                                     font=("Georgia", 9, "italic"),
                                     bg=COLOR_CARD, fg=COLOR_DIM)
        self.strength_lbl.pack(anchor="w", pady=(3, 0))
        self.strength_frame.pack_forget()

        # ── Requisitos contraseña ──
        self.req_frame = tk.Frame(self.card, bg=COLOR_CARD)
        req_texts = [
            ("req_len",     _tx("req_len")),
            ("req_upper",   _tx("req_upper")),
            ("req_lower",   _tx("req_lower")),
            ("req_num",     _tx("req_num")),
            ("req_special", _tx("req_special")),
        ]
        self.req_labels = {}
        for key, txt in req_texts:
            lbl = tk.Label(self.req_frame, text=f"  ◦  {txt}",
                           font=("Georgia", 9), bg=COLOR_CARD, fg=COLOR_DIM, anchor="w")
            lbl.pack(fill="x", padx=8, pady=1)
            self.req_labels[key] = lbl
        self.req_frame.pack(fill="x", padx=pad, pady=(0, 6))
        self.req_frame.pack_forget()

        # ── Campo confirmar contraseña (solo registro) ──
        self.confirm_outer = tk.Frame(self.card, bg=COLOR_CARD)
        self._campo(self.confirm_outer, _tx("campo_conf"), 0)
        confirm_frame = tk.Frame(self.confirm_outer, bg=COLOR_CARD)
        confirm_frame.pack(fill="x", pady=(4, 0))
        self.confirm_entry = tk.Entry(confirm_frame, font=FONT_ENTRY, show="●",
                                      bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG,
                                      insertbackground=COLOR_GOLD,
                                      relief="flat", bd=0, highlightthickness=1,
                                      highlightbackground=COLOR_GOLD_DIM,
                                      highlightcolor=COLOR_GOLD)
        self.confirm_entry.pack(fill="x", ipady=6)
        self.confirm_entry.bind("<FocusIn>",  lambda _: self._focus_entry(self.confirm_entry, True))
        self.confirm_entry.bind("<FocusOut>", lambda _: self._focus_entry(self.confirm_entry, False))
        self.confirm_entry.bind("<KeyRelease>", lambda _: self._limpiar_msg())
        self.confirm_outer.pack(fill="x", padx=pad, pady=(8, 0))
        self.confirm_outer.pack_forget()

        # ── Campos extra solo en registro: correo y teléfono ──
        self.extra_outer = tk.Frame(self.card, bg=COLOR_CARD)

        tk.Label(self.extra_outer, text=_tx("campo_correo").upper() + "  *",
                 font=("Georgia", 8, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w")
        self.correo_entry = tk.Entry(self.extra_outer, font=FONT_ENTRY,
                                     bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG,
                                     insertbackground=COLOR_GOLD,
                                     relief="flat", bd=0, highlightthickness=1,
                                     highlightbackground=COLOR_GOLD_DIM,
                                     highlightcolor=COLOR_GOLD)
        self.correo_entry.pack(fill="x", ipady=6, pady=(4, 10))
        self.correo_entry.bind("<FocusIn>",  lambda _: self._focus_entry(self.correo_entry, True))
        self.correo_entry.bind("<FocusOut>", lambda _: self._focus_entry(self.correo_entry, False))
        self.correo_entry.bind("<KeyRelease>", lambda _: self._limpiar_msg())

        tk.Label(self.extra_outer, text=_tx("campo_tel").upper(),
                 font=("Georgia", 8, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w")
        self.telefono_entry = tk.Entry(self.extra_outer, font=FONT_ENTRY,
                                       bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG,
                                       insertbackground=COLOR_GOLD,
                                       relief="flat", bd=0, highlightthickness=1,
                                       highlightbackground=COLOR_GOLD_DIM,
                                       highlightcolor=COLOR_GOLD)
        self.telefono_entry.pack(fill="x", ipady=6, pady=(4, 0))
        self.telefono_entry.bind("<FocusIn>",  lambda _: self._focus_entry(self.telefono_entry, True))
        self.telefono_entry.bind("<FocusOut>", lambda _: self._focus_entry(self.telefono_entry, False))

        self.extra_outer.pack(fill="x", padx=pad, pady=(8, 0))
        self.extra_outer.pack_forget()

        # ── Botón submit ──
        self.submit_btn = tk.Button(
            self.card, text=_tx("btn_login"),
            font=FONT_BTN, bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
            activebackground=COLOR_GOLD, activeforeground="#000",
            relief="flat", bd=0, cursor="hand2",
            command=self._on_submit)
        self.submit_btn.pack(fill="x", padx=pad, pady=(14, 0), ipady=10)
        self.submit_btn.bind("<Enter>", lambda _: self.submit_btn.config(bg=COLOR_GOLD, fg="#000"))
        self.submit_btn.bind("<Leave>", lambda _: self.submit_btn.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))

        # ── Enlace "¿Olvidaste tu contraseña?" (solo visible en login) ──
        self._olvide_btn = tk.Button(
            self.card, text=_tx("olvide"),
            font=("Georgia", 8, "italic"), bg=COLOR_CARD, fg=COLOR_DIM,
            activebackground=COLOR_CARD, activeforeground=COLOR_GOLD,
            relief="flat", bd=0, cursor="hand2",
            command=self._olvide_contrasena)
        self._olvide_btn.pack(pady=(6, 0))
        self._olvide_btn.bind("<Enter>", lambda _: self._olvide_btn.config(fg=COLOR_GOLD))
        self._olvide_btn.bind("<Leave>", lambda _: self._olvide_btn.config(fg=COLOR_DIM))

        # ── Footer ──
        self._footer_lbl = tk.Label(self.card, text=_tx("footer"),
                                    font=("Georgia", 8, "italic"), bg=COLOR_CARD, fg=COLOR_DIM)
        self._footer_lbl.pack(pady=(8, pad // 2))

    # ── Helpers de UI ───────────────────────────────────
    def _campo(self, parent, texto, padx):
        tk.Label(parent, text=texto.upper(),
                 font=("Georgia", 8, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w", padx=padx if padx else 0)

    def _focus_entry(self, entry, focused):
        color = COLOR_GOLD if focused else COLOR_GOLD_DIM
        entry.config(highlightbackground=color, highlightcolor=color)

    def _actualizar_tabs(self):
        modo = self.modo.get()
        active_cfg   = dict(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT, relief="flat")
        inactive_cfg = dict(bg=COLOR_CARD,     fg=COLOR_DIM,  relief="flat")
        if modo == "login":
            self.tab_login_btn.config(**active_cfg)
            self.tab_reg_btn.config(**inactive_cfg)
            self.submit_btn.config(text=_tx("btn_login")) if hasattr(self, "submit_btn") else None
        else:
            self.tab_login_btn.config(**inactive_cfg)
            self.tab_reg_btn.config(**active_cfg)
            self.submit_btn.config(text=_tx("btn_reg")) if hasattr(self, "submit_btn") else None

    def _switch_modo(self, modo):
        self.modo.set(modo)
        self._limpiar_msg()
        self._actualizar_tabs()

        if modo == "register":
            # El orden ya está fijado desde _build_login_card; solo mostrar
            self.strength_frame.pack(fill="x", padx=36, pady=(2, 4))
            self.req_frame.pack(fill="x", padx=36, pady=(0, 6))
            self.confirm_outer.pack(fill="x", padx=36, pady=(8, 0))
            self.extra_outer.pack(fill="x", padx=36, pady=(8, 0))
            # Mover submit y footer al final re-empaquetando
            self.submit_btn.pack_forget()
            self._olvide_btn.pack_forget()
            self._footer_lbl.pack_forget()
            self.submit_btn.pack(fill="x", padx=36, pady=(14, 0), ipady=10)
            self._footer_lbl.pack(pady=(12, 18))
            self._actualizar_fuerza(self.pass_entry.get())
            self._actualizar_requisitos(self.pass_entry.get())
        else:
            self.strength_frame.pack_forget()
            self.req_frame.pack_forget()
            self.confirm_outer.pack_forget()
            self.extra_outer.pack_forget()
            self.confirm_entry.delete(0, "end")
            self.correo_entry.delete(0, "end")
            self.telefono_entry.delete(0, "end")
            self.strength_lbl.config(text="")
            self.strength_bar.place(relwidth=0)
            self.submit_btn.pack_forget()
            self._olvide_btn.pack_forget()
            self._footer_lbl.pack_forget()
            self.submit_btn.pack(fill="x", padx=36, pady=(14, 0), ipady=10)
            self._olvide_btn.pack(pady=(6, 0))
            self._footer_lbl.pack(pady=(8, 0))

    def _toggle_pass(self):
        self.show_pass = not self.show_pass
        char = "" if self.show_pass else "●"
        self.pass_entry.config(show=char)
        self.confirm_entry.config(show=char)
        if self._show_img_act and self._show_img_inv:
            img = self._show_img_act if self.show_pass else self._show_img_inv
            self.toggle_btn.config(image=img)
        else:
            self.toggle_btn.config(text="🔒" if not self.show_pass else "👁")

    def _on_pass_keyrelease(self, _=None):
        self._limpiar_msg()
        if self.modo.get() == "register":
            pwd = self.pass_entry.get()
            self._actualizar_fuerza(pwd)
            self._actualizar_requisitos(pwd)

    def _actualizar_fuerza(self, pwd):
        checks = validar_contraseña(pwd)
        score  = sum(checks.values())
        pct    = score / 5
        label, color = fuerza_contraseña(pwd)
        self.strength_bar.place(relwidth=pct)
        self.strength_bar.config(bg=color if pwd else COLOR_DIM)
        self.strength_lbl.config(text=label, fg=color)

    def _actualizar_requisitos(self, pwd):
        mapping = {
            "req_len":     "longitud",
            "req_upper":   "mayuscula",
            "req_lower":   "minuscula",
            "req_num":     "numero",
            "req_special": "especial",
        }
        checks = validar_contraseña(pwd)
        req_tx = {
            "req_len":     _tx("req_len"),
            "req_upper":   _tx("req_upper"),
            "req_lower":   _tx("req_lower"),
            "req_num":     _tx("req_num"),
            "req_special": _tx("req_special"),
        }
        for key, check_key in mapping.items():
            ok = checks[check_key]
            fg = COLOR_SUCCESS if ok else COLOR_DIM
            prefix = "  ✓  " if ok else "  ◦  "
            self.req_labels[key].config(fg=fg, text=f"{prefix}{req_tx[key]}")

    def _mostrar_msg(self, texto, tipo="error"):
        colores = {"error": COLOR_ERROR, "success": COLOR_SUCCESS, "warning": COLOR_WARNING}
        self.msg_label.config(text=texto, fg=colores.get(tipo, COLOR_ERROR))

    def _limpiar_msg(self):
        self.msg_label.config(text="")

    # ── Lógica principal ────────────────────────────────
    def _on_submit(self):
        usuario   = self.user_entry.get().strip()
        contraseña = self.pass_entry.get()

        if not usuario:
            self._mostrar_msg("Introduce tu nombre de usuario.")
            self.user_entry.focus_set()
            return
        if not contraseña:
            self._mostrar_msg("Introduce tu contraseña.")
            self.pass_entry.focus_set()
            return

        if self.modo.get() == "login":
            self._login(usuario, contraseña)
        else:
            self._registrar(usuario, contraseña)

    def _login(self, usuario, contraseña):
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("SELECT password, rol FROM usuarios WHERE nombre = ?", (usuario,))
        row = cur.fetchone()
        conn.close()

        if row is None:
            # ── Usuario no existe → preguntar si registrarse ──
            resp = dialogo_yesno(
                self,
                "Usuario no encontrado",
                f"El usuario «{usuario}» no está registrado en la biblioteca.\n\n"
                "¿Deseas crear una cuenta con este nombre?",
                btn_si="Crear cuenta",
                btn_no="Cancelar"
            )
            if resp:
                if not contraseña_es_valida(contraseña):
                    # Redirigir al modo registro para que complete la contraseña
                    self._switch_modo("register")
                    self.user_entry.delete(0, "end")
                    self.user_entry.insert(0, usuario)
                    self.pass_entry.delete(0, "end")
                    self._mostrar_msg(
                        "Crea una contraseña segura para completar el registro.", "warning"
                    )
                    self.pass_entry.focus_set()
                    return
                try:
                    rol_nuevo = self._insertar_usuario(usuario, contraseña)
                    self._bienvenida(usuario, nuevo=True, rol=rol_nuevo)
                except ValueError as e:
                    self._mostrar_msg(str(e))

        elif row[0] == hash_password(contraseña):
            # ── Contraseña correcta ──
            rol = row[1]
            self._bienvenida(usuario, nuevo=False, rol=rol)

        else:
            # ── Contraseña incorrecta ──
            self._mostrar_msg("Contraseña incorrecta.")
            self.pass_entry.focus_set()
            self.pass_entry.select_range(0, "end")
            dialogo_error(
                self,
                "Contraseña incorrecta",
                f"La contraseña introducida para «{usuario}» es incorrecta.\n\n"
                "Comprueba que el Bloq Mayús no esté activado."
            )

    def _registrar(self, usuario, contraseña):
        if not contraseña_es_valida(contraseña):
            self._mostrar_msg(
                "La contraseña no cumple los requisitos de seguridad.", "warning"
            )
            return

        confirm = self.confirm_entry.get()
        if contraseña != confirm:
            self._mostrar_msg("Las contraseñas no coinciden.")
            self.confirm_entry.focus_set()
            return

        correo   = self.correo_entry.get().strip()
        telefono = self.telefono_entry.get().strip()

        if not correo:
            self._mostrar_msg("El correo electrónico es obligatorio.")
            self.correo_entry.focus_set()
            return
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", correo):
            self._mostrar_msg("El correo electrónico no tiene un formato válido.")
            self.correo_entry.focus_set()
            return

        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("SELECT id_usuario FROM usuarios WHERE nombre = ?", (usuario,))
        existe = cur.fetchone()
        conn.close()

        if existe:
            self._mostrar_msg(f"El usuario «{usuario}» ya existe en el sistema.")
            return

        # ── Comprobar correo duplicado antes de enviar nada ──
        conn2 = sqlite3.connect(DB_PATH)
        cur2  = conn2.cursor()
        cur2.execute("SELECT id_usuario FROM usuarios WHERE correo = ?", (correo,))
        correo_existe = cur2.fetchone()
        conn2.close()
        if correo_existe:
            self._mostrar_msg(
                f"El correo '{correo}' ya está asociado a otra cuenta.\n"
                "Usa otro correo o recupera tu contraseña.")
            self.correo_entry.focus_set()
            return

        # ── Verificar que el correo existe antes de enviar ──
        self._mostrar_msg("Comprobando correo electrónico...", "warning")
        self.update_idletasks()

        ok_smtp, err_smtp = verificar_correo_smtp(correo)
        if not ok_smtp:
            self._limpiar_msg()
            dialogo_error(self, "Correo no válido", err_smtp)
            self.correo_entry.focus_set()
            return

        self._mostrar_msg("Enviando código de verificación...", "warning")
        self.update_idletasks()

        codigo = generar_codigo()
        ok, err = enviar_codigo_verificacion(correo, codigo)

        self._limpiar_msg()

        if not ok:
            dialogo_error(self, "Error al enviar correo", err)
            return

        # Mostrar diálogo de verificación
        dlg = DialogoVerificacion(self, correo, codigo)

        if dlg.verificado:
            try:
                rol_nuevo = self._insertar_usuario(usuario, contraseña, correo, telefono)
                self._bienvenida(usuario, nuevo=True, rol=rol_nuevo)
            except ValueError as e:
                self._mostrar_msg(str(e))
        else:
            self._mostrar_msg("Verificación cancelada o fallida. No se creó la cuenta.")

    def _insertar_usuario(self, usuario, contraseña, correo="", telefono=""):
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM usuarios")
            rol = "admin" if cur.fetchone()[0] == 0 else "normal"
            # Comprobar nombre duplicado
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE nombre=?", (usuario,))
            if cur.fetchone()[0] > 0:
                raise ValueError(f"El nombre de usuario '{usuario}' ya está registrado.")
            # Comprobar correo duplicado
            if correo:
                cur.execute("SELECT COUNT(*) FROM usuarios WHERE correo=?", (correo,))
                if cur.fetchone()[0] > 0:
                    raise ValueError(
                        f"El correo '{correo}' ya está asociado a otra cuenta.\n"
                        "Usa otro correo o recupera tu contraseña."
                    )
            cur.execute(
                "INSERT INTO usuarios (nombre, correo, telefono, password, rol) "
                "VALUES (?, ?, ?, ?, ?)",
                (usuario, correo or None, telefono or None, hash_password(contraseña), rol)
            )
            conn.commit()
        finally:
            conn.close()
        return rol

    # ── Pantalla de bienvenida / menú principal ───────────
    def _bienvenida(self, usuario, nuevo=False, rol='normal'):
        self.usuario_activo = usuario
        self.rol_activo = rol
        self._set_fondo(menu=True)
        self.card.place_forget()

        # Contenedor a pantalla completa
        self.menu_frame = tk.Frame(self, bg="#0e0d12")
        self.menu_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # Splash de carga antes de abrir el menú
        if nuevo:
            msg = f"Bienvenido/a, {usuario}\nCuenta creada correctamente."
        else:
            msg = f"Bienvenido/a, {usuario}"
        splash_frame = tk.Frame(self.menu_frame, bg=COLOR_BG)
        splash_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(splash_frame, text="⏳",
                 font=("Georgia", 36), bg=COLOR_BG, fg=COLOR_GOLD
                 ).pack(expand=True, pady=(0, 10))
        tk.Label(splash_frame, text=msg,
                 font=("Georgia", 13, "italic"), bg=COLOR_BG, fg=COLOR_GOLD
                 ).pack()
        _cargando_txt = {"es": "Cargando menú...", "en": "Loading menu..."}
        _idioma_s = ConfigApp.get("idioma") or "es"
        tk.Label(splash_frame, text=_cargando_txt.get(_idioma_s, "Cargando menú..."),
                 font=("Georgia", 10), bg=COLOR_BG, fg=COLOR_DIM
                 ).pack(pady=(6, 0))
        splash_frame.update_idletasks()
        delay = 1200 if nuevo else 600
        self.menu_frame.after(delay, lambda: self._cargar_menu(usuario, rol))

    def _cargar_menu(self, usuario, rol="normal"):
        """Instancia el MenuPrincipal y lo muestra."""
        # Limpiar splash si existe
        for w in self.menu_frame.winfo_children():
            w.destroy()
        self._menu = MenuPrincipal(
            parent=self.menu_frame,
            db_path=DB_PATH,
            usuario=usuario,
            rol=rol,
            on_logout=self._logout,
        )
        self._menu.mostrar()

    def _olvide_contrasena(self):
        """
        Flujo de recuperación de contraseña:
        1. Pedir nombre de usuario.
        2. Buscar correo en BD.
        3. Enviar código de verificación.
        4. Verificar código con DialogoVerificacion.
        5. Permitir nueva contraseña.
        """
        usuario = self.user_entry.get().strip()

        if not usuario:
            self._mostrar_msg("Introduce tu nombre de usuario primero.")
            self.user_entry.focus_set()
            return

        # Buscar correo en BD
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("SELECT correo FROM usuarios WHERE nombre = ?", (usuario,))
        row = cur.fetchone()
        conn.close()

        if not row:
            dialogo_error(self, "Usuario no encontrado",
                          f"No existe ningún usuario llamado «{usuario}».")
            return

        correo = row[0]
        if not correo:
            dialogo_error(self, "Sin correo registrado",
                          f"El usuario «{usuario}» no tiene correo registrado.\n"
                          "Contacta con el administrador.")
            return

        # Verificar que el correo existe
        self._mostrar_msg("Enviando código de verificación...", "warning")
        self.update_idletasks()

        codigo = generar_codigo()
        ok, err = enviar_codigo_verificacion(correo, codigo)
        self._limpiar_msg()

        if not ok:
            dialogo_error(self, "Error al enviar correo", err)
            return

        # Diálogo de verificación
        dlg = DialogoVerificacion(self, correo, codigo)

        if not dlg.verificado:
            self._mostrar_msg("Verificación cancelada o fallida.")
            return

        # Diálogo para nueva contraseña
        self._dialogo_nueva_contrasena(usuario)

    def _dialogo_nueva_contrasena(self, usuario: str):
        """Muestra un diálogo modal para introducir la nueva contraseña."""
        dlg = tk.Toplevel(self)
        dlg.title("Nueva contraseña")
        dlg.resizable(False, False)
        dlg.configure(bg=COLOR_BG)
        dlg.grab_set()

        # Centrar
        dlg.update_idletasks()
        w, h = 380, 300
        x = self.winfo_x() + (self.winfo_width()  - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        pad = 32
        tk.Label(dlg, text="Nueva contraseña",
                 font=("Georgia", 14, "bold"),
                 bg=COLOR_BG, fg=COLOR_GOLD).pack(pady=(28, 4))
        tk.Label(dlg, text=f"Usuario: {usuario}",
                 font=("Georgia", 9, "italic"),
                 bg=COLOR_BG, fg=COLOR_DIM).pack()

        tk.Label(dlg, text="Nueva contraseña",
                 font=("Georgia", 9, "bold"),
                 bg=COLOR_BG, fg=COLOR_DIM).pack(anchor="w", padx=pad, pady=(18, 0))
        e_nueva = tk.Entry(dlg, font=("Georgia", 12), show="●",
                           bg=COLOR_CARD2, fg=COLOR_TEXT,
                           insertbackground=COLOR_GOLD, relief="flat",
                           highlightthickness=1,
                           highlightbackground=COLOR_GOLD_DIM,
                           highlightcolor=COLOR_GOLD)
        e_nueva.pack(fill="x", padx=pad, ipady=6)

        tk.Label(dlg, text="Confirmar contraseña",
                 font=("Georgia", 9, "bold"),
                 bg=COLOR_BG, fg=COLOR_DIM).pack(anchor="w", padx=pad, pady=(10, 0))
        e_conf = tk.Entry(dlg, font=("Georgia", 12), show="●",
                          bg=COLOR_CARD2, fg=COLOR_TEXT,
                          insertbackground=COLOR_GOLD, relief="flat",
                          highlightthickness=1,
                          highlightbackground=COLOR_GOLD_DIM,
                          highlightcolor=COLOR_GOLD)
        e_conf.pack(fill="x", padx=pad, ipady=6)

        msg = tk.Label(dlg, text="", font=("Georgia", 9, "italic"),
                       bg=COLOR_BG, fg=COLOR_ERROR, wraplength=320)
        msg.pack(pady=(8, 0))

        def _guardar():
            nueva    = e_nueva.get()
            confirma = e_conf.get()
            if nueva != confirma:
                msg.config(text="Las contraseñas no coinciden.")
                return
            if not contraseña_es_valida(nueva):
                msg.config(text="La contraseña no cumple los requisitos de seguridad.\n"
                               "(Mín. 8 caracteres, mayúscula, minúscula, número y símbolo)")
                return
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            cur.execute("UPDATE usuarios SET password = ? WHERE nombre = ?",
                        (hash_password(nueva), usuario))
            conn.commit()
            conn.close()
            dlg.destroy()
            dialogo_info(self, "Contraseña actualizada",
                         f"La contraseña de «{usuario}» ha sido cambiada.\n"
                         "Ya puedes iniciar sesión.")

        btn = tk.Button(dlg, text="Guardar contraseña",
                        font=("Georgia", 10, "bold"),
                        bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
                        activebackground=COLOR_GOLD, activeforeground="#000",
                        relief="flat", bd=0, cursor="hand2",
                        command=_guardar)
        btn.pack(fill="x", padx=pad, pady=(14, 0), ipady=8)
        btn.bind("<Enter>", lambda _: btn.config(bg=COLOR_GOLD, fg="#000"))
        btn.bind("<Leave>", lambda _: btn.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))

        e_nueva.bind("<Return>", lambda _: e_conf.focus_set())
        e_conf.bind("<Return>",  lambda _: _guardar())
        e_nueva.focus_set()
        dlg.wait_window()

    def _logout(self):
        self.usuario_activo = None
        if hasattr(self, "_menu"):
            self._menu.ocultar()
        if hasattr(self, "menu_frame") and self.menu_frame.winfo_exists():
            # Mostrar pantalla de carga sobre el menú antes de destruirlo
            loading = tk.Frame(self.menu_frame, bg=COLOR_BG)
            loading.place(relx=0, rely=0, relwidth=1, relheight=1)
            tk.Label(loading, text="⏳",
                     font=("Georgia", 36), bg=COLOR_BG, fg=COLOR_GOLD
                     ).pack(expand=True, pady=(0, 10))
            _cerrar_txt = {"es": "Cerrando sesión...", "en": "Logging out..."}
            _idioma = ConfigApp.get("idioma") or "es"
            tk.Label(loading, text=_cerrar_txt.get(_idioma, "Cerrando sesión..."),
                     font=("Georgia", 12, "italic"), bg=COLOR_BG, fg=COLOR_DIM
                     ).pack()
            loading.update_idletasks()
            self.menu_frame.after(500, self._logout_deferred)
        else:
            self._logout_deferred()

    def _logout_deferred(self):
        if hasattr(self, "menu_frame") and self.menu_frame.winfo_exists():
            self.menu_frame.destroy()

        # Destruir TODOS los widgets hijos de la ventana raíz
        # y reconstruir login completo (fondo + tarjeta)
        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        # Limpiar referencias a widgets destruidos
        for attr in ("submit_btn", "msg_label", "tab_login_btn", "tab_reg_btn",
                     "user_entry", "pass_entry", "confirm_entry",
                     "strength_frame", "req_frame", "confirm_outer",
                     "extra_outer", "_olvide_btn", "_footer_lbl",
                     "strength_lbl", "strength_bar", "strength_bar_bg",
                     "_bg_label", "card"):
            if hasattr(self, attr):
                delattr(self, attr)

        # Releer tema e idioma
        ConfigApp.invalidar()
        self._aplicar_tema_login()

        # Reconstruir fondo y tarjeta desde cero
        self._bg_label = tk.Label(self, bd=0)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._set_fondo(menu=False)

        self.modo = tk.StringVar(value="login")
        self.show_pass = False
        self._build_login_card()

        # Rebind teclas
        self.bind("<Return>", lambda _: self._on_submit())
        self.bind("<Escape>", lambda _: self._cerrar_dialogo_si_existe())
        self.user_entry.focus_set()

    def _cerrar_dialogo_si_existe(self):
        # Tkinter messagebox no tiene cierre programático directo,
        # pero dejamos el bind por si se añade un diálogo custom
        pass


# -------------------
# Arranque
# -------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()