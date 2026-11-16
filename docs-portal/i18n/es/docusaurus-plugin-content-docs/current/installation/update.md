---
title: Actualizar PromptVault
description: Actualice de forma segura una instalación de PromptVault autohospedada.
---

# Actualizar PromptVault

Siga estos pasos para actualizar la instalación con Docker Compose descrita en [Instalación](index.md). La base de datos conserva sus datos mientras reconstruye los servicios `web` y `docs`.

## Antes de empezar

1. Lea las [notas de la versión](../release-notes/index.md) para conocer los cambios que afectan a su instalación.
2. Compruebe que el servidor tenga espacio suficiente para una copia de seguridad de la base de datos y las nuevas imágenes.
3. Reserve un breve periodo de mantenimiento. Es posible que los usuarios no puedan iniciar sesión mientras se reinicia la aplicación.
4. Compruebe que puede acceder a la carpeta del proyecto PromptVault y al contenedor de la base de datos.

## 1. Hacer una copia de seguridad

Cree y verifique una copia comprimida de la base de datos antes de descargar o iniciar la actualización. Ejecute estos comandos desde la carpeta del proyecto PromptVault:

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U promptvault -d promptvault | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

El último comando debe terminar sin errores. Compruebe que el archivo de respaldo no esté vacío. Déjelo en `data/backups` por si necesita restaurarlo y copie otra versión a un lugar seguro fuera del servidor. No continúe si la copia ha fallado.

## 2. Descargar y reconstruir

Desde la carpeta del proyecto PromptVault, elija la versión que desea instalar. Una etiqueta de versión (tag) identifica una versión publicada. Elija una de las que aparecen en las notas de la versión:

```bash
git fetch --tags
git checkout <ETIQUETA_DE_VERSION>
```

Reconstruya e inicie los servicios de la aplicación y de la documentación:

```bash
docker compose build web docs
docker compose up -d db redis
docker compose up -d web docs
```

El proyecto está configurado para iniciar `web` solo cuando la base de datos y Redis indiquen que están listos.

## 3. Actualizar la base de datos

Una migración actualiza la estructura de la base de datos para la nueva versión de PromptVault. Ejecute la migración y compruebe qué versión de migración está activa:

```bash
docker compose exec -T web alembic upgrade head
docker compose exec -T web alembic current
```

El segundo comando debe mostrar la versión de migración actual. Si falla la migración, deténgase y consulte [Solución de problemas](../troubleshooting/index.md).

## 4. Comprobar la actualización

```bash
curl --fail http://localhost:8001/api/health
```

La comprobación de salud debe responder correctamente. Abra PromptVault en un navegador, inicie sesión y compruebe que sus prompts estén disponibles. Si usa el servicio de documentación, ábralo también (dirección predeterminada: `http://localhost:7876`).

## Si algo falla

Revise los registros de los servicios para buscar mensajes de error:

```bash
docker compose logs --tail=100 web docs
```

Si una reconstrucción sin caché falla con `No module named 'psycopg'`, use PromptVault 1.13.1 o una versión posterior. Esa versión corrigió el problema de dependencias descrito en el [ticket #94](https://codeberg.org/medenor/promptvault/issues/94). Para otros errores, consulte [Solución de problemas](../troubleshooting/index.md).

### Volver a la versión anterior

Estos pasos restauran la copia de seguridad de la base de datos creada antes de la actualización y devuelven la aplicación y la documentación a la versión anterior. La restauración reemplaza la base de datos actual por la copia anterior. Se perderán los prompts y otros cambios realizados desde esa copia, salvo que guarde primero la base de datos actual.

Si creó o modificó prompts después de actualizar, guarde la base de datos actual antes de restaurar:

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U promptvault -d promptvault | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

Después, detenga la aplicación, elija en las notas de la versión la etiqueta de la versión anterior y reconstruya sus imágenes:

```bash
docker compose stop web
git fetch --tags
git checkout <ETIQUETA_VERSION_ANTERIOR>
docker compose build web docs
```

Restaure la copia verificada anterior a la actualización. Sustituya `<ARCHIVO_DE_RESPALDO>` por el nombre del archivo creado en el paso 1. El primer comando elimina el contenido actual de la base de datos antes de cargar la copia:

```bash
docker compose exec -T db psql -U promptvault -d promptvault \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
set -euo pipefail
gzip -dc "data/backups/<ARCHIVO_DE_RESPALDO>" \
  | docker compose exec -T db psql -U promptvault -d promptvault
```

Inicie la versión anterior y compruebe que PromptVault funciona:

```bash
docker compose up -d web docs
curl --fail http://localhost:8001/api/health
```

Inicie sesión y compruebe que sus prompts estén disponibles. Si falla la restauración o el inicio, deténgase y consulte [Solución de problemas](../troubleshooting/index.md).
