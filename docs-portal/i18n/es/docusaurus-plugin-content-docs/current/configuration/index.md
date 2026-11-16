---
title: Configuración
sidebar_position: 2
---

# Referencia de configuración

PromptVault se configura mediante variables de entorno, normalmente definidas en el archivo `.env` en la raíz del repositorio. Empiece copiando `.env.example`. Esta es una referencia para administradores: cambie un valor solo cuando conozca el resultado que necesita, reinicie el servicio afectado y confirme que se inicia correctamente.

Términos utilizados: una URL es una dirección para conectarse a un servicio; SQL es el lenguaje de consultas de la base de datos; Redis es el servicio que aplica los límites de tasa; SMTP es el protocolo para enviar correo electrónico.

## Base de datos {#database}

| Variable | Predeterminado | Propósito |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data-dev/promptvault.db` | Cadena de conexión. Use una URL `postgresql://` en producción. |
| `DB_POOL_SIZE` | `20` | Tamaño del pool de conexiones (ignorado en SQLite). |
| `DB_POOL_TIMEOUT` | `30` | Tiempo de espera para obtener una conexión del pool, en segundos. |
| `DB_POOL_RECYCLE` | `3600` | Segundos antes de reciclar una conexión del pool. |
| `DB_ECHO` | `false` | Registra cada sentencia SQL — útil para depurar, ruidoso en producción. |

## Aplicación {#application}

| Variable | Predeterminado | Propósito |
|---|---|---|
| `ENVIRONMENT` | `development` | Uno de `development`, `testing`, `production`. |
| `PROMPTVAULT_DATA_DIR` | `./data-dev` | Directorio para archivos de datos, copias de seguridad y registros. **Use una ruta distinta por entorno** (dev/staging/prod) incluso si comparten sistema de archivos — compartir un directorio de datos entre entornos puede provocar que las copias de seguridad y restauraciones programadas colisionen. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`. |
| `AUDIT_LOG_LEVEL` | `INFO` | Nivel de registro específico para eventos de auditoría de control de versiones y copias de seguridad. |

## Autenticación {#authentication}

| Variable | Predeterminado | Propósito |
|---|---|---|
| `AUTH_ENABLED` | `true` | Establézcalo en `false` solo para una implementación de un único usuario, de confianza y sin red — esto desactiva el inicio de sesión y hace que todos los endpoints sean públicamente accesibles. |
| `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` | — | Rutas al par de claves ES256 usado para firmar y verificar JSON Web Tokens (JWT). Genérelo con los comandos de [Instalación](../installation/index.md). |
| `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` | `900` (15 min) | Duración del token de acceso. |
| `JWT_REFRESH_TOKEN_EXPIRE_SECONDS` | `604800` (7 días) | Duración del token de actualización. |
| `TOTP_ENCRYPTION_KEY` | — | Secreto del servidor que cifra en reposo los secretos de autenticación de dos factores (TOTP). Obligatorio en cuanto algún usuario activa la 2FA. Genéralo con `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. Nunca lo rotes sin un plan de migración: al cambiarlo, las configuraciones de 2FA existentes dejan de funcionar. |
| `MAX_LOGIN_ATTEMPTS` | `5` | Intentos fallidos antes del bloqueo de la cuenta. |
| `ACCOUNT_LOCKOUT_DURATION_SECONDS` | `900` | Duración del bloqueo. |
| `MAX_SESSIONS_PER_USER` | `5` | Límite de sesiones simultáneas (`0` = ilimitado). |
| `SESSION_INACTIVE_TIMEOUT_SECONDS` | `2592000` (30 días) | Expiración por inactividad. |

Las variables de política de contraseñas `PASSWORD_MIN_LENGTH`, `PASSWORD_REQUIRE_UPPERCASE`, `PASSWORD_REQUIRE_LOWERCASE`, `PASSWORD_REQUIRE_DIGIT` y `PASSWORD_REQUIRE_SPECIAL` también son configurables. De forma predeterminada, exigen al menos 12 caracteres y las cuatro clases de caracteres.

## Límite de tasa {#rate-limiting}

Los límites de tasa son por usuario (con reserva por IP para solicitudes anónimas) y se agrupan en categorías, cada una configurable de forma independiente:

| Categoría | Predeterminado | Prefijo de variable de entorno |
|---|---|---|
| Lectura (solicitudes GET) | 300/min | `RATE_LIMIT_READ_*` |
| Escritura (crear/actualizar/eliminar/revertir) | 60/min | `RATE_LIMIT_WRITE_*` |
| Costosas (importar/exportar, crear/restaurar/verificar copias de seguridad) | 10/min | `RATE_LIMIT_EXPENSIVE_*` |
| Masivas (eliminación masiva, eliminar todas las copias de seguridad, comprimir) | 5/min | `RATE_LIMIT_BULK_*` |

Cada categoría tiene variables `_ATTEMPTS` y `_WINDOW_SECONDS`, por ejemplo `RATE_LIMIT_WRITE_ATTEMPTS=60` y `RATE_LIMIT_WRITE_WINDOW_SECONDS=60`. Los endpoints de autenticación tienen límites separados: `RATE_LIMIT_LOGIN_*`, `RATE_LIMIT_REGISTER_*` y `RATE_LIMIT_PASSWORD_RESET_*`. El límite de tasa funciona solo cuando el servicio Redis indicado por `REDIS_URL` es accesible. Si no ejecuta Redis, no suponga que estos límites están activos.

## Correo electrónico (restablecimiento de contraseña) {#email-password-reset}

| Variable | Propósito |
|---|---|
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS` | Conexión al servidor SMTP. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Credenciales SMTP. |
| `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME` | Identidad del remitente en los correos salientes. |
| `PASSWORD_RESET_TOKEN_EXPIRE_SECONDS` | `3600` por defecto — cuánto tiempo permanece válido un enlace de restablecimiento. |
| `APP_BASE_URL` | URL base usada para construir el enlace de restablecimiento enviado por correo. |

## Copias de seguridad {#backups}

| Variable | Propósito |
|---|---|
| `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` | Requerida solo si configura almacenamiento en la nube para copias de seguridad — cifra en reposo las credenciales de proveedor almacenadas (claves de acceso/secreta). Genérela con `python -c "import secrets; print(secrets.token_hex(32))"` y nunca la incluya en un commit. |

Consulte [Copias de seguridad](../user-guide/backups.md) para saber cómo encajan los programas, el cifrado y el almacenamiento en la nube.

## Activos de frontend {#frontend-assets}

| Variable | Predeterminado | Propósito |
|---|---|---|
| `USE_VITE_ASSETS` | `false` | Establézcalo en `true` para servir CSS/JS desde la compilación de Vite en lugar de desde el código fuente. |

## Ejemplo: producción con PostgreSQL {#example-postgresql-production}

```bash
DATABASE_URL=postgresql://promptvault_user:secure_password@localhost:5432/promptvault_prod
DB_POOL_SIZE=30
DB_POOL_TIMEOUT=60
ENVIRONMENT=production
LOG_LEVEL=WARNING
```
