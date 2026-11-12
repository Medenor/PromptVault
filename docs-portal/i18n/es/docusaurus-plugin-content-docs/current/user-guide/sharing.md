---
title: Compartir prompts
sidebar_position: 3
---

# Compartir prompts

PromptVault admite compartir prompts individuales con compañeros de equipo específicos, con control de acceso de lectura/edición granular.

## Conceder acceso

Desde el modal de compartir de un prompt, puede conceder a un compañero de equipo uno de dos niveles de acceso:

- **Lectura**: ver el prompt y su historial de versiones.
- **Edición**: todo lo que permite la lectura, además de editar el contenido, la categoría y las etiquetas del prompt, y revertir a una versión anterior.

Ninguno de los dos niveles permite eliminar el prompt, volver a compartirlo con otros, alternar el estado de favorito o transferir la propiedad — esas acciones siguen siendo exclusivas del propietario. El selector de destinatarios busca usuarios activos por prefijo de nombre de usuario o correo electrónico, pero nunca muestra ni expone direcciones de correo electrónico en los resultados.

## Revocar acceso

El propietario del prompt puede revocar el acceso en cualquier momento desde el mismo modal de compartir.

## Encontrar prompts compartidos

Un filtro "Compartidos conmigo" muestra los prompts que otras personas han compartido con usted. Los prompts compartidos llevan una insignia distintiva de "Compartido" para que pueda distinguir una compartición explícita de un prompt que simplemente le es visible por defecto.

## Prompts públicos heredados

Los prompts creados antes de que se introdujera la función de compartir quedan clasificados como **"Público (heredado)"** — visibles para cualquier usuario autenticado, no solo para las personas con acceso concedido explícitamente — y se distinguen con una insignia diferente de una compartición explícita. Un propietario o administrador puede hacer privado un prompt público heredado mediante una acción "Hacer privado"; se trata de una transición en un solo sentido sin forma de volver a publicarlo posteriormente como público heredado, así que trátelo como una decisión deliberada y no como una simple opción de visualización.

Los prompts creados después de que se introdujera la función de compartir son **privados** por defecto: visibles solo para su propietario, los administradores y cualquier persona con acceso concedido explícitamente.

## Exportación/importación y compartición

Las concesiones de compartición y el indicador de público heredado **no** se incluyen en los prompts exportados (CSV/Markdown/JSON) — son estado de control de acceso vinculado a las cuentas de usuario de esta instancia específica, no contenido de prompt portátil. Volver a importar un archivo exportado crea prompts privados simples sin ninguna concesión restaurada. Si necesita conservar el estado de compartición, use una copia de seguridad/restauración completa de la base de datos en lugar de exportar/importar.
