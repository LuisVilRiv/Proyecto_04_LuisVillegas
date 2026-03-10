-- createbbdd.sql
-- Proyecto: Biblioteca La Granateca
-- Normalización 3FN con catálogo más completo
-- Autor: Luis
-- Fecha: 2026-03-09

-- =====================
-- Tabla de usuarios
-- =====================
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    correo TEXT UNIQUE,
    telefono TEXT,
    password TEXT NOT NULL DEFAULT '',
    rol TEXT NOT NULL DEFAULT 'normal'
);

-- =====================
-- Tabla de categorías
-- =====================
CREATE TABLE IF NOT EXISTS categorias (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_categoria TEXT UNIQUE NOT NULL
);

-- =====================
-- Tabla de editoriales
-- =====================
CREATE TABLE IF NOT EXISTS editoriales (
    id_editorial INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_editorial TEXT UNIQUE NOT NULL
);

-- =====================
-- Tabla de libros
-- =====================
CREATE TABLE IF NOT EXISTS libros (
    isbn TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    autor TEXT NOT NULL,
    id_categoria INTEGER,
    id_editorial INTEGER,
    fecha_publicacion TEXT,
    estado TEXT DEFAULT 'Disponible',
    FOREIGN KEY (id_categoria) REFERENCES categorias(id_categoria),
    FOREIGN KEY (id_editorial) REFERENCES editoriales(id_editorial)
);

-- =====================
-- Tabla de préstamos
-- =====================
CREATE TABLE IF NOT EXISTS prestamos (
    id_prestamo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    isbn TEXT NOT NULL,
    fecha_prestamo TEXT NOT NULL,
    fecha_devolucion_estimada TEXT NOT NULL,
    fecha_devolucion_real     TEXT,
    devuelto INTEGER DEFAULT 0,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
    FOREIGN KEY (isbn) REFERENCES libros(isbn)
);

-- =====================
-- Datos iniciales
-- =====================

-- Categorías
INSERT OR IGNORE INTO categorias (nombre_categoria) VALUES
('Fantasía'), 
('Misterio'), 
('Juvenil'), 
('Ciencia ficción'),
('Clásicos');

-- Editoriales
INSERT OR IGNORE INTO editoriales (nombre_editorial) VALUES
('Planeta'),
('SM'),
('Editorial X'),
('Alfaguara'),
('Anaya');

-- Libros de ejemplo
INSERT OR IGNORE INTO libros (isbn, titulo, autor, id_categoria, id_editorial, fecha_publicacion, estado) VALUES
('9788497590000', 'El Príncipe de la Niebla', 'Carlos Ruiz Zafón', 2, 1, '1993-06-15', 'Disponible'),
('9788408092334', 'Memorias de Idhún: La Resistencia', 'Laura Gallego García', 1, 2, '2004-04-01', 'Disponible'),
('9788408137329', 'Detective Esqueleto: Primer caso', 'Autor Desconocido', 3, 3, '2010-10-01', 'Disponible'),
('9788408178186', 'La Sombra del Viento', 'Carlos Ruiz Zafón', 2, 1, '2001-04-01', 'Disponible'),
('9788498380291', 'Finis Mundi', 'Laura Gallego García', 1, 2, '1999-05-15', 'Disponible'),
('9788408179701', 'Marina', 'Carlos Ruiz Zafón', 2, 1, '1999-01-01', 'Disponible'),
('9788498380505', 'Dos velas para el diablo', 'Laura Gallego García', 1, 2, '2000-09-01', 'Disponible'),
('9788498380772', 'El Valle de los Lobos', 'Laura Gallego García', 1, 2, '1999-06-01', 'Disponible'),
('9788420481440', '1984', 'George Orwell', 5, 4, '1949-06-08', 'Disponible'),
('9788420419331', 'Farenheit 451', 'Ray Bradbury', 4, 4, '1953-10-19', 'Disponible'),
('9788420419881', 'El Hobbit', 'J.R.R. Tolkien', 1, 4, '1937-09-21', 'Disponible'),
('9788497590017', 'Harry Potter y la piedra filosofal', 'J.K. Rowling', 1, 5, '1997-06-26', 'Disponible'),
('9788497590024', 'Harry Potter y la cámara secreta', 'J.K. Rowling', 1, 5, '1998-07-02', 'Disponible'),
('9788497590031', 'Harry Potter y el prisionero de Azkaban', 'J.K. Rowling', 1, 5, '1999-07-08', 'Disponible'),
('9788408130019', 'Crónica del pájaro que da cuerda al mundo', 'Haruki Murakami', 3, 4, '1995-04-12', 'Disponible');
-- =====================
-- Configuración de préstamos
-- =====================
CREATE TABLE IF NOT EXISTS configuracion_prestamos (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
INSERT OR IGNORE INTO configuracion_prestamos (clave, valor) VALUES
    ('max_dias',              '15'),
    ('dias_por_dia_retraso',  '2'),
    ('max_prestamos',         '3'),
    ('bloquear_sancionados',  '1'),
    ('aviso_dias_antes',      '3');

-- =====================
-- Tabla de sanciones
-- =====================
CREATE TABLE IF NOT EXISTS sanciones (
    id_sancion       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_prestamo      INTEGER NOT NULL,
    id_usuario       INTEGER NOT NULL,
    dias_retraso     INTEGER NOT NULL DEFAULT 0,
    dias_suspension  INTEGER NOT NULL DEFAULT 0,
    fecha_inicio     TEXT    NOT NULL,
    fecha_fin        TEXT    NOT NULL,
    anulada          INTEGER NOT NULL DEFAULT 0,
    nota             TEXT,
    FOREIGN KEY (id_prestamo) REFERENCES prestamos(id_prestamo),
    FOREIGN KEY (id_usuario)  REFERENCES usuarios(id_usuario)
);