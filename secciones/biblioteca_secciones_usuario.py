"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Secciones disponibles para usuarios con rol 'normal':
                 - SeccionMiCatalogo : Vista de solo lectura del catálogo.
                 - SeccionMisPrestamos: Vista y solicitud de préstamos propios.
Autor/a:         Luis Villegas Rivera
Fecha:           2026-03-09
Clases principales:
    - SeccionMiCatalogo   : Catálogo de libros (solo lectura).
    - SeccionMisPrestamos : Préstamos activos del usuario en sesión.
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime, timedelta

from secciones.biblioteca_gestion_libros import (
    Libro, aplicar_tema,
    COLOR_BG, COLOR_CARD, COLOR_CARD2, COLOR_GOLD, COLOR_GOLD_DIM,
    COLOR_TEXT, COLOR_DIM, COLOR_ERROR, COLOR_SUCCESS,
    FONT_TITLE, FONT_LABEL, FONT_ENTRY, FONT_SMALL, FONT_BTN,
)
from secciones.biblioteca_ajustes import T
from secciones.biblioteca_gestion_usuarios  import Usuario
from secciones.biblioteca_gestion_prestamos import generar_recibo


# ═══════════════════════════════════════════
# SECCIÓN: Catálogo (solo lectura)
# ═══════════════════════════════════════════
class SeccionMiCatalogo:
    """Vista de solo lectura del catálogo para usuarios normales."""

    def __init__(self, parent: tk.Widget, db_path: str, usuario: str):
        aplicar_tema()
        self.db_path = db_path
        self.usuario = usuario
        self.frame   = tk.Frame(parent, bg=COLOR_BG)
        self._build_ui()

    def _build_ui(self):
        # Cabecera
        cab = tk.Frame(self.frame, bg=COLOR_CARD, height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text=T("cab_catalogo","📚  Catálogo"),
                 font=FONT_TITLE, bg=COLOR_CARD, fg=COLOR_GOLD
                 ).pack(side="left", padx=24, pady=12)
        tk.Label(cab, text=T("solo_lectura","(solo lectura)"),
                 font=("Georgia", 9, "italic"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(side="left", pady=12)

        tk.Frame(self.frame, height=1, bg=COLOR_GOLD_DIM).pack(fill="x")

        body = tk.Frame(self.frame, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Búsqueda
        busq_frame = tk.Frame(body, bg=COLOR_BG)
        busq_frame.pack(fill="x", pady=(0, 10))
        tk.Label(busq_frame, text="🔍", font=("Georgia", 12),
                 bg=COLOR_BG, fg=COLOR_DIM).pack(side="left")
        self._busq_var = tk.StringVar()
        self._busq_var.trace_add("write", lambda *_: self._cargar_tabla())
        tk.Entry(busq_frame, textvariable=self._busq_var,
                 font=FONT_ENTRY, bg=COLOR_CARD2, fg=COLOR_TEXT,
                 insertbackground=COLOR_GOLD, relief="flat",
                 highlightthickness=1, highlightbackground=COLOR_GOLD_DIM
                 ).pack(side="left", fill="x", expand=True, ipady=5, padx=(6, 0))

        # Filtro disponibilidad
        self._solo_disp = tk.BooleanVar(value=False)
        tk.Checkbutton(busq_frame, text="  Solo disponibles",
                       variable=self._solo_disp,
                       font=FONT_SMALL, bg=COLOR_BG, fg=COLOR_TEXT,
                       selectcolor=COLOR_CARD, activebackground=COLOR_BG,
                       command=self._cargar_tabla
                       ).pack(side="left", padx=(14, 0))

        # Tabla
        cols = ("ISBN", "Título", "Autor", "Categoría", "Estado")
        style = ttk.Style()
        style.configure("Bib.Treeview",
                        background=COLOR_CARD2, foreground=COLOR_TEXT,
                        fieldbackground=COLOR_CARD2, rowheight=26,
                        font=("Georgia", 10))
        style.configure("Bib.Treeview.Heading",
                        background=COLOR_CARD, foreground=COLOR_GOLD,
                        font=("Georgia", 9, "bold"), relief="flat")
        style.map("Bib.Treeview", background=[("selected", COLOR_GOLD_DIM)])

        tree_f = tk.Frame(body, bg=COLOR_BG)
        tree_f.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_f, columns=cols, show="headings",
                                 style="Bib.Treeview", selectmode="browse")
        for col, w in zip(cols, [130, 260, 180, 120, 100]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=60)
        vsb = ttk.Scrollbar(tree_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._cargar_tabla()

    def _cargar_tabla(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        filtro = f"%{self._busq_var.get().strip()}%"
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            q = """
                SELECT l.isbn, l.titulo, l.autor,
                       COALESCE(c.nombre_categoria,'—'), l.estado
                FROM libros l
                LEFT JOIN categorias c ON l.id_categoria = c.id_categoria
                WHERE (l.titulo LIKE ? OR l.autor LIKE ? OR l.isbn LIKE ?)
            """
            params = [filtro, filtro, filtro]
            if self._solo_disp.get():
                q += " AND l.estado = 'Disponible'"
            q += " ORDER BY l.titulo"
            cur.execute(q, params)
            for fila in cur.fetchall():
                tag = "prestado" if fila[4] == "Prestado" else ""
                self.tree.insert("", "end", values=fila, tags=(tag,))
            self.tree.tag_configure("prestado", foreground="#c47a6a")
            conn.close()
        except sqlite3.Error:
            pass

    def mostrar(self):
        self.frame.pack(fill="both", expand=True)
        self._cargar_tabla()

    def ocultar(self):
        self.frame.pack_forget()


# ═══════════════════════════════════════════
# SECCIÓN: Mis Préstamos (usuario normal)
# ═══════════════════════════════════════════
class SeccionMisPrestamos:
    """
    Permite al usuario normal ver sus préstamos activos
    y solicitar nuevos préstamos.
    """

    def __init__(self, parent: tk.Widget, db_path: str, usuario: str):
        aplicar_tema()
        self.db_path = db_path
        self.usuario = usuario
        self.frame   = tk.Frame(parent, bg=COLOR_BG)
        self._id_usuario = None
        self._cargar_id_usuario()
        self._build_ui()

    def _cargar_id_usuario(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT id_usuario FROM usuarios WHERE nombre = ?",
                        (self.usuario,))
            row = cur.fetchone()
            self._id_usuario = row[0] if row else None
            conn.close()
        except sqlite3.Error:
            self._id_usuario = None

    def _build_ui(self):
        # Cabecera
        cab = tk.Frame(self.frame, bg=COLOR_CARD, height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text=T("cab_misprestamos","🔖  Mis Préstamos"),
                 font=FONT_TITLE, bg=COLOR_CARD, fg=COLOR_GOLD
                 ).pack(side="left", padx=24, pady=12)

        tk.Frame(self.frame, height=1, bg=COLOR_GOLD_DIM).pack(fill="x")

        body = tk.Frame(self.frame, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Panel izquierdo: solicitar préstamo ──
        left = tk.Frame(body, bg=COLOR_CARD, width=280,
                        highlightthickness=1, highlightbackground=COLOR_GOLD_DIM)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)

        tk.Label(left, text=T("solicitar_prestamo","SOLICITAR PRÉSTAMO"),
                 font=("Georgia", 9, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Frame(left, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=20)

        from tkinter import ttk
        from secciones.biblioteca_gestion_prestamos import _aplicar_estilo_combo
        _aplicar_estilo_combo()

        tk.Label(left, text="Libro", font=FONT_SMALL,
                 bg=COLOR_CARD, fg=COLOR_DIM).pack(anchor="w", padx=20, pady=(12, 0))

        # Mapa label → isbn
        self._libros_map: dict = {}
        self._libro_var = tk.StringVar()
        self._libro_combo = ttk.Combobox(
            left, textvariable=self._libro_var,
            font=("Georgia", 11), style="Dark.TCombobox")
        self._libro_combo.pack(fill="x", padx=20, ipady=4, pady=(3, 0))
        self._libro_combo.bind("<KeyRelease>",        lambda _: self._filtrar_libros())
        self._libro_combo.bind("<<ComboboxSelected>>", lambda _: self._libro_combo.selection_clear())
        self._cargar_libros_combo()

        self._msg = tk.Label(left, text="", font=("Georgia", 9, "italic"),
                             bg=COLOR_CARD, fg=COLOR_ERROR, wraplength=240)
        self._msg.pack(padx=20, pady=(10, 0), anchor="w")

        btn = tk.Button(left, text=T("btn_solicitar","＋  Solicitar préstamo"),
                        font=FONT_BTN, bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
                        activebackground=COLOR_GOLD, activeforeground="#000",
                        relief="flat", bd=0, cursor="hand2",
                        command=self._solicitar)
        btn.pack(fill="x", padx=20, pady=(12, 0), ipady=8)
        btn.bind("<Enter>", lambda _: btn.config(bg=COLOR_GOLD, fg="#000"))
        btn.bind("<Leave>", lambda _: btn.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))

        # Info de usuario
        tk.Frame(left, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=20, pady=(20, 8))
        self._info_lbl = tk.Label(
            left, text="", font=("Georgia", 9, "italic"),
            bg=COLOR_CARD, fg=COLOR_DIM, wraplength=240)
        self._info_lbl.pack(padx=20, anchor="w")
        self._actualizar_info()

        # ── Panel derecho: tabla préstamos propios ──
        right = tk.Frame(body, bg=COLOR_BG)
        right.pack(side="left", fill="both", expand=True)

        tk.Label(right, text=T("mis_activos","Mis préstamos activos"),
                 font=("Georgia", 10, "bold"), bg=COLOR_BG, fg=COLOR_GOLD
                 ).pack(anchor="w", pady=(0, 8))

        cols = ("ID", "ISBN", "Título", "F. Préstamo", "Devolución estimada")
        style = ttk.Style()
        style.configure("Bib.Treeview",
                        background=COLOR_CARD2, foreground=COLOR_TEXT,
                        fieldbackground=COLOR_CARD2, rowheight=26,
                        font=("Georgia", 10))
        style.configure("Bib.Treeview.Heading",
                        background=COLOR_CARD, foreground=COLOR_GOLD,
                        font=("Georgia", 9, "bold"), relief="flat")
        style.map("Bib.Treeview", background=[("selected", COLOR_GOLD_DIM)])

        tree_f = tk.Frame(right, bg=COLOR_BG)
        tree_f.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_f, columns=cols, show="headings",
                                 style="Bib.Treeview", selectmode="browse")
        for col, w in zip(cols, [50, 130, 240, 110, 130]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=40)
        vsb = ttk.Scrollbar(tree_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._cargar_tabla()

    def _actualizar_info(self):
        if self._id_usuario:
            self._info_lbl.config(
                text=f"Tu ID de socio: {self._id_usuario}\n"
                     "Usa el ISBN del catálogo para solicitar un préstamo.")

    # ── Métodos del combo de libros ───────────────────────────
    def _cargar_libros_combo(self):
        """Carga libros disponibles en el combo."""
        self._libros_map = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("""
                SELECT isbn, titulo, autor FROM libros
                WHERE estado = 'Disponible' ORDER BY titulo
            """)
            for isbn, titulo, autor in cur.fetchall():
                label = f"{titulo}  —  {autor}  ({isbn})"
                self._libros_map[label] = isbn
            conn.close()
        except Exception:
            pass
        self._libro_combo["values"] = list(self._libros_map.keys())

    def _filtrar_libros(self):
        txt = self._libro_var.get().lower()
        filtrados = [k for k in self._libros_map if txt in k.lower()]
        self._libro_combo["values"] = filtrados

    # ── Lógica de préstamo ────────────────────────────────────
    def _cargar_tabla(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        if not self._id_usuario:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("""
                SELECT p.id_prestamo, l.isbn, l.titulo,
                       p.fecha_prestamo, p.fecha_devolucion_estimada
                FROM prestamos p
                JOIN libros l ON p.isbn = l.isbn
                WHERE p.id_usuario = ? AND p.devuelto = 0
                ORDER BY p.id_prestamo DESC
            """, (self._id_usuario,))
            for fila in cur.fetchall():
                self.tree.insert("", "end", values=fila)
            conn.close()
        except sqlite3.Error:
            pass

    def _solicitar(self):
        """
        Solicita un préstamo para el usuario en sesión.
        Usa las clases Libro y Usuario con toda la lógica de negocio.
        """
        libro_txt = self._libro_var.get().strip()
        if not libro_txt:
            self._msg.config(text="Selecciona o escribe un libro.", fg=COLOR_ERROR)
            return
        # Resolver ISBN desde selección o texto directo
        raw_isbn = self._libros_map.get(libro_txt, libro_txt)
        if not self._id_usuario:
            self._msg.config(text="No se pudo identificar tu cuenta.", fg=COLOR_ERROR)
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()

            # Cargar usuario
            cur.execute("""
                SELECT id_usuario, nombre,
                       COALESCE(correo,''), COALESCE(telefono,'')
                FROM usuarios WHERE id_usuario = ?
            """, (self._id_usuario,))
            fila_u = cur.fetchone()
            if not fila_u:
                raise ValueError("No se encontró tu cuenta en la base de datos.")
            usuario = Usuario.desde_fila(fila_u)

            # Cargar libro
            cur.execute("""
                SELECT isbn, titulo, autor, estado FROM libros WHERE isbn = ?
            """, (raw_isbn,))
            fila_l = cur.fetchone()
            if not fila_l:
                raise ValueError(f"No existe ningún libro con ISBN '{raw_isbn}'.")
            libro = Libro.desde_fila(fila_l)

            # Error lógico: libro ya prestado
            usuario.tomar_prestado(libro)

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

            # Generar recibo
            try:
                ruta = generar_recibo(usuario, libro, id_prestamo)
                extra = f"\nRecibo: {__import__('os').path.basename(ruta)}"
            except IOError as e:
                extra = f"\n(Recibo no generado: {e})"

            self._msg.config(
                text=f"✓ Préstamo de '{libro.titulo}' registrado.{extra}",
                fg=COLOR_SUCCESS)
            self._libro_var.set("")
            self._cargar_libros_combo()
            self._cargar_tabla()

        except ValueError as e:
            self._msg.config(text=str(e), fg=COLOR_ERROR)
            try: conn.close()
            except: pass
        except sqlite3.Error as e:
            self._msg.config(text=f"Error BD: {e}", fg=COLOR_ERROR)
            try: conn.close()
            except: pass

    def mostrar(self):
        self.frame.pack(fill="both", expand=True)
        self._cargar_tabla()

    def ocultar(self):
        self.frame.pack_forget()