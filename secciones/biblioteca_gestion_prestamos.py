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


def generar_recibo(usuario: Usuario, libro: Libro, id_prestamo: int) -> str:
    try:
        os.makedirs(RECIBOS_DIR, exist_ok=True)
        fecha_hoy        = datetime.now()
        fecha_devolucion = fecha_hoy + timedelta(days=15)
        slug  = _nombre_limpio(usuario.nombre)
        fecha_slug = fecha_hoy.strftime("%Y%m%d_%H%M")
        nombre_archivo = f"recibo_{id_prestamo:04d}_{usuario.id_usuario}_{slug}_{fecha_slug}.txt"
        ruta  = os.path.join(RECIBOS_DIR, nombre_archivo)

        W = 56
        borde_d = "╔" + "═" * (W-2) + "╗"
        borde_f = "╚" + "═" * (W-2) + "╝"
        borde_m = "╠" + "═" * (W-2) + "╣"
        sep     = "║" + " " * (W-2) + "║"

        def fila(txt, ancho=W):
            pad = ancho - 4 - len(txt)
            return f"║  {txt}{chr(32)*max(pad,0)}  ║"

        def kv(clave, valor, ancho=W):
            linea = f"{clave:<18}{valor}"
            pad = ancho - 4 - len(linea)
            return f"║  {linea}{chr(32)*max(pad,0)}  ║"

        def titulo_sec(txt, ancho=W):
            inner = f"  ▸  {txt}  "
            pad = ancho - 2 - len(inner)
            return f"╠{inner}{"═"*max(pad,0)}╣"

        contenido = "\n".join([
            borde_d,
            fila(""),
            fila("  EL ARCHIVO DE LOS MUNDOS"),
            fila("  ✦  COMPROBANTE DE PRÉSTAMO  ✦"),
            fila(""),
            borde_m,
            fila(""),
            kv("  Nº Préstamo:", f"#{id_prestamo:04d}"),
            kv("  Fecha emisión:", fecha_hoy.strftime("%d/%m/%Y  %H:%M")),
            fila(""),
            titulo_sec("SOCIO"),
            fila(""),
            kv("  ID:", str(usuario.id_usuario)),
            kv("  Nombre:", usuario.nombre),
            kv("  Correo:", usuario.correo or "—"),
            kv("  Teléfono:", usuario.telefono or "—"),
            fila(""),
            titulo_sec("LIBRO PRESTADO"),
            fila(""),
            kv("  ISBN:", libro.isbn),
            kv("  Título:", libro.titulo[:30]),
            kv("  Autor:", libro.autor[:30]),
            fila(""),
            titulo_sec("DEVOLUCIÓN"),
            fila(""),
            kv("  Fecha límite:", fecha_devolucion.strftime("%d/%m/%Y")),
            kv("  Plazo:", "15 días naturales"),
            fila(""),
            borde_m,
            fila(""),
            fila("  Conserve este comprobante."),
            fila(""),
            borde_f,
        ]) + "\n"

        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        return ruta
    except IOError as e:
        raise IOError(f"Error al crear el recibo: {e}")


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

            cur.execute("""
                SELECT isbn, titulo, autor, estado FROM libros WHERE isbn = ?
            """, (isbn,))
            fila_l = cur.fetchone()
            if not fila_l:
                raise ValueError(f"No existe ningún libro con ISBN '{isbn}'.")
            libro = Libro.desde_fila(fila_l)

            usuario.tomar_prestado(libro)   # lanza ValueError si ya está prestado

            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            fecha_dev = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
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

            cur.execute("UPDATE prestamos SET devuelto=1 WHERE id_prestamo=?",
                        (id_prestamo,))
            cur.execute("UPDATE libros SET estado='Disponible' WHERE isbn=?", (isbn,))
            conn.commit()
            conn.close()

            self._msg_dev.config(
                text=f"✓ Devolución de '{titulo_l}' registrada.", fg=COLOR_SUCCESS)
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