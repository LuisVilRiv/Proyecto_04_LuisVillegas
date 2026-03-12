"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Módulo de gestión de préstamos y devoluciones. Los combos
                 permiten buscar socio y libro escribiendo o seleccionando
                 de la lista desplegable.
Autor/a:         Luis Villegas Rivera
Fecha:           2026-03-09
Clases principales:
    - SeccionPrestamos : Panel tkinter para préstamos y devoluciones.
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
import os
from datetime import datetime, timedelta

from secciones.biblioteca_gestion_libros   import (
    Libro, aplicar_tema,
    COLOR_BG, COLOR_CARD, COLOR_CARD2, COLOR_GOLD, COLOR_GOLD_DIM,
    COLOR_TEXT, COLOR_DIM, COLOR_ERROR, COLOR_SUCCESS,
    FONT_TITLE, FONT_LABEL, FONT_ENTRY, FONT_SMALL, FONT_BTN,
)
from secciones.biblioteca_ajustes import T
from secciones.biblioteca_gestion_usuarios import Usuario

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIBOS_DIR = os.path.join(BASE_DIR, "recibos")


# ── Generación de recibo ──────────────────────────────────────
def _nombre_limpio(nombre: str) -> str:
    """Convierte nombre a slug seguro para nombre de archivo."""
    import unicodedata, re
    n = unicodedata.normalize("NFD", nombre)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = re.sub(r"[^\w\s-]", "", n).strip()
    return re.sub(r"[\s]+", "_", n)[:30]


