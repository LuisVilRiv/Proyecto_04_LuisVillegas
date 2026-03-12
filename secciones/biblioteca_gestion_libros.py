"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Módulo de gestión del catálogo de libros. Define la clase Libro
                 y proporciona la interfaz gráfica para agregar, eliminar y
                 consultar el catálogo completo conectado a la base de datos SQLite.
Autor/a:         Luis Villegas
Fecha:           2026-03-09
Clases principales:
    - Libro          : Entidad que representa un ejemplar de la biblioteca.
    - SeccionLibros  : Panel tkinter para la gestión visual del catálogo.
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
import os

# ─────────────────────────────────────────
# Constantes de estilo — se actualizan con
# aplicar_tema() antes de construir cada UI
# ─────────────────────────────────────────
COLOR_BG       = "#0e0d12"
COLOR_CARD     = "#13121a"
COLOR_CARD2    = "#1a1820"
COLOR_GOLD     = "#c9a84c"
COLOR_GOLD_DIM = "#7a5f28"
COLOR_TEXT     = "#e8dfc8"
COLOR_DIM      = "#8a7f6a"
COLOR_ERROR    = "#c45a3a"
COLOR_SUCCESS  = "#4a8c5a"
FONT_TITLE     = ("Georgia", 16, "bold")
FONT_LABEL     = ("Georgia", 10)
FONT_ENTRY     = ("Georgia", 12)
FONT_SMALL     = ("Georgia", 9)
FONT_BTN       = ("Georgia", 10, "bold")

