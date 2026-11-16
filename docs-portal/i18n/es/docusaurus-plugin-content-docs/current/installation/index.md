---
title: Instalación
sidebar_position: 1
---

# Instalación

PromptVault es una aplicación autoalojada: se ejecuta en una infraestructura que usted controla. Elija el asistente de configuración si quiere que la aplicación cree la configuración necesaria de forma interactiva. Elija la vía manual solo si sabe editar variables de entorno y ejecutar comandos de Docker.

## Requisitos previos {#prerequisites}

- Python 3.14+
- PostgreSQL 15+ (recomendado para producción) o SQLite (suficiente para desarrollo/uso de un solo usuario)
- Docker y Docker Compose (vía de implementación recomendada)
- Git

## Inicio rápido con el asistente de configuración {#quick-start-with-the-setup-wizard}

La forma más rápida de obtener una instancia funcional es el asistente de configuración incluido. Crea claves de firma JSON Web Token (JWT), configura el entorno, prepara la base de datos y crea una cuenta de administrador.

```bash
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault
python scripts/setup/setup.py
```

Siga las indicaciones. Al finalizar, abra la dirección que se muestra e inicie sesión con las credenciales de administrador creadas.

## Configuración manual con Docker Compose {#manual-docker-compose-setup}

Use esta vía solo si necesita controlar cada ajuste. Ejecute los comandos en orden: los comandos posteriores usan los archivos y servicios creados en los pasos anteriores.

```bash
# Clonar el repositorio
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault

# Configurar el entorno
cp .env.example .env
# Edite .env y defina POSTGRES_PASSWORD (y otros valores según sea necesario)

# Generar las claves de firma JWT para la autenticación
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem

# Hacer que .env apunte a las claves generadas
echo "JWT_PRIVATE_KEY_PATH=$(pwd)/es256-private.pem" >> .env
echo "JWT_PUBLIC_KEY_PATH=$(pwd)/es256-public.pem" >> .env

# Iniciar los servicios (PostgreSQL + PromptVault)
docker-compose up -d

# Ejecutar las migraciones de base de datos
docker-compose exec web alembic upgrade head

# Crear el usuario administrador predeterminado
docker-compose exec web python scripts/create_admin_user.py

# (Opcional) Migrar datos JSON existentes
docker-compose exec web python scripts/migrate_json_to_db.py
```

Cuando los contenedores estén en ejecución, abra `http://localhost:8001` e inicie sesión con las credenciales de administrador creadas. Si la página no se abre, consulte [Solución de problemas](../troubleshooting/index.md) antes de cambiar datos o volúmenes de Docker.

## Compilar desde el código fuente {#building-from-source}

Si desarrolla localmente en lugar de implementar mediante Docker, el `Makefile` del repositorio encapsula todo el flujo de compilación/prueba/lint:

```bash
make install   # Dependencias de backend (.venv) y frontend (npm)
make dev       # Backend en el puerto :8003, servidor de desarrollo frontend en :5173
make build     # Activos de frontend de producción + imagen Docker
```

Consulte `docs/DEVELOPMENT.md` del proyecto para la referencia completa de objetivos, variables de entorno y modos de fallo comunes si algún paso no funciona como se espera.

## Crear el usuario administrador {#creating-the-admin-user}

Toda instalación nueva necesita al menos una cuenta de administrador:

```bash
# Docker Compose
docker-compose exec web python scripts/create_admin_user.py

# Local
python scripts/create_admin_user.py
```

El script solicita nombre de usuario, dirección de correo electrónico y contraseña, valida la contraseña según la política configurada y crea un usuario con privilegios de administrador completos. Guarde estas credenciales de forma segura.

- Para actualizar una instalación existente, siga la guía [Actualizar PromptVault](update.md).
## Próximos pasos {#next-steps}

- Consulte la [referencia de configuración](../configuration/index.md) para las variables de entorno que probablemente querrá ajustar (límites de tasa, tiempos de espera de sesión, almacenamiento de copias de seguridad).
- Si algo no funciona como se espera, consulte [Solución de problemas](../troubleshooting/index.md).
