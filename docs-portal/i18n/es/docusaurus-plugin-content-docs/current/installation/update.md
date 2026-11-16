---
title: Actualizar PromptVault
description: Actualice de forma segura una instalación de PromptVault autohospedada.
---

# Actualizar PromptVault

Siga estos pasos para actualizar la instalación con Docker Compose descrita en [Instalación](index.md). La base de datos conserva sus datos mientras reconstruye los servicios `web` y `docs`.

## Antes de empezar {#before-you-start}

1. Lea las [notas de la versión](../release-notes/index.md) y `CHANGELOG.md` para conocer los cambios incompatibles y las notas de migración.
2. Compruebe que el servidor tenga espacio suficiente para una copia de seguridad de la base de datos y las nuevas imágenes.
3. Pruebe primero la actualización en una instalación de pruebas, si dispone de una.
4. Reserve un breve periodo de mantenimiento. Es posible que los usuarios no puedan iniciar sesión mientras se reinicia la aplicación.
5. Compruebe que puede acceder a la carpeta del proyecto PromptVault y al contenedor de la base de datos.

## 1. Hacer una copia de seguridad {#1-back-up-the-database}

Cree y verifique una copia comprimida de la base de datos antes de descargar o iniciar la actualización. Ejecute estos comandos desde la carpeta del proyecto PromptVault:

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

El último comando debe terminar sin errores. Compruebe que el archivo de respaldo no esté vacío. Déjelo en `data/backups` por si necesita restaurarlo y copie otra versión a un lugar seguro fuera del servidor. No continúe si la copia ha fallado.

## 2. Descargar y reconstruir {#2-download-and-rebuild}

Desde la carpeta del proyecto PromptVault, actualice al último código de la rama `main`. Para instalar una versión estable concreta, use su etiqueta en su lugar.

```bash
git checkout main
git pull origin main
```

Para instalar una versión publicada concreta, descargue y seleccione su etiqueta:

```bash
git fetch --tags
git checkout <ETIQUETA_DE_VERSION>
```

Reconstruya los servicios sin usar capas en caché y sustituya el contenedor web. Mantenga en ejecución la base de datos y Redis:

```bash
docker-compose build --no-cache
docker-compose stop web
docker-compose rm web
docker-compose up -d db redis
sleep 15
docker-compose up -d web docs
```

Espere 15 segundos después de iniciar la base de datos y Redis para que la base termine de inicializarse. El proyecto también espera a que las comprobaciones de salud de la base y Redis sean satisfactorias antes de iniciar `web`.

## 3. Actualizar la base de datos {#3-apply-database-updates}

Una migración actualiza la estructura de la base de datos para la nueva versión de PromptVault. Ejecute la migración y compruebe qué versión de migración está activa:

```bash
docker-compose exec -T web alembic upgrade head
docker-compose exec -T web alembic current
```

Ejecute esta migración solo después de iniciar `web`. El segundo comando debe mostrar la versión de migración actual. Si falla la migración, deténgase y consulte [Solución de problemas](../troubleshooting/index.md).

## 4. Comprobar la actualización {#4-check-the-update}

```bash
docker-compose logs web | head -50
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

La comprobación de salud debe responder correctamente. Abra PromptVault en un navegador, inicie sesión y compruebe que sus prompts estén disponibles. Si usa el servicio de documentación, ábralo también (dirección predeterminada: `http://localhost:7876`).

## Si algo falla {#if-something-goes-wrong}

Revise los registros de los servicios para buscar mensajes de error:

```bash
docker-compose logs --tail=100 web docs
```

Si una reconstrucción sin caché falla con `No module named 'psycopg'`, use PromptVault 1.13.1 o una versión posterior. Esa versión corrigió el problema de dependencias descrito en el [ticket #94](https://codeberg.org/medenor/promptvault/issues/94). Para otros errores, consulte [Solución de problemas](../troubleshooting/index.md).

### Volver a la versión anterior {#return-to-the-previous-version}

Estos pasos restauran la copia de seguridad de la base de datos creada antes de la actualización y devuelven la aplicación y la documentación a la versión anterior. La restauración reemplaza la base de datos actual por la copia anterior. Se perderán los prompts y otros cambios realizados desde esa copia, salvo que guarde primero la base de datos actual.

Detenga la aplicación antes de continuar:

```bash
docker-compose stop web
```

Si creó o modificó prompts después de actualizar, guarde la base de datos actual antes de restaurar:

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

Restaure la copia verificada anterior a la actualización. Sustituya `<ARCHIVO_DE_RESPALDO>` por el nombre del archivo creado en el paso 1, sin el prefijo de carpeta `data/backups/`. Estos comandos eliminan y crean de nuevo la base de datos antes de cargar la copia:

```bash
set -euo pipefail
docker-compose exec -T db psql -U promptvault postgres -c 'DROP DATABASE promptvault;'
docker-compose exec -T db psql -U promptvault postgres -c 'CREATE DATABASE promptvault;'
gzip -dc "data/backups/<ARCHIVO_DE_RESPALDO>" \
  | docker-compose exec -T db psql -U promptvault -d promptvault
```

Después, seleccione la versión anterior y reconstruya sus imágenes sin usar capas en caché:

```bash
git fetch --tags
git checkout <ETIQUETA_VERSION_ANTERIOR>
docker-compose build --no-cache
```

Inicie la versión anterior y compruebe los registros y el endpoint de salud:

```bash
docker-compose up -d web docs
docker-compose logs web --tail=20
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Inicie sesión y compruebe que sus prompts estén disponibles. Si falla la restauración o el inicio, deténgase y consulte [Solución de problemas](../troubleshooting/index.md).