# ─────────────────────────────────────────
# Traducciones de UI — actualizado por aplicar_tema()
# ─────────────────────────────────────────
TEXTOS = {
    "es": {
        # Libros
        "libros_titulo":      "📚  Catálogo de Libros",
        "libros_agregar":     "AÑADIR LIBRO",
        "libros_isbn":        "ISBN",
        "libros_titulo_lbl":  "Título",
        "libros_autor":       "Autor",
        "libros_categ":       "Categoría (id)",
        "libros_editorial":   "Editorial (id)",
        "libros_fecha":       "Fecha publicación",
        "libros_btn_add":     "＋  Agregar libro",
        "libros_btn_del":     "✕  Eliminar seleccionado",
        "libros_buscar":      "",
        "libros_solo_disp":   "Solo disponibles",
        "col_isbn":           "ISBN",
        "col_titulo":         "Título",
        "col_autor":          "Autor",
        "col_categ":          "Categoría",
        "col_editorial":      "Editorial",
        "col_estado":         "Estado",
        "msg_campos_req":     "ISBN, título y autor son obligatorios.",
        "msg_id_numerico":    "Categoría y editorial deben ser números (id).",
        "msg_isbn_existe":    "El ISBN '{isbn}' ya existe en el catálogo.",
        "msg_prestamos_act":  "'{titulo}' tiene préstamos activos. Devuélvelo primero.",
        "msg_sel_tabla":      "Selecciona un libro de la tabla.",
        # Usuarios
        "socios_titulo":      "👤  Gestión de Socios",
        "socios_detalle":     "DETALLE DEL SOCIO",
        "socios_id":          "ID",
        "socios_nombre":      "Nombre",
        "socios_correo":      "Correo",
        "socios_telefono":    "Teléfono",
        "socios_prestamos":   "Préstamos activos",
        "socios_btn_del":     "✕  Eliminar socio",
        "socios_col_id":      "ID",
        "socios_col_nombre":  "Nombre",
        "socios_col_correo":  "Correo",
        "socios_col_tel":     "Teléfono",
        "socios_col_prest":   "Préstamos activos",
        "socios_prestamos_activos": "'{nombre}' tiene {n} préstamo(s) activo(s).\nGestiona las devoluciones primero.",
        "socios_sel":         "Selecciona un socio de la tabla.",
        # Préstamos
        "prest_titulo":       "🔖  Préstamos y Devoluciones",
        "prest_nuevo":        "NUEVO PRÉSTAMO",
        "prest_socio":        "Socio",
        "prest_libro":        "Libro",
        "prest_btn_reg":      "＋  Registrar préstamo",
        "prest_devolucion":   "DEVOLUCIÓN",
        "prest_sel_tabla":    "Selecciona un préstamo activo en la tabla",
        "prest_btn_dev":      "↩  Registrar devolución",
        "prest_solo_activos": "Solo préstamos activos",
        "prest_col_id":       "ID",
        "prest_col_socio":    "Socio",
        "prest_col_isbn":     "ISBN",
        "prest_col_titulo":   "Título",
        "prest_col_fprest":   "F. Préstamo",
        "prest_col_fdev":     "F. Dev. est.",
        "prest_col_estado":   "Estado",
        "prest_sel_req":      "Selecciona o escribe un socio y un libro.",
        "prest_ya_devuelto":  "Este préstamo ya fue devuelto.",
        "prest_sel_activo":   "Selecciona un préstamo activo de la tabla.",
        # Catálogo usuario
        "cat_titulo":         "📚  Catálogo",
        "cat_solo_lectura":   "(solo lectura)",
        "cat_solo_disp":      "  Solo disponibles",
        # Mis préstamos
        "misprest_titulo":    "🔖  Mis Préstamos",
        "misprest_solicitar": "SOLICITAR PRÉSTAMO",
        "misprest_libro":     "Libro",
        "misprest_btn":       "＋  Solicitar préstamo",
        "misprest_activos":   "Mis préstamos activos",
        "misprest_col_id":    "ID",
        "misprest_col_isbn":  "ISBN",
        "misprest_col_titulo":"Título",
        "misprest_col_fprest":"F. Préstamo",
        "misprest_col_fdev":  "Devolución estimada",
    },
    "en": {
        # Books
        "libros_titulo":      "📚  Book Catalogue",
        "libros_agregar":     "ADD BOOK",
        "libros_isbn":        "ISBN",
        "libros_titulo_lbl":  "Title",
        "libros_autor":       "Author",
        "libros_categ":       "Category (id)",
        "libros_editorial":   "Publisher (id)",
        "libros_fecha":       "Publication date",
        "libros_btn_add":     "＋  Add book",
        "libros_btn_del":     "✕  Delete selected",
        "libros_buscar":      "",
        "libros_solo_disp":   "Available only",
        "col_isbn":           "ISBN",
        "col_titulo":         "Title",
        "col_autor":          "Author",
        "col_categ":          "Category",
        "col_editorial":      "Publisher",
        "col_estado":         "Status",
        "msg_campos_req":     "ISBN, title and author are required.",
        "msg_id_numerico":    "Category and publisher must be numeric ids.",
        "msg_isbn_existe":    "ISBN '{isbn}' already exists in the catalogue.",
        "msg_prestamos_act":  "'{titulo}' has active loans. Return it first.",
        "msg_sel_tabla":      "Select a book from the table.",
        # Members
        "socios_titulo":      "👤  Member Management",
        "socios_detalle":     "MEMBER DETAIL",
        "socios_id":          "ID",
        "socios_nombre":      "Name",
        "socios_correo":      "Email",
        "socios_telefono":    "Phone",
        "socios_prestamos":   "Active loans",
        "socios_btn_del":     "✕  Delete member",
        "socios_col_id":      "ID",
        "socios_col_nombre":  "Name",
        "socios_col_correo":  "Email",
        "socios_col_tel":     "Phone",
        "socios_col_prest":   "Active loans",
        "socios_prestamos_activos": "'{nombre}' has {n} active loan(s).\nHandle returns first.",
        "socios_sel":         "Select a member from the table.",
        # Loans
        "prest_titulo":       "🔖  Loans & Returns",
        "prest_nuevo":        "NEW LOAN",
        "prest_socio":        "Member",
        "prest_libro":        "Book",
        "prest_btn_reg":      "＋  Register loan",
        "prest_devolucion":   "RETURN",
        "prest_sel_tabla":    "Select an active loan from the table",
        "prest_btn_dev":      "↩  Register return",
        "prest_solo_activos": "Active loans only",
        "prest_col_id":       "ID",
        "prest_col_socio":    "Member",
        "prest_col_isbn":     "ISBN",
        "prest_col_titulo":   "Title",
        "prest_col_fprest":   "Loan date",
        "prest_col_fdev":     "Est. return",
        "prest_col_estado":   "Status",
        "prest_sel_req":      "Select or type a member and a book.",
        "prest_ya_devuelto":  "This loan has already been returned.",
        "prest_sel_activo":   "Select an active loan from the table.",
        # Catalogue (user)
        "cat_titulo":         "📚  Catalogue",
        "cat_solo_lectura":   "(read only)",
        "cat_solo_disp":      "  Available only",
        # My loans
        "misprest_titulo":    "🔖  My Loans",
        "misprest_solicitar": "REQUEST A LOAN",
        "misprest_libro":     "Book",
        "misprest_btn":       "＋  Request loan",
        "misprest_activos":   "My active loans",
        "misprest_col_id":    "ID",
        "misprest_col_isbn":  "ISBN",
        "misprest_col_titulo":"Title",
        "misprest_col_fprest":"Loan date",
        "misprest_col_fdev":  "Estimated return",
    },
}

