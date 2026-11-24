---
title: Actualizar PromptVault
description: Actualice de forma segura una instalación de PromptVault autohospedada.
---

# Actualizar PromptVault

Siga estos pasos para actualizar la instalación con Docker Compose descrita en [Instalación](index.md). La base de datos conserva sus datos mientras reconstruye los servicios `web` y `docs`.

Si sus ajustes de producción están en un archivo `.env.production` independiente (recomendado, consulte [Configurar un entorno de producción](production-setup.md)), indíquelo una vez a Docker Compose antes de empezar. Todos los comandos `docker-compose` de la misma ventana de terminal lo usarán a partir de entonces:

```bash
export COMPOSE_ENV_FILES=.env.production
```

Ejecute los comandos de esta página en esa ventana de terminal. Sin este ajuste, Docker Compose lee `.env` y sus valores de desarrollo sustituyen a los de producción. Esto requiere Docker Compose 2.24 o posterior; con una versión anterior, consulte [Configurar un entorno de producción](production-setup.md#use-a-separate-environment-file).

## Antes de empezar {#before-you-start}

1. Lea las [notas de la versión](../release-notes/index.md) y `CHANGELOG.md` para conocer los cambios incompatibles y las notas de migración.
2. Compruebe que el servidor tenga espacio suficiente para una copia de seguridad de la base de datos y las nuevas imágenes.
3. Pruebe primero la actualización en una instalación de pruebas, si dispone de una.
4. Reserve un breve periodo de mantenimiento. Es posible que los usuarios no puedan iniciar sesión mientras se reinicia la aplicación.
5. Compruebe que puede acceder a la carpeta del proyecto PromptVault y al contenedor de la base de datos.

## 1. Hacer una copia de seguridad {#1-back-up-the-database}

Cree una copia comprimida de la base de datos y compruebe que el archivo no esté dañado antes de descargar o iniciar la actualización. Ejecute estos comandos desde la carpeta del proyecto PromptVault:

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

El último comando debe terminar sin errores. Compruebe que el archivo de respaldo no esté vacío. Déjelo en `data/backups` por si necesita restaurarlo y copie otra versión a un lugar seguro fuera del servidor. No continúe si la copia ha fallado. La comprobación con `gzip -t` muestra que el archivo no está dañado; no prueba una restauración.

A continuación, etiquete la imagen que ejecuta ahora su contenedor de producción, para poder volver a ella sin reconstruir. La *imagen* es la copia empaquetada de PromptVault que ejecuta el contenedor. Use el identificador de imagen del contenedor, no `:latest`: la etiqueta `:latest` de su equipo puede apuntar ya a una compilación más reciente.

```bash
docker tag "$(docker inspect promptvault-web --format '{{.Image}}')" promptvault-web:pre-update
docker run --rm --entrypoint python promptvault-web:pre-update -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

El segundo comando debe mostrar la versión que ejecuta ahora. Si muestra otra versión, no continúe: compruebe el nombre del contenedor con `docker-compose ps` y vuelva a ejecutar el primer comando.

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
# Últimas líneas del registro: busque errores
docker-compose logs web | head -50
# Comprobación de salud: debe tener éxito
curl --fail http://localhost:8001/api/health
# Número de prompts: debe coincidir con lo que espera
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
# Versión en ejecución: debe ser la nueva
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
# Ajustes en uso: producción exige ENVIRONMENT=production y DISABLE_RATE_LIMITING=false
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)='
```

La respuesta de la comprobación de salud no incluye la versión: use el comando de versión para confirmar la actualización. Abra PromptVault en un navegador, inicie sesión y compruebe que sus prompts estén disponibles. Si usa el servicio de documentación, ábralo también (dirección predeterminada: `http://localhost:7876`).

## Si algo falla {#if-something-goes-wrong}

Revise los registros de los servicios para buscar mensajes de error:

```bash
docker-compose logs --tail=100 web docs
```

Si el contenedor `web` se reinicia en bucle con `No module named 'psycopg'` en PostgreSQL, consulte [Solución de problemas](../troubleshooting/index.md#psycopg-missing). Para otros errores, consulte [Solución de problemas](../troubleshooting/index.md).

### Volver a la versión anterior {#return-to-the-previous-version}

Vuelva a la imagen que etiquetó en el paso 1 (`promptvault-web:pre-update`). Siga estos pasos en orden.

**1. Inicie la imagen anterior.**

```bash
docker tag promptvault-web:pre-update promptvault-web:latest
docker-compose up -d --no-build web
docker-compose logs web --tail=20
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

El último comando debe mostrar la versión anterior. Compruebe el endpoint de salud (`curl --fail http://localhost:8001/api/health`), inicie sesión y compruebe que sus prompts estén disponibles. Si todo funciona y la actualización no ejecutó migraciones de la base de datos, ha terminado. La línea «Actualización» de las [notas de la versión](../release-notes/index.md) de la versión instalada indica si ejecutó migraciones; muchas versiones no tienen ninguna. Si las ejecutó, continúe con el paso 2.

**2. Detenga la aplicación.** Hágalo solo si va a restaurar la base de datos.

```bash
docker-compose stop web
```

**3. Guarde la base de datos actual (opcional).**

Si creó o modificó prompts después de actualizar, guarde la base de datos actual antes de restaurar:

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

**4. Restaure la copia.** La restauración sustituye la base de datos actual: los prompts y otros cambios hechos desde la copia se perderán si no los guardó en el paso 3.

Restaure la copia verificada anterior a la actualización. Sustituya `<ARCHIVO_DE_RESPALDO>` por el nombre del archivo creado en el paso 1, sin el prefijo de carpeta `data/backups/`. Estos comandos eliminan y crean de nuevo la base de datos antes de cargar la copia:

```bash
set -euo pipefail
docker-compose exec -T db psql -U promptvault postgres -c 'DROP DATABASE promptvault;'
docker-compose exec -T db psql -U promptvault postgres -c 'CREATE DATABASE promptvault;'
gzip -dc "data/backups/<ARCHIVO_DE_RESPALDO>" \
  | docker-compose exec -T db psql -U promptvault -d promptvault
```

**5. Inicie de nuevo la imagen anterior y compruébela.**

```bash
docker-compose up -d --no-build web
docker-compose logs web --tail=20
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Inicie sesión y compruebe que sus prompts estén disponibles. Si falla la restauración o el inicio, deténgase y consulte [Solución de problemas](../troubleshooting/index.md).

**Si no etiquetó ninguna imagen en el paso 1,** extraiga la etiqueta de la versión anterior (`git fetch --tags`, luego `git checkout <ETIQUETA_VERSION_ANTERIOR>`) y ejecute `docker-compose build` sin `--no-cache`. Docker puede reutilizar las capas de dependencias en caché, pero nada lo garantiza, así que compruebe la versión y que la aplicación arranca antes de fiarse de ella.

No vuelva atrás extrayendo la versión antigua y reconstruyendo con `--no-cache`. La compilación instala de nuevo sus dependencias, así que el resultado puede diferir de la imagen que usaba, y algunas versiones ya no se pueden reconstruir: una imagen compilada a partir del código fuente de la versión 1.16.0, por ejemplo, falla con PostgreSQL.
