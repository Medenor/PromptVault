---
title: Solución de problemas
sidebar_position: 4
---

# Solución de problemas

Esta página cubre los problemas más comunes al instalar o ejecutar PromptVault. Para una cobertura exhaustiva, consulte `docs/TROUBLESHOOTING.md` del proyecto.

## Puerto ya en uso

Si el puerto `8001` (web), `5432` (PostgreSQL) o `6379` (Redis) ya está ocupado por otro proceso, `docker-compose up` no podrá iniciar ese servicio. Detenga el proceso en conflicto o cambie el puerto asignado en su `.env`/`docker-compose.yml` antes de volver a intentarlo.

## El demonio de Docker no está en ejecución

Los comandos `docker-compose` fallan con un error de conexión si Docker mismo no está en ejecución. Inicie Docker Desktop (o el servicio `docker` en Linux) y vuelva a intentarlo.

## Fallo de conexión a la base de datos

Si PromptVault no puede conectarse a PostgreSQL al iniciar:

- Confirme que el contenedor/servicio realmente está en ejecución (`docker-compose ps`).
- Verifique que `DATABASE_URL` en `.env` coincida con las credenciales y el host/puerto en el que PostgreSQL realmente está escuchando.
- Si acaba de cambiar `POSTGRES_PASSWORD`, recuerde que los contenedores existentes con un volumen de datos ya inicializado no adoptarán automáticamente la nueva contraseña — es posible que deba recrear el volumen para una instalación limpia, o actualizar la contraseña dentro de la base de datos existente en su lugar.

## Fallos de migración

Si `alembic upgrade head` falla a mitad de camino:

- Vuelva a ejecutarlo — la mayoría de las migraciones están escritas para ser idempotentes.
- Si una migración falla específicamente en una base de datos SQLite recién creada con un error SQL específico de PostgreSQL, probablemente esté usando una versión desactualizada — versiones recientes corrigieron migraciones que usaban SQL específico de un dialecto no portátil, así que asegúrese de no estar usando un commit antiguo.
- Nunca edite el esquema de la base de datos manualmente para evitar un fallo de migración — abra un issue con el error exacto en su lugar, ya que las ediciones manuales del esquema hacen que las migraciones futuras sean impredecibles.

## Errores de clave JWT

Si la aplicación no se inicia y se queja de claves JWT faltantes o inválidas, confirme que `JWT_PRIVATE_KEY_PATH`/`JWT_PUBLIC_KEY_PATH` apunten a un par de claves ES256 válido generado con:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem
```

Las claves generadas con una curva o algoritmo diferente no funcionarán — PromptVault espera específicamente ES256 (P-256/prime256v1).

## Bloqueado tras inicios de sesión fallidos

Los intentos de inicio de sesión fallidos repetidos activan un bloqueo temporal de la cuenta (`MAX_LOGIN_ATTEMPTS`, 5 intentos por defecto, `ACCOUNT_LOCKOUT_DURATION_SECONDS`, 15 minutos por defecto). Espere a que termine la ventana de bloqueo, o pida a un administrador que la reinicie, en lugar de volver a intentarlo repetidamente — reintentar durante un bloqueo no reinicia el temporizador antes de tiempo.

## Errores de límite de tasa (429)

Si las operaciones masivas, importaciones/exportaciones o acciones de copia de seguridad devuelven `429 Too Many Requests`, ha alcanzado uno de los límites de tasa por usuario descritos en [Configuración](../configuration/index.md#límite-de-tasa). La respuesta incluye un encabezado `Retry-After`; espere esa ventana, o pida a un administrador que aumente la variable `RATE_LIMIT_*` correspondiente si el valor predeterminado es realmente demasiado bajo para su flujo de trabajo.

## La importación/exportación no restaura la compartición

Si importa un archivo previamente exportado y los prompts compartidos vuelven a ser privados sin ninguna concesión, esto es esperado — la exportación/importación intencionalmente no transporta el estado de compartición (vea [Compartir prompts](../user-guide/sharing.md#exportaciónimportación-y-compartición)). Use una copia de seguridad/restauración completa en su lugar si necesita conservar la compartición.

## ¿Sigue atascado?

Consulte el `docs/TROUBLESHOOTING.md` completo en el repositorio, o abra un issue en [Codeberg](https://codeberg.org/medenor/promptvault) con el mensaje de error exacto y el comando que ejecutó.