# Alias activo — se actualiza con aplicar_tema()
TX = TEXTOS["es"]



def aplicar_tema():
    """
    Actualiza las constantes de color y fuente en TODOS los módulos
    de secciones, para que los widgets construidos después usen el tema activo.
    Usa globals() de cada módulo para sobrescribir las copias locales.
    """
    try:
        from secciones.biblioteca_ajustes import ConfigApp, T
        c = ConfigApp.colores()
        f = ConfigApp.fuentes()
    except Exception:
        return  # Sin ConfigApp disponible, mantener defaults

    nuevos = {
        "COLOR_BG":       c["bg"],
        "COLOR_CARD":     c["card"],
        "COLOR_CARD2":    c["card2"],
        "COLOR_GOLD":     c["acento"],
        "COLOR_GOLD_DIM": c["acento_dim"],
        "COLOR_TEXT":     c["text"],
        "COLOR_DIM":      c["dim"],
        "COLOR_ERROR":    c["error"],
        "COLOR_SUCCESS":  c["success"],
        "FONT_TITLE":     ("Georgia", f["titulo"], "bold"),
        "FONT_LABEL":     ("Georgia", f["cuerpo"]),
        "FONT_ENTRY":     ("Georgia", f["entry"]),
        "FONT_SMALL":     ("Georgia", f["small"]),
        "FONT_BTN":       ("Georgia", f["btn"], "bold"),
    }

    # Lista de módulos que exportan estas constantes
    import sys
    idioma = ConfigApp.get("idioma") or "es"
    modulos = [
        "secciones.biblioteca_gestion_libros",
        "secciones.biblioteca_gestion_usuarios",
        "secciones.biblioteca_gestion_prestamos",
        "secciones.biblioteca_secciones_usuario",
        "secciones.biblioteca_sanciones",
        "secciones.biblioteca_facturas",
        "secciones.biblioteca_calendario",
    ]
    for nombre in modulos:
        mod = sys.modules.get(nombre)
        if mod:
            for k, v in nuevos.items():
                if hasattr(mod, k):
                    setattr(mod, k, v)
            # Actualizar alias TX con el idioma activo
            if hasattr(mod, "TEXTOS") and hasattr(mod, "TX"):
                tx_nuevo = mod.TEXTOS.get(idioma, mod.TEXTOS["es"])
                setattr(mod, "TX", tx_nuevo)


