---
title: Notas de la versión
sidebar_position: 1
---

# Notas de la versión

Aspectos destacados de las versiones recientes de PromptVault. Para el historial completo y sin resumir, consulte `docs/CHANGELOG.md` en el repositorio.

Consulte [Actualizar PromptVault](../installation/update.md) para ver los pasos de actualización.

## 1.17.0

- **Corrección**: las instalaciones con PostgreSQL en la versión 1.16.0 no arrancaban (`No module named 'psycopg'`). PromptVault ahora incluye el controlador psycopg v3. Su `DATABASE_URL` no necesita cambios: funcionan tanto `postgresql://` como `postgresql+psycopg2://`. SQLite no se ve afectado.
- **Corrección de seguridad**: PyJWT se actualizó a la 2.15.1. Un token con JSON muy anidado hacía que los puntos de acceso de renovación, cierre de sesión y 2FA respondieran con un error del servidor en lugar de un 401. Los tokens enviados en el cuerpo de una petición se limitan ahora a 4096 caracteres. PromptVault solo acepta tokens ES256, así que los demás avisos de seguridad de PyJWT no le afectan.
- **Refuerzo**: el restablecimiento de contraseña ya no devuelve el token en texto claro a quien lo invoca y registra una dirección de correo enmascarada en lugar de la real.
- **Interfaz**: en cada tarjeta de prompt, Copiar es ahora la acción principal (azul) y Editar la secundaria. Historial, Copiar + versión, Compartir y Eliminar están en un menú «Más acciones». El encabezado es neutro en todas las páginas. Se corrigió el modo oscuro en insignias, avisos, botones, enlaces del pie de página y la estrella de favoritos. Si falla la primera carga de la lista de prompts, ahora se muestra un error con un botón «Reintentar».
- **Actualización**: reconstruya las imágenes y reinicie. No hace falta ninguna migración de base de datos.

## 1.16.0

- **Corrección de seguridad**: la solicitud de restablecimiento de contraseña ahora responde igual exista o no la cuenta, y el enlace de restablecimiento ya no se escribe en los registros de la aplicación. Los enlaces caducan a la hora, pero puedes borrar las líneas de registro antiguas que contengan `reset-password?token=`.
- **Corrección**: `setup_env.py --from-file` ahora acepta valores YAML sin comillas (`true`, `20`) y conserva el valor por defecto de las claves que faltan en el archivo. `DB_POOL_SIZE` se comprueba como un número positivo y no como un puerto.
- **Asistente de instalación**: sus dependencias (`click`, `rich`, `httpx`) pasan al extra `setup`, y la imagen de Docker ya no las instala. Ejecuta `pip install -e ".[setup]"` (o `make install`) antes de `scripts/setup/setup.py`.
- **Build**: compilar el frontend ahora requiere Node.js 26 o superior.
- **Actualización**: reconstruye las imágenes y reinicia. No hace falta ninguna migración de la base de datos.

## 1.15.0

- **Guías para desarrolladores de la API**: un nuevo espacio Desarrollador / API explica cómo llamar a la API de PromptVault: primeras llamadas (inicio de sesión con 2FA, lectura, creación, búsqueda, historial) y una referencia de rutas, permisos, paginación y errores. Consulte [Desarrollador / API](../developer-api/index.md).
- **Guía de actualización**: el portal ahora incluye una guía para hacer copias de seguridad, actualizar, comprobar y restaurar una instalación de Docker Compose. Consulte [Actualizar PromptVault](../installation/update.md).
- **Volver a PromptVault**: todas las páginas tienen un enlace de vuelta a la aplicación. Defina `DOCS_APP_URL` al construir la imagen de documentación para que enlace a su instancia.
- **Ahora en GitHub**: el código fuente, las incidencias y las versiones se han trasladado de Codeberg a https://github.com/Medenor/PromptVault, y el enlace del pie de página lo sigue.

## 1.14.1

- **Corrección**: los diálogos de importación y edición de skills ahora respetan el modo oscuro en lugar de mostrarse sobre fondo blanco.

## 1.14.0

- **Skills**: PromptVault ahora almacena skills (un archivo `SKILL.md` con scripts, referencias y otros archivos) junto a tus prompts. Importa un skill desde un `.zip` con **Nuevo ▾ → Importar skill**, explora sus instrucciones renderizadas y su árbol de archivos, edita sus detalles, reemplaza sus archivos, descárgalo como `.zip` o elimínalo. Los skills se pueden buscar, filtrar por tipo y se incluyen en las copias de seguridad de la base de datos. El historial de versiones, el uso compartido, los marcadores de posición y la importación/exportación masiva aún no se aplican a los skills. Consulta la nueva página Skills de la guía de usuario.
- **Menús de la cabecera**: «Nuevo prompt» e «Importar skill» comparten ahora el menú **Nuevo ▾**, y los enlaces secundarios pasan a un menú **Más ▾** en pantallas de ancho medio, para que la navegación quepa en una línea.
- **Corrección de seguridad**: la actualización masiva de etiquetas ahora comprueba que eres propietario (o administrador) de cada elemento seleccionado.
- **Actualización**: aplica la migración de la base de datos y reconstruye las imágenes. Puede ser necesario recargar la página una vez para obtener las nuevas traducciones.

