---
title: Etiquetas
sidebar_position: 3
---

# Etiquetas

A diferencia de las categorías, un prompt puede llevar varias etiquetas a la vez, lo que hace que las etiquetas sean más adecuadas para marcadores transversales —como `visible-al-cliente` o `pendiente-de-revisión`— que la agrupación única que ofrece una categoría.

## Crear y asignar etiquetas {#creating-and-assigning-tags}

Una etiqueta tiene un nombre, una descripción opcional, un color opcional y, opcionalmente, una etiqueta padre, lo que permite construir una jerarquía simple de etiquetas (una etiqueta no puede ser su propio padre, y los ciclos se rechazan). Las etiquetas se asignan a un prompt al crearlo o editarlo; escribir el nombre de una etiqueta que aún no existe la crea.

## Filtrar por etiqueta {#filtering-by-tag}

La cuadrícula principal de prompts puede filtrarse por etiqueta para reducir la vista a los prompts que llevan esa marca.

## Mantenimiento masivo de etiquetas {#bulk-tag-maintenance}

La página Gestionar etiquetas ofrece varias operaciones masivas para mantener ordenada tu lista de etiquetas:

- **Fusionar** — combinar una o varias etiquetas de origen en una sola etiqueta de destino, reasignando todos los prompts que tenían una etiqueta de origen.
- **Eliminación masiva** — eliminar varias etiquetas a la vez; eliminar una etiqueta todavía en uso en prompts requiere una confirmación explícita "forzada".
- **Buscar y reemplazar** — renombrar una etiqueta en todas partes a la vez, fusionándola con el reemplazo si ya existe uno con ese nombre.
- **Limpieza de huérfanas** — listar etiquetas sin ningún prompt asociado (etiquetas sin uso) y prompts sin ninguna etiqueta asociada (prompts sin etiquetar), para limpiar ambos lados.

Fusionar, la eliminación masiva y buscar-y-reemplazar pueden deshacerse inmediatamente después de ejecutarse.

## Analítica de etiquetas {#tag-analytics}

Una vista de analítica de etiquetas muestra tus etiquetas más y menos usadas, y qué pares de etiquetas aparecen con más frecuencia juntos en el mismo prompt, útil para detectar etiquetas redundantes o demasiado específicas.