# ═══════════════════════════════════════════
# CLASE LIBRO  (requisito POO del proyecto)
# ═══════════════════════════════════════════
class Libro:
    """
    Representa un ejemplar de la biblioteca.

    Atributos
    ---------
    titulo  : str   — Título del libro.
    autor   : str   — Autor o autores.
    isbn    : str   — Identificador ISBN único.
    estado  : str   — "Disponible" | "Prestado".
    """

    def __init__(self, titulo: str, autor: str, isbn: str,
                 estado: str = "Disponible"):
        self.titulo = titulo
        self.autor  = autor
        self.isbn   = str(isbn)
        self.estado = estado

    # ── Cambio de estado ──────────────────
    def marcar_prestado(self) -> None:
        """Cambia el estado a 'Prestado'."""
        if self.estado == "Prestado":
            raise ValueError(f"El libro '{self.titulo}' ya está prestado.")
        self.estado = "Prestado"

    def marcar_disponible(self) -> None:
        """Cambia el estado a 'Disponible'."""
        self.estado = "Disponible"

    def esta_disponible(self) -> bool:
        return self.estado == "Disponible"

    # ── Representación ────────────────────
    def __str__(self) -> str:
        return (f"[{self.isbn}] {self.titulo} — {self.autor} "
                f"({self.estado})")

    def __repr__(self) -> str:
        return (f"Libro(titulo={self.titulo!r}, autor={self.autor!r}, "
                f"isbn={self.isbn!r}, estado={self.estado!r})")

    # ── Serialización desde/hacia BD ──────
    @classmethod
    def desde_fila(cls, fila: tuple) -> "Libro":
        """Crea un Libro a partir de una fila (isbn, titulo, autor, estado)."""
        isbn, titulo, autor, estado = fila
        return cls(titulo=titulo, autor=autor, isbn=isbn, estado=estado)


