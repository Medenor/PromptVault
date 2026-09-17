---
title: Instalación
sidebar_position: 1
---

# Instalación

PromptVault es una aplicación autoalojada. Esta página cubre las dos formas admitidas de ponerla en marcha: el asistente de configuración automatizado y una implementación manual con Docker Compose.

## Requisitos previos

- Python 3.14+
- PostgreSQL 15+ (recomendado para producción) o SQLite (suficiente para desarrollo/uso de un solo usuario)
- Docker y Docker Compose (vía de implementación recomendada)
- Git

## Inicio rápido con el asistente de configuración

La forma más rápida de obtener una instancia funcional es el asistente de configuración incluido, que gestiona de forma interactiva la generación de claves JWT, la configuración del entorno, la creación de la base de datos y la creación del usuario administrador.

```bash
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault
python scripts/setup/setup.py
```

Siga las indicaciones. Al finalizar, PromptVault estará implementado y listo para usarse.

## Configuración manual con Docker Compose

Si prefiere configurar cada paso usted mismo:

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

Una vez que los contenedores estén en ejecución, abra `http://localhost:8001` e inicie sesión con las credenciales de administrador recién creadas.

## Compilar desde el código fuente

Si desarrolla localmente en lugar de implementar mediante Docker, el `Makefile` del repositorio encapsula todo el flujo de compilación/prueba/lint:

```bash
make install   # Dependencias de backend (.venv) y frontend (npm)
make dev       # Backend en el puerto :8003, servidor de desarrollo frontend en :5173
make build     # Activos de frontend de producción + imagen Docker
```

Consulte `docs/DEVELOPMENT.md` del proyecto para la referencia completa de objetivos, variables de entorno y modos de fallo comunes si algún paso no funciona como se espera.

## Crear el usuario administrador

Toda instalación nueva necesita al menos una cuenta de administrador:

```bash
# Docker Compose
docker-compose exec web python scripts/create_admin_user.py

# Local
python scripts/create_admin_user.py
```

El script solicita nombre de usuario, dirección de correo electrónico y contraseña, valida la contraseña según la política configurada y crea un usuario con privilegios de administrador completos. Guarde estas credenciales de forma segura.

## Próximos pasos

- Consulte la [referencia de configuración](../configuration/index.md) para las variables de entorno que probablemente querrá ajustar (límites de tasa, tiempos de espera de sesión, almacenamiento de copias de seguridad).
- Si algo no funciona como se espera, consulte [Solución de problemas](../troubleshooting/index.md).
