# El Archivo de los Mundos

Sistema de gestión de biblioteca personal desarrollado como aplicación de escritorio en Python. Permite registrar, organizar y consultar colecciones de libros con un sistema de usuarios completo y una interfaz visual cuidada.

## Características

- **Autenticación completa** — registro, inicio de sesión y verificación de cuenta por email (SMTP)
- **Hashing seguro** — las contraseñas se almacenan cifradas con SHA-256, nunca en texto plano
- **Base de datos local** — gestión de datos con SQLite sin dependencias externas
- **Interfaz de escritorio** — UI construida con tkinter, tema oscuro con acentos dorados
- **Arquitectura modular** — el sistema de autenticación está desacoplado del resto de la aplicación mediante un callback `on_success`, lo que facilita su reutilización

## Tecnologías

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3 |
| Interfaz | tkinter |
| Base de datos | SQLite3 |
| Seguridad | hashlib (SHA-256) |
| Email | smtplib / SMTP |

## Estructura del proyecto

```
el-archivo-de-los-mundos/
├── auth/
│   ├── login.py          # Ventana de inicio de sesión
│   ├── register.py       # Ventana de registro
│   └── verify.py         # Verificación por email
├── db/
│   └── database.py       # Gestión de SQLite
├── ui/
│   └── main.py           # Interfaz principal
└── app.py                # Punto de entrada
```

## Instalación

```bash
git clone https://github.com/LuisVilRiv/el-archivo-de-los-mundos.git
cd el-archivo-de-los-mundos
pip install -r requirements.txt
python app.py
```

> Requiere Python 3.8 o superior. Para la verificación por email es necesario configurar las credenciales SMTP en el fichero de configuración.

## Capturas

> *(pendiente de añadir)*

## Lo que aprendí

Este proyecto nació como herramienta personal y acabó convirtiéndose en un ejercicio completo de arquitectura de aplicaciones de escritorio: separación de responsabilidades, persistencia de datos, seguridad básica en autenticación y diseño de UI sin frameworks externos.

## Licencia

MIT