def generar_recibo(usuario: Usuario, libro: Libro, id_prestamo: int,
                   ruta_destino: str = None) -> str:
    """
    Genera un recibo de préstamo en PDF con el tema e idioma actuales.
    Si ruta_destino se especifica, sobreescribe ese archivo en lugar de crear uno nuevo.
    Devuelve la ruta absoluta al archivo .pdf generado.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units     import cm
        from reportlab.lib           import colors
        from reportlab.platypus      import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums  import TA_CENTER, TA_LEFT
    except ImportError:
        raise IOError(
            "reportlab no está instalado. Ejecuta: pip install reportlab")

    # ── Idioma ────────────────────────────────────────────────
    from secciones.biblioteca_ajustes import ConfigApp, IDIOMAS
    _lang = ConfigApp.get("idioma") or "es"
    _i    = IDIOMAS.get(_lang, IDIOMAS["es"])
    def _p(k, fb=""):
        return _i.get(k, fb or k)

    _TX_PDF = {
        "es": {
            "titulo":      "EL ARCHIVO DE LOS MUNDOS",
            "subtitulo":   "COMPROBANTE DE PRESTAMO",
            "prestamo":    "PRESTAMO",
            "emision":     "FECHA DE EMISION",
            "sec_socio":   "DATOS DEL SOCIO",
            "sec_libro":   "LIBRO PRESTADO",
            "sec_dev":     "DEVOLUCION",
            "id_socio":    "ID socio",
            "nombre":      "Nombre",
            "correo":      "Correo",
            "telefono":    "Telefono",
            "isbn":        "ISBN",
            "titulo_l":    "Titulo",
            "autor":       "Autor",
            "fecha_lim":   "Fecha limite",
            "plazo":       "Plazo",
            "plazo_val":   "15 dias naturales",
            "pie":         "Conserve este comprobante como justificante del prestamo.",
            "sello_ok":    "DEVUELTO",
            "sello_tard":  "DEVUELTO CON RETRASO",
            "sello_sub_ok":    lambda fr: f"el {fr}",
            "sello_sub_tard":  lambda d:  f"con {d} dias de retraso",
        },
        "en": {
            "titulo":      "THE ARCHIVE OF WORLDS",
            "subtitulo":   "LOAN RECEIPT",
            "prestamo":    "LOAN",
            "emision":     "ISSUE DATE",
            "sec_socio":   "MEMBER DETAILS",
            "sec_libro":   "BORROWED BOOK",
            "sec_dev":     "RETURN",
            "id_socio":    "Member ID",
            "nombre":      "Name",
            "correo":      "Email",
            "telefono":    "Phone",
            "isbn":        "ISBN",
            "titulo_l":    "Title",
            "autor":       "Author",
            "fecha_lim":   "Due date",
            "plazo":       "Period",
            "plazo_val":   "15 calendar days",
            "pie":         "Keep this receipt as proof of your loan.",
            "sello_ok":    "RETURNED",
            "sello_tard":  "RETURNED LATE",
            "sello_sub_ok":    lambda fr: f"on {fr}",
            "sello_sub_tard":  lambda d:  f"{d} days late",
        },
    }
    TX = _TX_PDF.get(_lang, _TX_PDF["es"])

    # ── Paleta desde el tema activo ───────────────────────────
    tc    = ConfigApp.colores()
    GOLD  = colors.HexColor(tc["acento"])
    DARK  = colors.HexColor(tc["bg"])
    CARD  = colors.HexColor(tc["card"])
    CARD2 = colors.HexColor(tc["card2"])
    DIM   = colors.HexColor(tc["dim"])
    TEXT  = colors.HexColor(tc["text"])
    ERR   = colors.HexColor(tc["error"])
    LINE  = colors.HexColor(tc["sep"])

    os.makedirs(RECIBOS_DIR, exist_ok=True)
    ahora      = datetime.now()
    fecha_dev  = (ahora + timedelta(days=15)).strftime("%d/%m/%Y")
    fecha_emis = ahora.strftime("%d/%m/%Y  %H:%M")

    if ruta_destino:
        ruta_pdf = ruta_destino
    else:
        slug       = _nombre_limpio(usuario.nombre)
        ts         = ahora.strftime("%Y%m%d_%H%M")
        nombre_pdf = f"recibo_{id_prestamo:04d}_{usuario.id_usuario}_{slug}_{ts}.pdf"
        ruta_pdf   = os.path.join(RECIBOS_DIR, nombre_pdf)

    # ── Estilos ───────────────────────────────────────────────
    base = getSampleStyleSheet()
    def ps(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    S = {
        "titulo":   ps("t",  fontName="Times-Bold",     fontSize=17,
                        leading=26,
                        textColor=GOLD, alignment=TA_CENTER),
        "sub":      ps("s",  fontName="Times-Italic",   fontSize=9,
                        leading=14,
                        textColor=DIM,  alignment=TA_CENTER),
        "sec":      ps("sh", fontName="Helvetica-Bold", fontSize=10,
                        leading=14,
                        textColor=GOLD, alignment=TA_LEFT),
        "lbl":      ps("lb", fontName="Helvetica",      fontSize=9,
                        leading=13,
                        textColor=DIM,  alignment=TA_LEFT),
        "val":      ps("vl", fontName="Helvetica-Bold", fontSize=10,
                        leading=14,
                        textColor=TEXT, alignment=TA_LEFT),
        "val_gold": ps("vg", fontName="Helvetica-Bold", fontSize=10,
                        leading=14,
                        textColor=GOLD, alignment=TA_LEFT),
        "val_err":  ps("ve", fontName="Helvetica-Bold", fontSize=10,
                        leading=14,
                        textColor=ERR,  alignment=TA_LEFT),
        "num":      ps("nm", fontName="Times-Bold",     fontSize=24,
                        leading=30,
                        textColor=GOLD, alignment=TA_LEFT),
        "fecha":    ps("fv", fontName="Helvetica-Bold", fontSize=12,
                        leading=16,
                        textColor=TEXT, alignment=TA_LEFT),
        "pie":      ps("pi", fontName="Times-Italic",   fontSize=9,
                        leading=13,
                        textColor=DIM,  alignment=TA_CENTER),
    }

    ancho = A4[0] - 4*cm   # ancho útil: A4 menos márgenes (2cm + 2cm)

    # Separador horizontal como tabla (más fiable que HRFlowable)
    def hr_table(color=GOLD, thickness=1, before=6, after=6):
        t = Table([[""]], colWidths=[ancho], rowHeights=[thickness])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), color),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ]))
        # Envolver con espaciado
        return [Spacer(1, before), t, Spacer(1, after)]

    def kv_tabla(filas):
        col1 = 3.6*cm
        col2 = ancho - col1
        data = [[Paragraph(lb, S["lbl"]), Paragraph(vl, S[st])]
                for lb, vl, st in filas]
        t = Table(data, colWidths=[col1, col2])
        t.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [CARD, CARD2]),
            ("LEFTPADDING",    (0,0), (-1,-1), 10),
            ("RIGHTPADDING",   (0,0), (-1,-1), 10),
            ("TOPPADDING",     (0,0), (-1,-1),  6),
            ("BOTTOMPADDING",  (0,0), (-1,-1),  6),
            ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
            ("LINEBELOW",      (0,0), (-1,-2), 0.3, LINE),
        ]))
        return t

    # ── Contenido ─────────────────────────────────────────────
    story = []

    # Línea dorada superior gruesa
    story += hr_table(GOLD, thickness=3, before=0, after=14)

    # Cabecera: título + subtítulo en una tabla para control de espacio exacto
    header_tbl = Table([
        [Paragraph(TX["titulo"],    S["titulo"])],
        [Paragraph(TX["subtitulo"], S["sub"])],
    ], colWidths=[ancho], rowHeights=[32, 20])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(header_tbl)

    story += hr_table(GOLD, thickness=1, before=14, after=0)

    # Bloque préstamo + fecha en tabla con alturas fijas
    cab = Table([
        [Paragraph(TX["prestamo"],  S["lbl"]),
         Paragraph(TX["emision"],   S["lbl"])],
        [Paragraph(f"# {id_prestamo:04d}", S["num"]),
         Paragraph(fecha_emis,             S["fecha"])],
    ], colWidths=[ancho * 0.36, ancho * 0.64],
       rowHeights=[18, 36])
    cab.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), CARD),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ("TOPPADDING",    (0,0), (0,0),    4),
        ("TOPPADDING",    (0,1), (-1,1),   4),
        ("BOTTOMPADDING", (0,0), (-1,-1),  4),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("LINERIGHT",     (0,0), (0,-1),  0.5, LINE),
    ]))
    story.append(cab)

    story += hr_table(GOLD, thickness=1, before=0, after=10)

    # Datos del socio
    story.append(Paragraph(TX["sec_socio"], S["sec"]))
    story += hr_table(GOLD, thickness=0.4, before=4, after=0)
    story.append(kv_tabla([
        (TX["id_socio"], str(usuario.id_usuario),               "val_gold"),
        (TX["nombre"],   usuario.nombre                 or "—", "val"),
        (TX["correo"],   getattr(usuario, "correo", "") or "—", "val"),
        (TX["telefono"], getattr(usuario, "telefono","")or "—", "val"),
    ]))

    story.append(Spacer(1, 12))

    # Libro prestado
    story.append(Paragraph(TX["sec_libro"], S["sec"]))
    story += hr_table(GOLD, thickness=0.4, before=4, after=0)
    story.append(kv_tabla([
        (TX["isbn"],    libro.isbn   or "—", "val"),
        (TX["titulo_l"],libro.titulo or "—", "val_gold"),
        (TX["autor"],   libro.autor  or "—", "val"),
    ]))

    story.append(Spacer(1, 12))

    # Devolución
    story.append(Paragraph(TX["sec_dev"], S["sec"]))
    story += hr_table(ERR, thickness=0.4, before=4, after=0)
    story.append(kv_tabla([
        (TX["fecha_lim"], fecha_dev,          "val_err"),
        (TX["plazo"],     TX["plazo_val"],    "val"),
    ]))

    story.append(Spacer(1, 18))
    story += hr_table(GOLD, thickness=2, before=0, after=6)
    story.append(Paragraph(TX["pie"], S["pie"]))
    story.append(Spacer(1, 6))
    story += hr_table(GOLD, thickness=2, before=0, after=0)

    def fondo(c, doc):
        c.saveState()
        c.setFillColor(DARK)
        c.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        c.restoreState()

    doc = SimpleDocTemplate(
        ruta_pdf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
        title=f"Recibo Prestamo #{id_prestamo:04d}",
        author="Biblioteca El Archivo de los Mundos",
    )
    try:
        doc.build(story, onFirstPage=fondo, onLaterPages=fondo)
    except Exception as e:
        raise IOError(f"Error al crear el PDF: {e}")

    return ruta_pdf


# ── Sello de devolución sobre PDF existente ──────────────────
def estampar_devolucion_en_pdf(id_prestamo: int,
                                fecha_real: str,
                                fecha_estimada: str) -> bool:
    """
    Superpone un sello semitransparente en el margen derecho del PDF del recibo.
    Dorado si devuelto a tiempo, rojo si con retraso.
    """
    try:
        from pypdf import PdfReader, PdfWriter
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units     import cm
        from reportlab.lib           import colors
        from reportlab.pdfgen        import canvas as rl_canvas
        import io
        from datetime import datetime as _dt
    except ImportError:
        return False

    if not os.path.isdir(RECIBOS_DIR):
        return False
    patron = f"recibo_{id_prestamo:04d}_"
    candidatos = [f for f in os.listdir(RECIBOS_DIR)
                  if f.startswith(patron) and f.endswith(".pdf")]
    if not candidatos:
        return False
    ruta_pdf = os.path.join(RECIBOS_DIR, sorted(candidatos)[-1])

    try:
        fe = _dt.strptime(fecha_estimada, "%Y-%m-%d")
        fr = _dt.strptime(fecha_real,     "%Y-%m-%d")
        dias_retraso = max(0, (fr - fe).days)
    except ValueError:
        dias_retraso = 0

    # Colores del tema e idioma activos
    from secciones.biblioteca_ajustes import ConfigApp, IDIOMAS
    tc   = ConfigApp.colores()
    lang = ConfigApp.get("idioma") or "es"
    _TX_S = {
        "es": {
            "ok":   "DEVUELTO",
            "tard": "DEVUELTO CON RETRASO",
            "sub_ok":   lambda fr: f"el {fr.strftime('%d/%m/%Y')}",
            "sub_tard": lambda d:  f"con {d} dias de retraso",
        },
        "en": {
            "ok":   "RETURNED",
            "tard": "RETURNED LATE",
            "sub_ok":   lambda fr: f"on {fr.strftime('%d/%m/%Y')}",
            "sub_tard": lambda d:  f"{d} days late",
        },
    }
    _ts = _TX_S.get(lang, _TX_S["es"])

    con_retraso  = dias_retraso > 0
    color_acento = colors.HexColor(tc["error"]) if con_retraso else colors.HexColor(tc["acento"])
    texto1 = _ts["tard"] if con_retraso else _ts["ok"]
    texto2 = _ts["sub_tard"](dias_retraso) if con_retraso else _ts["sub_ok"](fr)

    buf = io.BytesIO()
    w, h = A4
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.saveState()

    # Margen derecho, centrado verticalmente en el área de contenido
    center_y = ((h - 2*cm) + 2*cm) / 2
    stamp_x  = w - 2*cm - 1.5*cm
    c.translate(stamp_x, center_y)
    c.rotate(90)

    c.setFont("Times-Bold", 22)
    txt1_w  = c.stringWidth(texto1, "Times-Bold", 22)
    sello_w = max(txt1_w + 44, 300)
    sello_h = 76

    # Marco exterior
    c.setStrokeColor(color_acento)
    c.setLineWidth(2)
    c.setStrokeAlpha(0.85)
    c.setFillAlpha(0)
    c.rect(-sello_w/2, -sello_h/2, sello_w, sello_h, fill=0, stroke=1)
    # Marco interior fino
    m = 5
    c.setLineWidth(0.6)
    c.setStrokeAlpha(0.50)
    c.rect(-sello_w/2+m, -sello_h/2+m, sello_w-2*m, sello_h-2*m, fill=0, stroke=1)

    # Texto principal
    c.setFillColor(color_acento)
    c.setFillAlpha(0.92)
    c.setStrokeAlpha(0)
    c.setFont("Times-Bold", 22)
    c.drawCentredString(0, 10, texto1)

    # Texto secundario
    c.setFont("Times-Italic", 10)
    c.setFillAlpha(0.80)
    c.drawCentredString(0, -12, texto2)

    c.restoreState()
    c.save()
    buf.seek(0)

    try:
        reader  = PdfReader(ruta_pdf)
        overlay = PdfReader(buf)
        writer  = PdfWriter()
        for i, page in enumerate(reader.pages):
            if i == 0:
                page.merge_page(overlay.pages[0])
            writer.add_page(page)
        with open(ruta_pdf, "wb") as f:
            writer.write(f)
        return True
    except Exception:
        return False


# ── Helper: estilo Combobox oscuro ────────────────────────────
def _aplicar_estilo_combo():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("Dark.TCombobox",
        fieldbackground=COLOR_CARD2, background=COLOR_CARD,
        foreground=COLOR_TEXT, selectbackground=COLOR_GOLD_DIM,
        selectforeground=COLOR_TEXT, arrowcolor=COLOR_GOLD,
        bordercolor=COLOR_GOLD_DIM, lightcolor=COLOR_CARD2,
        darkcolor=COLOR_CARD2, font=("Georgia", 11))
    s.map("Dark.TCombobox",
        fieldbackground=[("readonly", COLOR_CARD2)],
        foreground=[("readonly", COLOR_TEXT)],
        arrowcolor=[("readonly", COLOR_GOLD)])


# ═══════════════════════════════════════════════════════
# SECCIÓN TKINTER — Préstamos y Devoluciones (admin)
# ═══════════════════════════════════════════════════════
class SeccionPrestamos:
    """
    Panel para gestionar préstamos y devoluciones.
    Combos con búsqueda en tiempo real para socio y libro.
    """

    def __init__(self, parent: tk.Widget, db_path: str, usuario: str):
        aplicar_tema()
        self.db_path        = db_path
        self.usuario_activo = usuario

        # Mapas label→id para los combos
        self._socios_map: dict[str, int] = {}   # "Nombre (ID)" → id_usuario
        self._libros_map: dict[str, str] = {}   # "Título — Autor (ISBN)" → isbn

        self.frame = tk.Frame(parent, bg=COLOR_BG)
        _aplicar_estilo_combo()
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────
    def _build_ui(self):
        # Cabecera
        cab = tk.Frame(self.frame, bg=COLOR_CARD, height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text=T("cab_prestamos","🔖  Préstamos y Devoluciones"),
                 font=FONT_TITLE, bg=COLOR_CARD, fg=COLOR_GOLD
                 ).pack(side="left", padx=24, pady=12)
        tk.Frame(self.frame, height=1, bg=COLOR_GOLD_DIM).pack(fill="x")

        body = tk.Frame(self.frame, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Panel izquierdo ───────────────────────────────────
        left = tk.Frame(body, bg=COLOR_CARD, width=300,
                        highlightthickness=1, highlightbackground=COLOR_GOLD_DIM)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)

        # ─ Nuevo préstamo ─
        tk.Label(left, text=T("nuevo_prestamo","NUEVO PRÉSTAMO"),
                 font=("Georgia", 9, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Frame(left, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=20)

        # Combo socio
        tk.Label(left, text=T("lbl_socio","Socio"), font=FONT_SMALL,
                 bg=COLOR_CARD, fg=COLOR_DIM).pack(anchor="w", padx=20, pady=(12, 0))
        self._socio_var = tk.StringVar()
        self._socio_combo = ttk.Combobox(
            left, textvariable=self._socio_var,
            font=("Georgia", 11), style="Dark.TCombobox")
        self._socio_combo.pack(fill="x", padx=20, ipady=4, pady=(3, 0))
        self._socio_combo.bind("<KeyRelease>",        lambda _: self._filtrar_socios())
        self._socio_combo.bind("<<ComboboxSelected>>", lambda _: self._socio_combo.selection_clear())

        # Combo libro
        tk.Label(left, text=T("lbl_libro","Libro"), font=FONT_SMALL,
                 bg=COLOR_CARD, fg=COLOR_DIM).pack(anchor="w", padx=20, pady=(10, 0))
        self._libro_var = tk.StringVar()
        self._libro_combo = ttk.Combobox(
            left, textvariable=self._libro_var,
            font=("Georgia", 11), style="Dark.TCombobox")
        self._libro_combo.pack(fill="x", padx=20, ipady=4, pady=(3, 0))
        self._libro_combo.bind("<KeyRelease>",        lambda _: self._filtrar_libros())
        self._libro_combo.bind("<<ComboboxSelected>>", lambda _: self._libro_combo.selection_clear())

        self._msg_prest = tk.Label(
            left, text="", font=("Georgia", 9, "italic"),
            bg=COLOR_CARD, fg=COLOR_ERROR, wraplength=260)
        self._msg_prest.pack(padx=20, pady=(8, 0), anchor="w")

        btn_p = tk.Button(left, text=T("btn_prestamo","＋  Registrar préstamo"),
                          font=FONT_BTN, bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
                          activebackground=COLOR_GOLD, activeforeground="#000",
                          relief="flat", bd=0, cursor="hand2",
                          command=self._registrar_prestamo)
        btn_p.pack(fill="x", padx=20, pady=(10, 0), ipady=8)
        btn_p.bind("<Enter>", lambda _: btn_p.config(bg=COLOR_GOLD, fg="#000"))
        btn_p.bind("<Leave>", lambda _: btn_p.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))

        # ─ Devolución ─
        tk.Label(left, text=T("devolucion_hdr","DEVOLUCIÓN"),
                 font=("Georgia", 9, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w", padx=20, pady=(24, 4))
        tk.Frame(left, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=20)
        tk.Label(left, text=T("sel_prestamo_tabla","Selecciona un préstamo activo en la tabla"),
                 font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_DIM,
                 wraplength=250).pack(anchor="w", padx=20, pady=(10, 0))

        self._msg_dev = tk.Label(
            left, text="", font=("Georgia", 9, "italic"),
            bg=COLOR_CARD, fg=COLOR_ERROR, wraplength=260)
        self._msg_dev.pack(padx=20, pady=(8, 0), anchor="w")

        btn_d = tk.Button(left, text=T("btn_devolucion","↩  Registrar devolución"),
                          font=FONT_BTN, bg="#1a2a1a", fg="#6acf7a",
                          activebackground=COLOR_SUCCESS, activeforeground=COLOR_TEXT,
                          relief="flat", bd=0, cursor="hand2",
                          command=self._registrar_devolucion)
        btn_d.pack(fill="x", padx=20, pady=(10, 20), ipady=8)

        # ── Panel derecho: tabla ──────────────────────────────
        right = tk.Frame(body, bg=COLOR_BG)
        right.pack(side="left", fill="both", expand=True)

        filt = tk.Frame(right, bg=COLOR_BG)
        filt.pack(fill="x", pady=(0, 8))
        self._solo_activos = tk.BooleanVar(value=True)
        tk.Checkbutton(filt, text=T("solo_activos","Solo préstamos activos"),
                       variable=self._solo_activos,
                       font=FONT_SMALL, bg=COLOR_BG, fg=COLOR_TEXT,
                       selectcolor=COLOR_CARD, activebackground=COLOR_BG,
                       command=self._cargar_tabla).pack(side="left")
        tk.Label(filt, text="  🔍", font=("Georgia", 12),
                 bg=COLOR_BG, fg=COLOR_DIM).pack(side="left")
        self._busq_var = tk.StringVar()
        self._busq_var.trace_add("write", lambda *_: self._cargar_tabla())
        tk.Entry(filt, textvariable=self._busq_var,
                 font=FONT_ENTRY, bg=COLOR_CARD2, fg=COLOR_TEXT,
                 insertbackground=COLOR_GOLD, relief="flat",
                 highlightthickness=1, highlightbackground=COLOR_GOLD_DIM
                 ).pack(side="left", fill="x", expand=True, ipady=5, padx=(4, 0))

        cols = ("ID", "Socio", "ISBN", "Título",
                "F. Préstamo", "F. Dev. est.", "Estado")
        ts = ttk.Style()
        ts.configure("Bib.Treeview",
                     background=COLOR_CARD2, foreground=COLOR_TEXT,
                     fieldbackground=COLOR_CARD2, rowheight=26,
                     font=("Georgia", 10))
        ts.configure("Bib.Treeview.Heading",
                     background=COLOR_CARD, foreground=COLOR_GOLD,
                     font=("Georgia", 9, "bold"), relief="flat")
        ts.map("Bib.Treeview", background=[("selected", COLOR_GOLD_DIM)])

        tf = tk.Frame(right, bg=COLOR_BG)
        tf.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                 style="Bib.Treeview", selectmode="browse")
        for col, w in zip(cols, [40, 130, 120, 170, 95, 110, 75]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=40)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._cargar_socios()
        self._cargar_libros()
        self._cargar_tabla()

    # ── Carga de combos ───────────────────────────────────────
    def _cargar_socios(self):
        """Carga todos los socios en el mapa y actualiza el combo."""
        self._socios_map = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT id_usuario, nombre FROM usuarios ORDER BY nombre")
            for id_u, nombre in cur.fetchall():
                label = f"{nombre}  (ID: {id_u})"
                self._socios_map[label] = id_u
            conn.close()
        except sqlite3.Error:
            pass
        self._socio_combo["values"] = list(self._socios_map.keys())

    def _cargar_libros(self, solo_disponibles=False):
        """Carga libros disponibles en el mapa y actualiza el combo."""
        self._libros_map = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            q = "SELECT isbn, titulo, autor FROM libros"
            if solo_disponibles:
                q += " WHERE estado = 'Disponible'"
            q += " ORDER BY titulo"
            cur.execute(q)
            for isbn, titulo, autor in cur.fetchall():
                label = f"{titulo}  —  {autor}  ({isbn})"
                self._libros_map[label] = isbn
            conn.close()
        except sqlite3.Error:
            pass
        self._libro_combo["values"] = list(self._libros_map.keys())

    def _filtrar_socios(self):
        """Filtra las opciones del combo de socios según lo escrito."""
        txt = self._socio_var.get().lower()
        filtrados = [k for k in self._socios_map if txt in k.lower()]
        self._socio_combo["values"] = filtrados
        if filtrados:
            self._socio_combo.event_generate("<<ComboboxSelected>>")
            self._socio_combo["values"] = filtrados  # mantener lista abierta

    def _filtrar_libros(self):
        """Filtra las opciones del combo de libros según lo escrito."""
        txt = self._libro_var.get().lower()
        filtrados = [k for k in self._libros_map if txt in k.lower()]
        self._libro_combo["values"] = filtrados

    def _resolver_ids(self):
        """
        Extrae id_usuario e isbn desde los combos.
        Acepta tanto selección de la lista como texto libre con ISBN/ID directo.
        Devuelve (id_usuario: int, isbn: str) o lanza ValueError.
        """
        socio_txt = self._socio_var.get().strip()
        libro_txt = self._libro_var.get().strip()

        if not socio_txt or not libro_txt:
            raise ValueError("Selecciona o escribe un socio y un libro.")

        # ── Resolver socio ──
        if socio_txt in self._socios_map:
            id_usuario = self._socios_map[socio_txt]
        else:
            # Intentar como ID numérico directo
            try:
                id_usuario = int(socio_txt)
            except ValueError:
                raise ValueError(
                    f"Socio no reconocido: '{socio_txt}'.\n"
                    "Selecciónalo de la lista o escribe su ID numérico.")

        # ── Resolver libro ──
        if libro_txt in self._libros_map:
            isbn = self._libros_map[libro_txt]
        else:
            # Intentar como ISBN directo
            isbn = libro_txt

        return id_usuario, isbn

    # ── Lógica de préstamo ────────────────────────────────────
    def _registrar_prestamo(self):
        try:
            id_usuario, isbn = self._resolver_ids()
        except ValueError as e:
            self._msg_prest.config(text=str(e), fg=COLOR_ERROR)
            return

        try:
            from secciones.biblioteca_sanciones import (
                leer_config, esta_sancionado, registrar_sancion)

            cfg         = leer_config(self.db_path)
            max_dias    = int(cfg.get("max_dias", 15))
            max_prest   = int(cfg.get("max_prestamos", 3))
            bloquear    = bool(cfg.get("bloquear_sancionados", 1))

            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()

            cur.execute("""
                SELECT id_usuario, nombre,
                       COALESCE(correo,''), COALESCE(telefono,'')
                FROM usuarios WHERE id_usuario = ?
            """, (id_usuario,))
            fila_u = cur.fetchone()
            if not fila_u:
                raise ValueError(f"No existe ningún socio con ID {id_usuario}.")
            usuario = Usuario.desde_fila(fila_u)

            # Bloqueo por sanción activa
            if bloquear and esta_sancionado(self.db_path, id_usuario):
                from secciones.biblioteca_sanciones import dias_suspension_restantes
                dias = dias_suspension_restantes(self.db_path, id_usuario)
                raise ValueError(
                    f"El socio '{usuario.nombre}' tiene una suspensión activa "
                    f"({dias} día(s) restante(s)).")

            # Límite de préstamos simultáneos
            cur.execute("""
                SELECT COUNT(*) FROM prestamos
                WHERE id_usuario = ? AND devuelto = 0
            """, (id_usuario,))
            activos = cur.fetchone()[0]
            if activos >= max_prest:
                raise ValueError(
                    f"El socio '{usuario.nombre}' ya tiene {activos} préstamo(s) activo(s) "
                    f"(máximo: {max_prest}).")

            cur.execute("""
                SELECT isbn, titulo, autor, estado FROM libros WHERE isbn = ?
            """, (isbn,))
            fila_l = cur.fetchone()
            if not fila_l:
                raise ValueError(f"No existe ningún libro con ISBN '{isbn}'.")
            libro = Libro.desde_fila(fila_l)

            usuario.tomar_prestado(libro)   # lanza ValueError si ya está prestado

            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            fecha_dev = (datetime.now() + timedelta(days=max_dias)).strftime("%Y-%m-%d")
            cur.execute("""
                INSERT INTO prestamos
                    (id_usuario, isbn, fecha_prestamo,
                     fecha_devolucion_estimada, devuelto)
                VALUES (?, ?, ?, ?, 0)
            """, (usuario.id_usuario, libro.isbn, fecha_hoy, fecha_dev))
            id_prestamo = cur.lastrowid
            cur.execute("UPDATE libros SET estado='Prestado' WHERE isbn=?",
                        (libro.isbn,))
            conn.commit()
            conn.close()

            try:
                ruta = generar_recibo(usuario, libro, id_prestamo)
                extra = f"\nRecibo: {os.path.basename(ruta)}"
            except IOError as e:
                extra = f"\n(Recibo no generado: {e})"

            self._msg_prest.config(
                text=f"✓ Préstamo de '{libro.titulo}' para '{usuario.nombre}'.{extra}",
                fg=COLOR_SUCCESS)
            self._socio_var.set("")
            self._libro_var.set("")
            self._cargar_libros()
            self._cargar_tabla()

        except ValueError as e:
            self._msg_prest.config(text=str(e), fg=COLOR_ERROR)
            try: conn.close()
            except: pass
        except sqlite3.Error as e:
            self._msg_prest.config(text=f"Error BD: {e}", fg=COLOR_ERROR)
            try: conn.close()
            except: pass

    def _registrar_devolucion(self):
        sel = self.tree.selection()
        if not sel:
            self._msg_dev.config(
                text="Selecciona un préstamo activo de la tabla.", fg=COLOR_ERROR)
            return

        vals        = self.tree.item(sel[0], "values")
        id_prestamo = vals[0]
        if vals[6] == "Devuelto":
            self._msg_dev.config(text="Este préstamo ya fue devuelto.", fg=COLOR_ERROR)
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("""
                SELECT p.id_usuario, p.isbn,
                       u.nombre, COALESCE(u.correo,''), COALESCE(u.telefono,''),
                       l.titulo, l.autor
                FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                JOIN libros   l ON p.isbn = l.isbn
                WHERE p.id_prestamo = ?
            """, (id_prestamo,))
            row = cur.fetchone()
            if not row:
                raise ValueError("No se encontró el préstamo.")

            id_u, isbn, nombre_u, correo_u, tel_u, titulo_l, autor_l = row
            usuario = Usuario(nombre=nombre_u, id_usuario=id_u,
                              correo=correo_u, telefono=tel_u)
            libro   = Libro(titulo=titulo_l, autor=autor_l,
                            isbn=isbn, estado="Prestado")
            usuario.libros_prestados.append(libro)
            usuario.devolver(isbn)

            fecha_real = datetime.now().strftime("%Y-%m-%d")
            cur.execute("""
                SELECT fecha_devolucion_estimada FROM prestamos
                WHERE id_prestamo = ?
            """, (id_prestamo,))
            fila_est = cur.fetchone()
            fecha_estimada = fila_est[0] if fila_est else fecha_real

            cur.execute("""
                UPDATE prestamos
                SET devuelto = 1, fecha_devolucion_real = ?
                WHERE id_prestamo = ?
            """, (fecha_real, id_prestamo))
            cur.execute("UPDATE libros SET estado='Disponible' WHERE isbn=?", (isbn,))
            conn.commit()
            conn.close()

            # Calcular retraso y registrar sanción si procede
            from secciones.biblioteca_sanciones import (
                leer_config, calcular_dias_retraso, registrar_sancion)
            cfg          = leer_config(self.db_path)
            factor       = int(cfg.get("dias_por_dia_retraso", 2))
            dias_retraso = calcular_dias_retraso(fecha_estimada)
            msg_extra    = ""
            if dias_retraso > 0:
                dias_susp = registrar_sancion(
                    self.db_path, int(id_prestamo), id_u, dias_retraso, factor)
                msg_extra = (f"  ·  Retraso: {dias_retraso}d "
                             f"→ suspensión de {dias_susp}d aplicada.")

            # Sellar el PDF del recibo
            estampar_devolucion_en_pdf(int(id_prestamo), fecha_real, fecha_estimada)

            self._msg_dev.config(
                text=f"✓ Devolución de '{titulo_l}' registrada.{msg_extra}",
                fg=COLOR_SUCCESS if not msg_extra else COLOR_ERROR)
            self._cargar_libros()
            self._cargar_tabla()

        except ValueError as e:
            self._msg_dev.config(text=str(e), fg=COLOR_ERROR)
            try: conn.close()
            except: pass
        except sqlite3.Error as e:
            self._msg_dev.config(text=f"Error BD: {e}", fg=COLOR_ERROR)
            try: conn.close()
            except: pass

    def _cargar_tabla(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        filtro = f"%{self._busq_var.get().strip()}%"
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            q = """
                SELECT p.id_prestamo, u.nombre, l.isbn, l.titulo,
                       p.fecha_prestamo, p.fecha_devolucion_estimada,
                       CASE p.devuelto WHEN 1 THEN 'Devuelto' ELSE 'Activo' END
                FROM prestamos p
                JOIN usuarios u ON p.id_usuario = u.id_usuario
                JOIN libros   l ON p.isbn = l.isbn
                WHERE (u.nombre LIKE ? OR l.titulo LIKE ? OR l.isbn LIKE ?)
            """
            params = [filtro, filtro, filtro]
            if self._solo_activos.get():
                q += " AND p.devuelto = 0"
            q += " ORDER BY p.id_prestamo DESC"
            cur.execute(q, params)
            for fila in cur.fetchall():
                tag = "devuelto" if fila[6] == "Devuelto" else "activo"
                self.tree.insert("", "end", values=fila, tags=(tag,))
            self.tree.tag_configure("activo",   foreground=COLOR_GOLD)
            self.tree.tag_configure("devuelto", foreground=COLOR_DIM)
            conn.close()
        except sqlite3.Error as e:
            self._msg_prest.config(text=f"Error BD: {e}", fg=COLOR_ERROR)

    def mostrar(self):
        self.frame.pack(fill="both", expand=True)
        self._cargar_socios()
        self._cargar_libros()
        self._cargar_tabla()

    def ocultar(self):
        self.frame.pack_forget()