## 1.13.1

- **Corrección**: reconstruir la imagen de Docker sin caché ya no falla con `No module named 'psycopg'` (la dependencia de SQLAlchemy ahora está limitada a versiones inferiores a 2.1).
- **Corrección**: el enlace de Documentación del menú de la aplicación ahora funciona en los despliegues con Docker. La pila de Docker incluye un servicio `docs` que sirve el portal en el puerto 7876. Tras actualizar, reconstruya ambas imágenes: `docker-compose build web docs && docker-compose up -d docs web`.

## 1.13.0

- **Autenticación de dos factores (contraseña de un solo uso basada en tiempo, TOTP), opcional**: los usuarios pueden activar una app de autenticación desde su perfil y recibir códigos de recuperación de un solo uso. Los administradores pueden exigir 2FA por rol.
- **Enlace al portal de documentación**: el menú de la aplicación ahora enlaza al portal de documentación. La URL de despliegue se configura mediante `VITE_DOCS_PORTAL_URL`; el desarrollo local utiliza `http://localhost:7876`.
- **Búsqueda de texto completo con clasificación por relevancia**: la búsqueda ahora se ejecuta contra un índice de texto completo real en lugar de un simple escaneo de subcadenas, con resultados clasificados por relevancia y fragmentos de coincidencia resaltados.
- **Versión de la aplicación mostrada en el pie de página**.
- Varias correcciones de fiabilidad del backend (fallo del informe de cobertura en plantillas, portabilidad de migraciones, limpieza de código muerto).

## 1.12.0

- **Compartición de prompts y colaboración en equipo**: los propietarios de prompts ahora pueden conceder a compañeros de equipo acceso de lectura o edición a prompts individuales, con un filtro "Compartidos conmigo" y una distinción clara entre una compartición explícita y un prompt visible por defecto. El estado de compartición no se incluye intencionalmente en la exportación/importación — use una copia de seguridad/restauración completa si necesita conservarlo.
- **Cambio de visibilidad**: los prompts nuevos son privados por defecto; los prompts que existían antes de esta versión quedaron clasificados como "Público (heredado)" y pueden hacerse privados (de forma irreversible) por su propietario o un administrador.
- Gran refactorización interna de plantillas y módulos TypeScript sobredimensionados — sin cambios de comportamiento visibles para el usuario.
- **Seguridad**: límite de tasa extendido de los endpoints de autenticación a todos los endpoints que cambian estado o son costosos (importar/exportar, copias de seguridad, acciones masivas), ahora realmente por usuario en lugar de accidentalmente global. Se corrigieron varios riesgos de XSS almacenado por el uso inseguro de `innerHTML`.

## 1.11.0

- Parches de seguridad de dependencias (Jinja2, python-multipart y otras) que cierran 24 CVE conocidos.
- Nuevo trabajo de CI de auditoría de seguridad que ejecuta escaneos de vulnerabilidades de dependencias en cada push/PR.
- **Marcadores de posición dinámicos en prompts**: el contenido de los prompts puede contener tokens tipo `[NOMBRE]`/`{NOMBRE}` que se rellenan al copiar.

## 1.10.0

- Paginación del lado del servidor para la lista de prompts, de modo que las bibliotecas grandes se cargan página a página en lugar de todo el conjunto de datos a la vez.
- **Sistema mejorado de copias de seguridad y restauración**: cifrado, almacenamiento en la nube (compatible con S3, Google Drive, Dropbox), programación y registro de auditoría para copias de seguridad, además de varias correcciones de seguridad relacionadas con copias de seguridad (path traversal, XSS almacenado, endpoints no autenticados).
- Selector de idioma global añadido al encabezado de todas las páginas.
- Nuevo Makefile de flujo de trabajo para desarrolladores (`make install`, `make dev`, `make test`, `make lint`, `make build`) como punto de entrada único para tareas comunes.
- Mejoras de interfaz responsive para móviles: navegación optimizada para pantallas táctiles, soporte sin conexión e instalabilidad como aplicación web progresiva.

## 1.9.0

- **Versionado semántico de prompts**: los prompts pueden recibir un número de versión opcional `MAJOR.MINOR.PATCH` al crearlos o editarlos.
