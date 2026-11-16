---
title: Versionado de prompts
sidebar_position: 1
---

# Versionado de prompts

PromptVault mantiene un historial completo, al estilo de Git, de cada prompt, para que nunca pierda de vista cómo evolucionó y siempre pueda revertir a una versión anterior.

## Versionado automático {#automatic-versioning}

Cada vez que guarda un cambio en un prompt, PromptVault crea automáticamente una nueva versión que registra:

- Un identificador de versión único
- Una marca de tiempo
- El autor del cambio
- Un mensaje de confirmación que describe qué cambió
- Una instantánea completa del prompt en ese momento

No necesita hacer nada para habilitar esto — ocurre en cada actualización.

## Ver el historial de versiones {#viewing-version-history}

Abra el historial de versiones de cualquier prompt mediante:

- El atajo de teclado `Cmd+H` (Mac) o `Ctrl+H` (Windows/Linux)
- El botón "Historial de versiones" en el editor de prompts

La ventana de historial enumera cada versión de la más reciente a la más antigua, con su mensaje de confirmación y metadatos, un cuadro de búsqueda para encontrar una versión específica y acciones rápidas para comparar o revertir.

## Comparar versiones {#comparing-versions}

Desde la ventana de historial de versiones, seleccione dos versiones cualesquiera para ver una comparación detallada de todos los campos del prompt (título, contenido, categoría, etiquetas, notas).

Los campos de texto usan resaltado de diferencias a nivel de carácter en lugar de a nivel de línea, de modo que las ediciones pequeñas — una corrección tipográfica, un cambio de puntuación, una sola palabra añadida — sean fáciles de detectar en lugar de quedar sepultadas en un muro de "línea modificada". Las inserciones aparecen resaltadas en verde, las eliminaciones tachadas en rojo, y el texto sin cambios permanece neutro.

## Revertir a una versión anterior {#reverting-to-a-previous-version}

Desde la vista de comparación o de historial, puede revertir un prompt a cualquier versión anterior. Revertir crea una **nueva** versión que contiene el contenido antiguo — no elimina el historial, por lo que la propia reversión también queda registrada y puede deshacerse revirtiendo de nuevo.

## Por qué esto importa {#why-this-matters}

Si está iterando sobre un prompt y una nueva variante rinde peor, siempre puede volver a lo que funcionaba sin tener que recordar ni volver a escribir manualmente la redacción anterior.
