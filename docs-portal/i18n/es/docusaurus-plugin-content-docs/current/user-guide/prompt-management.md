---
title: Gestionar prompts
sidebar_position: 1
---

# Gestionar prompts

La página principal de PromptVault es una cuadrícula de tarjetas: cada prompt visible se muestra como una tarjeta, y el trabajo diario —crear, editar, eliminar y marcar como favorito— se realiza directamente desde esa cuadrícula.

## Crear un prompt

Crear un prompt requiere un título y el propio contenido del prompt; la categoría y las etiquetas son opcionales. El primer guardado también crea la versión inicial del prompt, registrada con un mensaje de commit (por defecto "Initial commit" si no proporcionas uno), para que aparezca desde el principio en el [historial de versiones](./versioning.md) de ese prompt.

## Editar un prompt

Editar el título, contenido, categoría o etiquetas de un prompt crea una nueva versión en lugar de sobrescribir silenciosamente la anterior — cada guardado queda registrado, y siempre puedes consultar (o volver a) una versión anterior. Eliges el mensaje de commit para cada edición, igual que en la creación inicial.

## Eliminar un prompt

Eliminar un prompt es un borrado suave: el prompt se oculta de la cuadrícula, pero sus datos y todo su historial de versiones se conservan en lugar de destruirse por completo, de modo que la recuperación sigue siendo posible. Solo el propietario del prompt o un administrador pueden eliminarlo.

## Marcar como favorito

Cualquier prompt puede marcarse como favorito desde su tarjeta, lo que te permite filtrar la cuadrícula para mostrar solo los prompts que más usas. Solo el propietario del prompt puede alternar su estado de favorito — marcar como favorito es un indicador personal, no compartido.

## Filtrar y explorar

Además de los favoritos, la cuadrícula puede filtrarse por [categoría](./categories.md), por [etiqueta](./tags.md) o por una consulta de [búsqueda](./search.md), y los resultados se paginan — consulta [Paginación](./pagination.md) para saber cómo funciona "Cargar más" en bibliotecas grandes.
