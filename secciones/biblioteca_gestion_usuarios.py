"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Módulo de gestión de usuarios/socios. Define la clase Usuario
                 y proporciona la interfaz gráfica para registrar, eliminar y
                 consultar los socios de la biblioteca.
Autor/a:         Luis Villegas
Fecha:           2026-03-09
Clases principales:
    - Usuario         : Entidad que representa un socio de la biblioteca.
    - SeccionUsuarios : Panel tkinter para la gestión visual de socios.
"""

import tkinter as tk
from tkinter import ttk
import sqlite3

from secciones.biblioteca_gestion_libros import (
    Libro, aplicar_tema,
    COLOR_BG, COLOR_CARD, COLOR_CARD2, COLOR_GOLD, COLOR_GOLD_DIM,
    COLOR_TEXT, COLOR_DIM, COLOR_ERROR, COLOR_SUCCESS,
    FONT_TITLE, FONT_LABEL, FONT_ENTRY, FONT_SMALL, FONT_BTN,
)
from secciones.biblioteca_ajustes import T


# ═══════════════════════════════════════════
# CLASE USUARIO  (requisito POO del proyecto)
# ═══════════════════════════════════════════
class Usuario:
    """
    Representa un socio de la biblioteca.

    Atributos
    ---------
    nombre          : str   — Nombre de usuario en el sistema.
    id_usuario      : int   — Identificador único en la base de datos.
    libros_prestados: list  — Lista de objetos Libro actualmente en posesión.
    correo          : str   — Correo electrónico del socio.
    telefono        : str   — Teléfono de contacto (opcional).
    """

    def __init__(self, nombre: str, id_usuario: int,
                 correo: str = "", telefono: str = ""):
        self.nombre           = nombre
        self.id_usuario       = id_usuario
        self.correo           = correo
        self.telefono         = telefono
        self.libros_prestados: list[Libro] = []

    # ── Gestión de préstamos ──────────────
    def tomar_prestado(self, libro: Libro) -> None:
        """Agrega un libro a la lista de préstamos del usuario."""
        if not isinstance(libro, Libro):
            raise TypeError("Se esperaba un objeto de tipo Libro.")
        if libro.isbn in [l.isbn for l in self.libros_prestados]:
            raise ValueError(
                f"El usuario ya tiene prestado el libro '{libro.titulo}'.")
        libro.marcar_prestado()
        self.libros_prestados.append(libro)

    def devolver(self, isbn: str) -> Libro:
        """
        Retira un libro de la lista del usuario y lo marca como disponible.
        Devuelve el objeto Libro devuelto.
        """
        for libro in self.libros_prestados:
            if libro.isbn == str(isbn):
                libro.marcar_disponible()
                self.libros_prestados.remove(libro)
                return libro
        raise ValueError(
            f"El usuario '{self.nombre}' no tiene prestado el ISBN '{isbn}'.")

    def tiene_prestamos(self) -> bool:
        return len(self.libros_prestados) > 0

    # ── Representación ────────────────────
    def __str__(self) -> str:
        n = len(self.libros_prestados)
        return (f"[{self.id_usuario}] {self.nombre} "
                f"— {n} libro(s) en préstamo")

    def __repr__(self) -> str:
        return (f"Usuario(nombre={self.nombre!r}, "
                f"id_usuario={self.id_usuario!r})")

    # ── Serialización desde BD ────────────
    @classmethod
    def desde_fila(cls, fila: tuple) -> "Usuario":
        """Crea un Usuario a partir de una fila (id, nombre, correo, telefono)."""
        id_u, nombre, correo, telefono = fila
        return cls(nombre=nombre, id_usuario=id_u,
                   correo=correo or "", telefono=telefono or "")


# ═══════════════════════════════════════════
# SECCIÓN TKINTER — Gestión de Usuarios
# ═══════════════════════════════════════════
class SeccionUsuarios:
    """
    Panel de gestión de socios.
    Permite registrar, eliminar y consultar usuarios usando la clase Usuario.
    """

    def __init__(self, parent: tk.Widget, db_path: str, usuario: str):
        aplicar_tema()
        self.db_path = db_path
        self.usuario_activo = usuario

        self.frame = tk.Frame(parent, bg=COLOR_BG)
        self._build_ui()

    # ── Construcción de UI ────────────────
    def _build_ui(self):
        # Cabecera
        cab = tk.Frame(self.frame, bg=COLOR_CARD, height=56)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text=T("cab_socios","👤  Gestión de Socios"),
                 font=FONT_TITLE, bg=COLOR_CARD, fg=COLOR_GOLD
                 ).pack(side="left", padx=24, pady=12)

        tk.Frame(self.frame, height=1, bg=COLOR_GOLD_DIM).pack(fill="x")

        body = tk.Frame(self.frame, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Panel izquierdo: detalle del socio seleccionado ──
        left = tk.Frame(body, bg=COLOR_CARD, width=280,
                        highlightthickness=1, highlightbackground=COLOR_GOLD_DIM)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)

        tk.Label(left, text=T("detalle_socio","DETALLE DEL SOCIO"),
                 font=("Georgia", 9, "bold"), bg=COLOR_CARD, fg=COLOR_DIM
                 ).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Frame(left, height=1, bg=COLOR_GOLD_DIM).pack(fill="x", padx=20)

        self._det_labels = {}
        campos_det = [
            ("id",       "ID"),
            ("nombre",   "Nombre"),
            ("correo",   "Correo"),
            ("telefono", "Teléfono"),
            ("prestamos","Libros en préstamo"),
        ]
        for key, lbl in campos_det:
            tk.Label(left, text=lbl, font=FONT_SMALL,
                     bg=COLOR_CARD, fg=COLOR_DIM).pack(anchor="w", padx=20, pady=(10, 0))
            val = tk.Label(left, text="—", font=FONT_ENTRY,
                           bg=COLOR_CARD, fg=COLOR_TEXT,
                           anchor="w", wraplength=230)
            val.pack(anchor="w", padx=20)
            self._det_labels[key] = val

        self._msg_det = tk.Label(left, text="", font=("Georgia", 9, "italic"),
                                 bg=COLOR_CARD, fg=COLOR_ERROR, wraplength=240)
        self._msg_det.pack(padx=20, pady=(12, 0), anchor="w")

        btn_del = tk.Button(left, text=T("btn_eliminar_socio","✕  Eliminar socio"),
                            font=FONT_BTN, bg="#2a1a1a", fg="#c47a6a",
                            activebackground=COLOR_ERROR, activeforeground=COLOR_TEXT,
                            relief="flat", bd=0, cursor="hand2",
                            command=self._eliminar_usuario)
        btn_del.pack(fill="x", padx=20, pady=(16, 20), ipady=8)

        # ── Panel derecho: tabla ──
        right = tk.Frame(body, bg=COLOR_BG)
        right.pack(side="left", fill="both", expand=True)

        # Búsqueda
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
        cols = ("ID", "Nombre", "Correo", "Teléfono", "Préstamos activos")
        style = ttk.Style()
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
        anchos = [50, 180, 200, 120, 130]
        for col, ancho in zip(cols, anchos):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=ancho, minwidth=50)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._cargar_tabla()

    # ── Lógica de datos ───────────────────
    def _cargar_tabla(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        filtro = f"%{self._busq_var.get().strip()}%"
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("""
                SELECT u.id_usuario, u.nombre,
                       COALESCE(u.correo,   '—'),
                       COALESCE(u.telefono, '—'),
                       COUNT(p.id_prestamo)
                FROM usuarios u
                LEFT JOIN prestamos p
                       ON u.id_usuario = p.id_usuario AND p.devuelto = 0
                WHERE u.nombre LIKE ? OR u.correo LIKE ?
                GROUP BY u.id_usuario
                ORDER BY u.nombre
            """, (filtro, filtro))
            for fila in cur.fetchall():
                tag = "con_prestamos" if fila[4] > 0 else ""
                self.tree.insert("", "end", values=fila, tags=(tag,))
            self.tree.tag_configure("con_prestamos", foreground=COLOR_GOLD)
            conn.close()
        except sqlite3.Error as e:
            self._msg_det.config(text=f"Error BD: {e}", fg=COLOR_ERROR)

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        keys = ["id", "nombre", "correo", "telefono", "prestamos"]
        sufijos = ["", "", "", "", " libro(s)"]
        for key, val, suf in zip(keys, vals, sufijos):
            self._det_labels[key].config(text=f"{val}{suf}")
        self._msg_det.config(text="")

    def _eliminar_usuario(self):
        """Elimina un socio si no tiene préstamos activos."""
        sel = self.tree.selection()
        if not sel:
            self._msg_det.config(
                text="Selecciona un socio de la tabla.", fg=COLOR_ERROR)
            return

        vals     = self.tree.item(sel[0], "values")
        id_u     = vals[0]
        nombre   = vals[1]
        prestamos = int(vals[4])

        if prestamos > 0:
            self._msg_det.config(
                text=f"'{nombre}' tiene {prestamos} préstamo(s) activo(s).\n"
                     "Gestiona las devoluciones primero.",
                fg=COLOR_ERROR)
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("DELETE FROM usuarios WHERE id_usuario = ?", (id_u,))
            conn.commit()
            conn.close()
            self._msg_det.config(
                text=f"Socio '{nombre}' eliminado.", fg=COLOR_SUCCESS)
            for key in self._det_labels:
                self._det_labels[key].config(text="—")
            self._cargar_tabla()
        except sqlite3.Error as e:
            self._msg_det.config(text=f"Error BD: {e}", fg=COLOR_ERROR)

    # ── Ciclo de vida ─────────────────────
    def mostrar(self):
        self.frame.pack(fill="both", expand=True)
        self._cargar_tabla()

    def ocultar(self):
        self.frame.pack_forget()