---
title: Referencia de la API
sidebar_position: 3
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Referencia de la API

Consulte aquí las familias de rutas existentes. Abra `/docs` en su **aplicación**, no en el portal documental, para ver el esquema completo de la instancia. Para una guía práctica, empiece por [sus primeras llamadas](getting-started.md).

## Autenticación y permisos

Envíe `Authorization: Bearer <ACCESS_TOKEN>` en sus scripts. El inicio de sesión y la renovación aceptan JSON. La creación y modificación de prompts aceptan campos de formulario.

Los tokens de acceso caducan a los 15 minutos por defecto. Envíe el último token de renovación a `POST /api/auth/refresh` como `{"refresh_token":"<REFRESH_TOKEN>"}`. Sustituya **ambos** tokens tras renovar. Reutilizar un token antiguo puede revocar la sesión; no renueve en paralelo. `POST /api/auth/logout` acepta el token de renovación actual en JSON para cerrar esa sesión.

Con autenticación activa, la lista y la búsqueda solo devuelven elementos visibles para usted. Sin credenciales, o con un token no válido o caducado, pueden devolver una página vacía en lugar de 401. Una página vacía no confirma que la autenticación haya tenido éxito. La propiedad, el rol de administración, los permisos compartidos y la visibilidad heredada determinan el acceso. Un permiso de edición permite modificar y restaurar, pero no eliminar ni gestionar el uso compartido. Consulte [Compartir](../user-guide/sharing.md). Los skills tienen reglas propias; consulte [Skills](../user-guide/skills.md).

## Encontrar una operación

Sustituya `{id}` por el identificador de un prompt y `{version_id}` por un identificador de su historial. La tabla sirve de orientación; no enumera todas las operaciones administrativas.

| Operación                                     | Ruta                                                                                                           |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Listar / buscar                               | `GET /api/prompts` · `GET /api/prompts/search`                                                                 |
| Crear / leer / modificar / eliminar           | `POST /api/prompts` · `GET /api/prompts/{id}` · `PUT /api/prompts/{id}` · `DELETE /api/prompts/{id}`           |
| Leer el historial / una versión               | `GET /api/prompts/{id}/versions` · `GET /api/prompts/{id}/versions/{version_id}`                               |
| Restaurar una versión                         | `POST /api/prompts/{id}/versions/{version_id}/revert`                                                          |
| Gestionar el uso compartido de prompts        | `POST /api/prompts/{id}/shares` · `GET /api/prompts/{id}/shares` · `DELETE /api/prompts/{id}/shares/{user_id}` |
| Importar / consultar / descargar skills       | `POST /api/skills/import` · `GET /api/skills/{id}` · `GET /api/skills/{id}/download`                           |
| Leer categorías / tags                        | `GET /api/categories` · `GET /api/tags`                                                                        |
| Importar / exportar prompts                   | `POST /api/import` · `POST /api/export`                                                                        |
| Gestionar copias de seguridad                 | `GET /api/backups` · `POST /api/backups`                                                                       |
| Gestionar cuentas / sesiones / programaciones | `/api/admin/users` · `/api/admin/sessions` · `/api/admin/scheduler/...`                                        |

Consulte los permisos y formatos de las operaciones administrativas en la referencia de la instancia.

Los campos de formulario de creación y modificación son `title`, `prompt`, `category`, `tags`, `commit_message` y, opcionalmente, `semantic_version`. `title` y `prompt` son obligatorios en ambos casos. Separe los tags con comas. Una restauración acepta el campo opcional `commit_message` y crea una entrada de historial. La eliminación retira datos: úsela solo en elementos que quiera eliminar.

## Recorrer los resultados

La lista y la búsqueda usan `page=1` y `limit=50` por defecto, con un máximo de 100 elementos por página. Continúe mientras `has_next` sea `true`. El objeto `prompts` usa identificadores como claves. `item_type` acepta `all`, `prompt` o `skill`; los skills omiten el cuerpo `prompt`. `filter=shared-with-me` limita los resultados a los permisos compartidos explícitos.

La búsqueda acepta `search`, `category`, `tag`, `favorites`, `case_sensitive` y `ranked`. No muestre fragmentos de búsqueda como HTML sin escapar. Consulte la [guía de búsqueda](../user-guide/search.md) para entender las coincidencias.

## Resolver una llamada fallida

Examine el estado HTTP y la respuesta. Según la operación, los errores usan `detail`, `error` o un mensaje estructurado. Un prompt inexistente puede devolver `{"detail":"Prompt with ID 123 not found"}`.

| Estado | Causa que comprobar                                               | Acción                                                                                     |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 401    | Credenciales ausentes, no válidas o caducadas                     | Inicie sesión o renueve una vez con el último token de renovación.                         |
| 403    | Permisos insuficientes o configuración 2FA obligatoria incompleta | Revise los permisos y complete la configuración en la aplicación.                          |
| 404    | Ruta incorrecta o desactivada, elemento ausente u oculto          | Revise la dirección, el identificador y el acceso; no dé por hecho que el elemento existe. |
| 409    | Operación incompatible con el tipo de elemento                    | Use rutas de skills para skills y rutas exclusivas de prompts para sus funciones.          |
| 422    | Campos ausentes, formato incorrecto o valores no válidos          | Lea los errores de campos; envíe formularios para crear o modificar prompts.               |
| 429    | Límite de solicitudes alcanzado                                   | Espere los segundos indicados en `Retry-After` antes de repetir.                           |

Los límites dependen de la operación y del servidor; consulte [Configuración](../configuration/index.md). Tras un tiempo de espera agotado, compruebe si la modificación se completó antes de repetirla. Para problemas de conexión o del servidor, consulte [Solución de problemas](../troubleshooting/index.md).