# ═══════════════════════════════════════════
# SECCIÓN TKINTER — Gestión de Libros
# ═══════════════════════════════════════════
class SeccionLibros:
    """
    Panel de gestión del catálogo de libros.
    Permite agregar, eliminar y consultar libros usando la clase Libro.
    """

    def __init__(self, parent: tk.Widget, db_path: str, usuario: str):
        aplicar_tema()
        self.db_path = db_path
        self.usuario = usuario

        self.frame = tk.Frame(parent, bg=COLOR_BG)
        self._build_ui()

    # ── Construcción de UI ────────────────
    def _build_ui(self):
        # Cabecera
        cab = tk.Frame(self.frame, bg=COLOR_CARD, height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text=TX["libros_titulo"],
                 font=FONT_TITLE, bg=COLOR_CARD, fg=COLOR_GOLD
                 ).pack(side="left", padx=24, pady=12)

        tk.Frame(self.frame, height=1, bg=COLOR_GOLD_DIM).pack(fill="x")

        # Cuerpo principal
        body = tk.Frame(self.frame, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Panel izquierdo: formulario ──
        left = tk.Frame(body, bg=COLOR_CARD, width=300,
                        highlightthickness=1, highlightbackground=COLOR_GOLD_DIM)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)

        tk.Label(left, text=TX["libros_agregar"],
                 font=("Georgia", 9, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Frame(left, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=20)

        self._campos_form = {}
        campos = [
            ("isbn",    TX["libros_isbn"]),
            ("titulo",  TX["libros_titulo_lbl"]),
            ("autor",   TX["libros_autor"]),
            ("categ",   TX["libros_categ"]),
            ("editorial", TX["libros_editorial"]),
            ("fecha",   TX["libros_fecha"]),
        ]
        for key, label in campos:
            tk.Label(left, text=label, font=FONT_SMALL,
                     bg=COLOR_CARD, fg=COLOR_DIM).pack(anchor="w", padx=20, pady=(10, 0))
            e = tk.Entry(left, font=FONT_ENTRY, bg=COLOR_CARD2, fg=COLOR_TEXT,
                         insertbackground=COLOR_GOLD, relief="flat",
                         highlightthickness=1, highlightbackground=COLOR_GOLD_DIM,
                         highlightcolor=COLOR_GOLD)
            e.pack(fill="x", padx=20, ipady=5, pady=(2, 0))
            self._campos_form[key] = e

        self._msg_form = tk.Label(left, text="", font=("Georgia", 9, "italic"),
                                  bg=COLOR_CARD, fg=COLOR_ERROR, wraplength=260)
        self._msg_form.pack(padx=20, pady=(8, 0), anchor="w")

        btn_add = tk.Button(left, text=TX["libros_btn_add"],
                            font=FONT_BTN, bg=COLOR_GOLD_DIM, fg=COLOR_TEXT,
                            activebackground=COLOR_GOLD, activeforeground="#000",
                            relief="flat", bd=0, cursor="hand2",
                            command=self._agregar_libro)
        btn_add.pack(fill="x", padx=20, pady=(12, 6), ipady=8)
        btn_add.bind("<Enter>", lambda _: btn_add.config(bg=COLOR_GOLD, fg="#000"))
        btn_add.bind("<Leave>", lambda _: btn_add.config(bg=COLOR_GOLD_DIM, fg=COLOR_TEXT))

        btn_del = tk.Button(left, text=TX["libros_btn_del"],
                            font=FONT_BTN, bg="#2a1a1a", fg="#c47a6a",
                            activebackground=COLOR_ERROR, activeforeground=COLOR_TEXT,
                            relief="flat", bd=0, cursor="hand2",
                            command=self._eliminar_libro)
        btn_del.pack(fill="x", padx=20, pady=(0, 20), ipady=8)

        # ── Panel derecho: tabla ──
        right = tk.Frame(body, bg=COLOR_BG)
        right.pack(side="left", fill="both", expand=True)

        # Barra búsqueda
        busq_frame = tk.Frame(right, bg=COLOR_BG)
        busq_frame.pack(fill="x", pady=(0, 8))
        tk.Label(busq_frame, text="🔍", font=("Georgia", 12),
                 bg=COLOR_BG, fg=COLOR_DIM).pack(side="left")
        self._busq_var = tk.StringVar()
        self._busq_var.trace_add("write", lambda *_: self._cargar_tabla())
        busq_e = tk.Entry(busq_frame, textvariable=self._busq_var,
                          font=FONT_ENTRY, bg=COLOR_CARD2, fg=COLOR_TEXT,
                          insertbackground=COLOR_GOLD, relief="flat",
                          highlightthickness=1, highlightbackground=COLOR_GOLD_DIM)
        busq_e.pack(side="left", fill="x", expand=True, ipady=5, padx=(6, 0))

        # Tabla
        cols = (TX["col_isbn"], TX["col_titulo"], TX["col_autor"], TX["col_categ"], TX["col_editorial"], TX["col_estado"])
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Bib.Treeview",
                        background=COLOR_CARD2, foreground=COLOR_TEXT,
                        fieldbackground=COLOR_CARD2, rowheight=26,
                        font=("Georgia", 10))
        style.configure("Bib.Treeview.Heading",
                        background=COLOR_CARD, foreground=COLOR_GOLD,
                        font=("Georgia", 9, "bold"), relief="flat")
        style.map("Bib.Treeview", background=[("selected", COLOR_GOLD_DIM)])

        tree_frame = tk.Frame(right, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 style="Bib.Treeview", selectmode="browse")
        anchos = [120, 220, 160, 110, 110, 90]
        for col, ancho in zip(cols, anchos):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=ancho, minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._cargar_tabla()

    # ── Lógica de datos ───────────────────
    def _cargar_tabla(self):
        """Carga libros desde la BD y los muestra en la tabla."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        filtro = f"%{self._busq_var.get().strip()}%"
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("""
                SELECT l.isbn, l.titulo, l.autor,
                       COALESCE(c.nombre_categoria, '—'),
                       COALESCE(e.nombre_editorial,  '—'),
                       l.estado
                FROM libros l
                LEFT JOIN categorias  c ON l.id_categoria = c.id_categoria
                LEFT JOIN editoriales e ON l.id_editorial  = e.id_editorial
                WHERE l.titulo LIKE ? OR l.autor LIKE ? OR l.isbn LIKE ?
                ORDER BY l.titulo
            """, (filtro, filtro, filtro))
            for fila in cur.fetchall():
                tag = "prestado" if fila[5] == "Prestado" else ""
                self.tree.insert("", "end", values=fila, tags=(tag,))
            self.tree.tag_configure("prestado", foreground="#c47a6a")
            conn.close()
        except sqlite3.Error as e:
            self._msg_form.config(text=f"Error BD: {e}", fg=COLOR_ERROR)

    def _on_select(self, _=None):
        """Al seleccionar una fila, rellena el formulario con sus datos."""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        mapeo = ["isbn", "titulo", "autor", "categ", "editorial"]
        for key, val in zip(mapeo, vals[:5]):
            e = self._campos_form[key]
            e.delete(0, "end")
            e.insert(0, val)

    def _agregar_libro(self):
        """Valida el formulario y agrega un libro usando la clase Libro."""
        isbn     = self._campos_form["isbn"].get().strip()
        titulo   = self._campos_form["titulo"].get().strip()
        autor    = self._campos_form["autor"].get().strip()
        categ    = self._campos_form["categ"].get().strip()
        editorial = self._campos_form["editorial"].get().strip()
        fecha    = self._campos_form["fecha"].get().strip()

        if not isbn or not titulo or not autor:
            self._msg_form.config(
                text=TX["msg_campos_req"], fg=COLOR_ERROR)
            return

        # Crear objeto Libro (POO)
        try:
            libro = Libro(titulo=titulo, autor=autor, isbn=isbn)
        except Exception as e:
            self._msg_form.config(text=f"Error al crear libro: {e}", fg=COLOR_ERROR)
            return

        try:
            id_cat = int(categ)   if categ    else None
            id_edi = int(editorial) if editorial else None
        except ValueError:
            self._msg_form.config(
                text=TX["msg_id_numerico"], fg=COLOR_ERROR)
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("""
                INSERT INTO libros (isbn, titulo, autor, id_categoria,
                                    id_editorial, fecha_publicacion, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (libro.isbn, libro.titulo, libro.autor,
                  id_cat, id_edi, fecha or None, libro.estado))
            conn.commit()
            conn.close()
            self._msg_form.config(
                text=f"Libro '{libro.titulo}' añadido.", fg=COLOR_SUCCESS)
            self._limpiar_form()
            self._cargar_tabla()
        except sqlite3.IntegrityError:
            self._msg_form.config(
                text=TX["msg_isbn_existe"].format(isbn=isbn), fg=COLOR_ERROR)
        except sqlite3.Error as e:
            self._msg_form.config(text=f"Error BD: {e}", fg=COLOR_ERROR)

    def _eliminar_libro(self):
        """Elimina el libro seleccionado si no tiene préstamos activos."""
        sel = self.tree.selection()
        if not sel:
            self._msg_form.config(
                text=TX["msg_sel_tabla"], fg=COLOR_ERROR)
            return

        isbn  = self.tree.item(sel[0], "values")[0]
        titulo = self.tree.item(sel[0], "values")[1]

        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            # Comprobar préstamos activos
            cur.execute("""
                SELECT COUNT(*) FROM prestamos
                WHERE isbn = ? AND devuelto = 0
            """, (isbn,))
            if cur.fetchone()[0] > 0:
                self._msg_form.config(
                    text=TX["msg_prestamos_act"].format(titulo=titulo),
                    fg=COLOR_ERROR)
                conn.close()
                return
            cur.execute("DELETE FROM libros WHERE isbn = ?", (isbn,))
            conn.commit()
            conn.close()
            self._msg_form.config(
                text=f"Libro '{titulo}' eliminado.", fg=COLOR_SUCCESS)
            self._cargar_tabla()
        except sqlite3.Error as e:
            self._msg_form.config(text=f"Error BD: {e}", fg=COLOR_ERROR)

    def _limpiar_form(self):
        for e in self._campos_form.values():
            e.delete(0, "end")

    # ── Ciclo de vida ─────────────────────
    def mostrar(self):
        self.frame.pack(fill="both", expand=True)
        self._cargar_tabla()

    def ocultar(self):
        self.frame.pack_forget()