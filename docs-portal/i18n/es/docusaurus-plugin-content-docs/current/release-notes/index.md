---
title: Notas de la versión
sidebar_position: 1
---

# Notas de la versión

Aspectos destacados de las versiones recientes de PromptVault. Para el historial completo y sin resumir, consulte `docs/CHANGELOG.md` en el repositorio.

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
