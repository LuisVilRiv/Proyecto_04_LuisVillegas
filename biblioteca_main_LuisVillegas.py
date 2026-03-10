"""
Proyecto:        Biblioteca El Archivo de los Mundos
Descripción:     Módulo principal. Menú adaptado por rol con soporte completo
                 de temas, fuentes e idioma mediante T() y ConfigApp.
Autor/a:         Luis Villegas Rivera
Fecha:           2026-03-09
Clases principales:
    - MenuPrincipal : Menú visual con navegación por secciones según rol.
"""

import tkinter as tk

from secciones.biblioteca_gestion_libros    import SeccionLibros
from secciones.biblioteca_gestion_usuarios  import SeccionUsuarios
from secciones.biblioteca_gestion_prestamos import SeccionPrestamos
from secciones.biblioteca_secciones_usuario import SeccionMiCatalogo, SeccionMisPrestamos
from secciones.biblioteca_ajustes           import SeccionAjustes, ConfigApp, T
from secciones.biblioteca_sanciones         import SeccionSanciones
from secciones.biblioteca_calendario        import SeccionCalendario
from secciones.biblioteca_facturas          import SeccionFacturas


class MenuPrincipal:
    def __init__(self, parent, db_path, usuario, rol, on_logout):
        self.parent    = parent
        self.db_path   = db_path
        self.usuario   = usuario
        self.rol       = rol
        self.on_logout = on_logout
        self._seccion_activa = None
        self._btn_activo     = None
        self._c  = ConfigApp.colores()
        self._f  = ConfigApp.fuentes()
        self.frame = tk.Frame(parent, bg=self._c["bg"])
        self._build_ui()

    def _build_ui(self):
        c, f = self._c, self._f

        # Menús según rol (con texto traducido)
        menu_admin = [
            (T("menu_libros"),       SeccionLibros),
            (T("menu_socios"),       SeccionUsuarios),
            (T("menu_prestamos"),    SeccionPrestamos),
            (T("menu_sanciones", "⚖  Sanciones"), SeccionSanciones),
            (T("menu_calendario", "📅  Calendario"), SeccionCalendario),
            (T("menu_facturas",   "🧾  Facturas"),   SeccionFacturas),
        ]
        menu_normal = [
            (T("menu_catalogo"),     SeccionMiCatalogo),
            (T("menu_misprestamos"), SeccionMisPrestamos),
            (T("menu_calendario", "📅  Calendario"), SeccionCalendario),
            (T("menu_facturas",   "🧾  Facturas"),   SeccionFacturas),
        ]

        # ── Topbar ──
        topbar = tk.Frame(self.frame, bg=c["card"], height=48)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="El Archivo de los Mundos",
                 font=("Georgia", f["titulo"] - 3, "bold"),
                 bg=c["card"], fg=c["acento"]).pack(side="left", padx=20, pady=10)
        tk.Label(topbar, text=f"  ·  {self.usuario}",
                 font=("Georgia", f["titulo"] - 5, "italic"),
                 bg=c["card"], fg=c["dim"]).pack(side="left", pady=10)

        badge_fg   = "#4a8aaf" if self.rol == "admin" else c["acento_dim"]
        badge_text = "  ✦ ADMIN" if self.rol == "admin" else "  SOCIO"
        tk.Label(topbar, text=badge_text,
                 font=("Georgia", f["small"], "bold"),
                 bg=c["card"], fg=badge_fg).pack(side="left", pady=10)

        btn_logout = tk.Button(
            topbar, text=T("cerrar_sesion", "Cerrar sesión"),
            font=("Georgia", f["small"]), bg=c["card"], fg=c["dim"],
            activebackground=c["acento_dim"], activeforeground=c["text"],
            relief="flat", bd=0, cursor="hand2", command=self.on_logout)
        btn_logout.pack(side="right", padx=(0, 16), ipadx=10, ipady=4)
        btn_logout.bind("<Enter>", lambda _: btn_logout.config(fg=c["acento"]))
        btn_logout.bind("<Leave>", lambda _: btn_logout.config(fg=c["dim"]))

        btn_ajustes = tk.Button(
            topbar, text=T("ajustes", "⚙  Ajustes"),
            font=("Georgia", f["small"]), bg=c["card"], fg=c["dim"],
            activebackground=c["acento_dim"], activeforeground=c["text"],
            relief="flat", bd=0, cursor="hand2",
            command=self._abrir_ajustes)
        btn_ajustes.pack(side="right", padx=(0, 4), ipadx=10, ipady=4)
        btn_ajustes.bind("<Enter>", lambda _: btn_ajustes.config(fg=c["acento"]))
        btn_ajustes.bind("<Leave>", lambda _: btn_ajustes.config(fg=c["dim"]))

        tk.Frame(self.frame, height=1, bg=c["sep"]).pack(fill="x")

        # ── Cuerpo ──
        body = tk.Frame(self.frame, bg=c["bg"])
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=c["sidebar"], width=190)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        lbl_menu = T("menu_admin_lbl") if self.rol == "admin" else T("menu_normal_lbl")
        tk.Label(sidebar, text=lbl_menu,
                 font=("Georgia", f["small"] - 1, "bold"),
                 bg=c["sidebar"], fg=c["dim"]).pack(anchor="w", padx=20, pady=(20, 8))
        tk.Frame(sidebar, height=1, bg=c["sep"]).pack(fill="x", padx=14, pady=(0, 8))

        secciones = menu_admin if self.rol == "admin" else menu_normal
        for texto, Clase in secciones:
            btn = tk.Button(
                sidebar, text=texto,
                font=("Georgia", f["btn"]), bg=c["sidebar"], fg=c["dim"],
                activebackground=c["card"], activeforeground=c["text"],
                relief="flat", bd=0, cursor="hand2", anchor="w", padx=20, pady=10)
            btn.config(command=lambda cl=Clase, b=btn: self._abrir(cl, b))
            btn.bind("<Enter>",
                     lambda e, b=btn: b.config(bg=c["card"])
                     if b is not self._btn_activo else None)
            btn.bind("<Leave>",
                     lambda e, b=btn: b.config(bg=c["sidebar"])
                     if b is not self._btn_activo else None)
            btn.pack(fill="x")

        tk.Frame(sidebar, height=1, bg=c["sep"]).pack(fill="x", padx=14, pady=(16, 8))
        tk.Label(sidebar, text="v1.0 · 2026",
                 font=("Georgia", f["small"] - 1),
                 bg=c["sidebar"], fg=c["dim"]).pack(anchor="w", padx=20)

        self._contenido = tk.Frame(body, bg=c["bg"])
        self._contenido.pack(side="left", fill="both", expand=True)

        bv = tk.Frame(self._contenido, bg=c["bg"])
        bv.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(bv, text="⟡", font=("Georgia", 36),
                 bg=c["bg"], fg=c["acento_dim"]).pack()
        tk.Label(bv, text=T("selecciona_seccion", "Selecciona una sección"),
                 font=("Georgia", f["cuerpo"] + 4, "italic"),
                 bg=c["bg"], fg=c["dim"]).pack(pady=(8, 0))
        self._bv = bv

    def _abrir(self, Clase, boton):
        self._ocultar_bv()
        self._ocultar_seccion()
        if self._btn_activo:
            self._btn_activo.config(bg=self._c["sidebar"], fg=self._c["dim"])
        boton.config(bg=self._c["card"], fg=self._c["acento"])
        self._btn_activo = boton
        self._mostrar_carga()
        self.frame.after(40, lambda: self._abrir_deferred(Clase))

    def _abrir_deferred(self, Clase):
        try:
            sec = Clase(self._contenido, self.db_path, self.usuario)
            self._seccion_activa = sec
            self._ocultar_carga()
            sec.mostrar()
        except Exception as e:
            import traceback; traceback.print_exc()
            self._ocultar_carga()
            for w in self._contenido.winfo_children():
                w.pack_forget()
            tk.Label(self._contenido, text=f"Error: {e}",
                     font=("Georgia", 11), bg=self._c["bg"],
                     fg=self._c["error"]).pack(expand=True)
            self._seccion_activa = None

    def _abrir_ajustes(self, tab=None):
        self._ocultar_bv()
        self._ocultar_seccion()
        if self._btn_activo:
            self._btn_activo.config(bg=self._c["sidebar"], fg=self._c["dim"])
            self._btn_activo = None
        try:
            sec = SeccionAjustes(
                parent=self._contenido, db_path=self.db_path,
                usuario=self.usuario, rol=self.rol,
                on_apply=self._on_ajustes_apply)
            sec.mostrar()
            self._seccion_activa = sec
            if tab:
                sec.abrir_tab(tab)
        except Exception as e:
            tk.Label(self._contenido, text=f"Error: {e}",
                     font=("Georgia", 11), bg=self._c["bg"],
                     fg=self._c["error"]).pack(expand=True)

    def _on_ajustes_apply(self, accion="recargar", nuevo_usuario=None, tab=None):
        if accion == "logout":
            self.on_logout(); return
        if accion == "cambiar_usuario" and nuevo_usuario:
            self.usuario = nuevo_usuario
        self._recargar(volver_ajustes=True, tab=tab)

    def _recargar(self, volver_ajustes=False, tab=None):
        ConfigApp.invalidar()
        self._c = ConfigApp.colores()
        self._f = ConfigApp.fuentes()
        self._seccion_activa = None
        self._btn_activo     = None
        for w in self.frame.winfo_children():
            w.destroy()
        self._build_ui()
        if volver_ajustes:
            self.frame.after(50, lambda: self._abrir_ajustes(tab=tab))

    # ── Pantalla de carga ───────────────────────────────
    def _mostrar_carga(self, texto=None):
        """Muestra un overlay de carga sobre el contenido."""
        c = self._c
        if hasattr(self, "_overlay") and self._overlay.winfo_exists():
            return
        self._overlay = tk.Frame(self._contenido, bg=c["bg"])
        self._overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        msg = texto or T("cargando", "Cargando...")
        tk.Label(
            self._overlay,
            text="⏳",
            font=("Georgia", 32),
            bg=c["bg"], fg=c["acento"]
        ).pack(expand=True, pady=(0, 8))
        tk.Label(
            self._overlay,
            text=msg,
            font=("Georgia", 12, "italic"),
            bg=c["bg"], fg=c["dim"]
        ).pack()
        self._overlay.lift()
        self._contenido.update_idletasks()

    def _ocultar_carga(self):
        """Elimina el overlay de carga si existe."""
        if hasattr(self, "_overlay") and self._overlay.winfo_exists():
            self._overlay.destroy()
        if hasattr(self, "_overlay"):
            del self._overlay

    def _ocultar_bv(self):
        if hasattr(self, "_bv") and self._bv.winfo_exists():
            self._bv.place_forget()

    def _ocultar_seccion(self):
        if self._seccion_activa:
            try: self._seccion_activa.ocultar()
            except: pass
            self._seccion_activa = None
        # Limpiar cualquier widget huérfano del contenedor
        for w in self._contenido.winfo_children():
            try: w.pack_forget()
            except: pass

    def mostrar(self):
        self.frame.pack(fill="both", expand=True)

    def ocultar(self):
        self.frame.pack_forget()