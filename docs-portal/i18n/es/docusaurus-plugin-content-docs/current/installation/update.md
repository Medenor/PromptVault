---
title: Actualizar PromptVault
description: Actualice de forma segura una instalación de PromptVault autohospedada.
---

# Actualizar PromptVault

Estos pasos corresponden a la instalación con Docker Compose descrita en [Instalación](index.md). Actualizan los servicios `web` y `docs` y conservan la base de datos y su volumen con nombre.

## Antes de empezar

1. Lea las [notas de la versión](../release-notes/index.md) para conocer los cambios que afectan a su instalación.
2. Compruebe que el servidor tenga espacio suficiente para una copia de seguridad y las nuevas imágenes.
3. Reserve un breve periodo de mantenimiento. Es posible que los usuarios no puedan iniciar sesión durante el reinicio.
4. Compruebe que puede acceder a la carpeta del proyecto en el servidor y al contenedor de la base de datos.

## 1. Hacer una copia de seguridad

Cree y compruebe un volcado comprimido de la base de datos antes de descargar o iniciar la actualización:

```bash
mkdir -p data/backups
docker compose exec -T db pg_dump -U promptvault -d promptvault \
  | gzip > "data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
gzip -t data/backups/*.sql.gz
```

Compruebe que el archivo más reciente no esté vacío y que `gzip -t` termine sin errores. Guarde la copia en un lugar seguro. No continúe si la copia ha fallado.

## 2. Descargar y reconstruir

Desde la carpeta del proyecto PromptVault, obtenga la versión que desea instalar. Use la etiqueta de versión de las notas si no quiere la última versión de desarrollo:

```bash
git fetch --tags
git checkout <release-tag>
```

Reconstruya y reinicie los servicios de la aplicación y de la documentación:

```bash
docker compose build web docs
docker compose up -d db redis
docker compose up -d web docs
```

La base de datos y Redis deben estar en buen estado antes de iniciar la aplicación. Compose espera las comprobaciones de estado configuradas en el proyecto.

## 3. Aplicar las migraciones

Ejecute las migraciones con la imagen web actualizada:

```bash
docker compose exec -T web alembic upgrade head
docker compose exec -T web alembic current
```

El segundo comando muestra la revisión actual. Si la migración falla, deténgase y consulte [Solución de problemas](../troubleshooting/index.md).

## 4. Comprobar la actualización

```bash
curl --fail http://localhost:8001/api/health
```

El endpoint de salud debe responder correctamente. Abra PromptVault en el navegador, inicie sesión y compruebe que sus prompts estén disponibles. Abra también el servicio de documentación si lo usa (dirección predeterminada: `http://localhost:7876`).

## Si algo falla

Revise primero los registros de los servicios:

```bash
docker compose logs --tail=100 web docs
```

Una reconstrucción sin caché puede revelar una dependencia de Python ausente si su versión no está fijada correctamente. Por ejemplo, la restricción de versión de SQLAlchemy corregida en las notas relacionadas con el [ticket #94](https://codeberg.org/medenor/promptvault/issues/94) evita un problema conocido al instalar `psycopg`. Para otros síntomas, consulte [Solución de problemas](../troubleshooting/index.md).

### Restaurar la copia de seguridad

Si no se puede usar la nueva versión, vuelva a la versión anterior de la aplicación y restaure el volcado verificado. La restauración reemplaza el contenido actual de la base de datos. Guarde primero una copia del estado actual si contiene datos nuevos.

```bash
docker compose stop web
# Copie el archivo de respaldo al servidor si hace falta y luego:
docker compose exec -T db psql -U promptvault -d promptvault \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
gzip -dc data/backups/<archivo-de-respaldo>.sql.gz \
  | docker compose exec -T db psql -U promptvault -d promptvault
```

Después de restaurar, inicie los servicios `web` y `docs` de la versión anterior. Para obtener ayuda, consulte [Solución de problemas](../troubleshooting/index.md).
