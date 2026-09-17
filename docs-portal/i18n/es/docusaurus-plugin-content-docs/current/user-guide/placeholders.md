---
title: Marcadores de posición
sidebar_position: 4
---

# Marcadores de posición

Los marcadores de posición convierten un prompt estático en una plantilla reutilizable: escribe un token entre corchetes como `[DURATION]` o entre llaves como `{DURATION}` en cualquier parte del contenido de un prompt, y PromptVault te pedirá que lo rellenes al copiar el prompt.

## Sintaxis reconocida

El nombre de un marcador de posición debe tener 2 o más caracteres formados por letras mayúsculas, dígitos, guiones bajos o espacios — por ejemplo `[DURATION]`, `[TYPE OF PRESENTATION]` o `{MAX_RETRIES}`. Los tokens en minúsculas, con mayúsculas y minúsculas mezcladas, o con guiones (como `[Duration]` o `[YYYY-MM-DD]`) **no** se reconocen como marcadores de posición y se dejan como texto sin más, al igual que los corchetes sueltos que no forman un par bien emparejado.

`[DURATION]` y `{DURATION}` se tratan como dos marcadores de posición distintos, aunque compartan nombre — la sintaxis de corchetes y la de llaves no se fusionan.

## Rellenar valores al copiar

Al hacer clic en Copiar en un prompt que contiene marcadores de posición se abre un formulario con un campo de entrada por cada marcador distinto, en lugar de copiar de inmediato. Si el mismo marcador aparece varias veces en el prompt, sigue recibiendo un único campo — el valor introducido reemplaza cada aparición. Confirmar dejando algunos o todos los campos vacíos igualmente copia con éxito; el token de un campo dejado en blanco se copia sin cambios, en su forma original.

Los prompts sin marcadores de posición se copian al instante, exactamente igual que antes — el formulario solo aparece cuando realmente hay algo que rellenar.

## Los marcadores de posición en el resto de PromptVault

Fuera del flujo de copia, un token de marcador de posición se trata como texto ordinario en todos los demás lugares: el [historial de versiones](./versioning.md) guarda el contenido bruto de cada versión con los tokens intactos, la [búsqueda](./search.md) y el filtrado por categoría/etiqueta tratan el texto del marcador de posición como cualquier otro texto, y el contenido [exportado](./import-export.md) contiene los tokens originales, sin sustituir. Las vistas de historial de versiones y de comparación son de solo lectura y nunca muestran el formulario de relleno de marcadores — para copiar una versión anterior con valores rellenados, primero revierte a ella y luego usa la acción de Copiar habitual.
