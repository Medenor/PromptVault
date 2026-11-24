---
title: Configurar un entorno de producción
description: Separar los ajustes de producción de los de desarrollo y sustituir la contraseña predeterminada de la base de datos.
---

# Configurar un entorno de producción

Siga estos pasos en el servidor que ejecuta PromptVault con Docker Compose. Docker Compose lee el archivo `.env` que está junto a `docker-compose.yml`, el mismo que usa para desarrollo, por lo que un ajuste de desarrollo como `ENVIRONMENT=development` o `DISABLE_RATE_LIMITING=true` puede llegar a sus contenedores de producción. Estos pasos dejan los ajustes de producción en su propio archivo.

## Usar un archivo de entorno independiente {#use-a-separate-environment-file}

Ejecute estos comandos desde la carpeta del proyecto PromptVault. Asegúrese de que Git ignora el archivo nuevo antes de que contenga secretos:

```bash
echo '.env.production' >> .gitignore
cp .env .env.production

sed -i.bak \
  -e 's/^ENVIRONMENT=.*/ENVIRONMENT=production/' \
  -e 's/^LOG_LEVEL=.*/LOG_LEVEL=WARNING/' \
  -e 's/^DISABLE_RATE_LIMITING=.*/DISABLE_RATE_LIMITING=false/' \
  .env.production && rm .env.production.bak
grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)=' .env.production
```

El último comando debe mostrar `ENVIRONMENT=production`, `LOG_LEVEL=WARNING` y `DISABLE_RATE_LIMITING=false`. Si falta alguna variable en el resultado, añádala a `.env.production`.

Indique a Docker Compose que use el archivo nuevo. Hágalo una vez en cada ventana de terminal que use para producción; todos los comandos `docker-compose` de esa ventana lo usarán a partir de entonces:

```bash
export COMPOSE_ENV_FILES=.env.production
docker-compose up -d
```

`COMPOSE_ENV_FILES` requiere Docker Compose 2.24 o posterior (compruébelo con `docker-compose version`). Con una versión anterior, añada en su lugar `--env-file .env.production` a cada comando `docker-compose`.

Docker Compose pasa a los contenedores solo estas variables del archivo:

- `ENVIRONMENT`, `LOG_LEVEL`, `DISABLE_RATE_LIMITING` y `POSTGRES_PASSWORD`
- `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` y `JWT_REFRESH_TOKEN_EXPIRE_SECONDS`
- `DOCS_APP_URL` y `VITE_DOCS_PORTAL_URL`

Los demás valores de `.env` (como `DATABASE_URL`) solo se aplican cuando ejecuta PromptVault directamente en un equipo, no con Docker Compose. La página [Configuración](../configuration/index.md) describe cada variable.

`ENVIRONMENT=production` puede aplicar un comportamiento más estricto que el de desarrollo. Tras el cambio, lea `docker-compose logs --tail 30 web` y corrija lo que indique.

## Comprobar los ajustes en uso {#check-the-settings-in-use}

Muestre los ajustes que usa el contenedor en ejecución:

```bash
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)='
```

El resultado debe mostrar `ENVIRONMENT=production`, `LOG_LEVEL=WARNING` y `DISABLE_RATE_LIMITING=false`. Si muestra valores de desarrollo, el contenedor se inició sin el archivo de producción: defina `COMPOSE_ENV_FILES` como se indica arriba y ejecute de nuevo `docker-compose up -d`.

`docker-compose config` imprime `POSTGRES_PASSWORD` en texto claro, así que no pegue su salida en ningún sitio.

## Sustituir la contraseña predeterminada de la base de datos {#replace-the-default-database-password}

Si `POSTGRES_PASSWORD` no está definida, Docker Compose usa en silencio `changeme`. Solo los contenedores de la misma red de Docker pueden llegar a la base de datos, pero sustituya igualmente el valor predeterminado.

PostgreSQL lee `POSTGRES_PASSWORD` solo cuando crea por primera vez el volumen de datos, así que cambiar solo la variable **no** cambia la contraseña de una base de datos existente. Cámbiela primero en la base de datos y después en Compose:

```bash
# 1. Genere una contraseña sin caracteres especiales (pasa a formar parte de una URL de conexión)
NEWPW=$(openssl rand -hex 24)

# 2. Cámbiela en la base de datos
docker exec promptvault-db psql -U promptvault -d promptvault -c "ALTER USER promptvault PASSWORD '$NEWPW'"

# 3. Guárdela para Compose y recree los contenedores de inmediato
echo "POSTGRES_PASSWORD=$NEWPW" >> .env.production
docker-compose up -d
```

Hágalo en un momento tranquilo: entre los pasos 2 y 3, el contenedor web sigue con la contraseña antigua y las conexiones nuevas fallan durante unos segundos. Haga una copia de seguridad nueva después.

Compruebe el resultado desde el contenedor web, no desde el contenedor de la base de datos. La imagen de la base de datos confía en las conexiones hechas desde dentro de su propio contenedor, así que una prueba allí acepta cualquier contraseña. Ejecute los dos comandos:

```bash
# La contraseña antigua debe ser rechazada
docker exec promptvault-web python -c "import psycopg; psycopg.connect(host='db', user='promptvault', password='changeme', dbname='promptvault', connect_timeout=5)" >/dev/null 2>&1 && echo "old password: ACCEPTED" || echo "old password: rejected"

# La contraseña actual debe funcionar
docker exec promptvault-web python -c "import os, psycopg; psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5)" >/dev/null 2>&1 && echo "current password: works" || echo "current password: FAILED"
```

Salida esperada: `old password: rejected` y después `current password: works`. Si la contraseña sustituida no era `changeme`, indíquela en su lugar en el primer comando.

Guarde `.env.production` en un lugar seguro, por ejemplo un gestor de contraseñas: contiene la única copia de la contraseña fuera de la base de datos.
