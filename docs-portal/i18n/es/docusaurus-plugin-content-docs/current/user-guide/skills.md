---
title: Skills
sidebar_position: 4
---

# Skills

Un skill es una carpeta de instrucciones y archivos de apoyo que un agente de IA puede cargar para realizar una tarea. Siempre incluye un archivo `SKILL.md` y puede incluir también scripts, referencias y otros archivos. PromptVault guarda los skills junto a tus prompts para que puedas organizar, buscar, respaldar y exportar ambos en un solo lugar.

## Qué es un skill

Un skill se guarda como un archivo `.zip`. El archivo `SKILL.md` empieza con un encabezado breve (el nombre y una descripción) seguido de las instrucciones. PromptVault sigue el formato abierto Agent Skills.

En la lista de la bóveda, un skill muestra una insignia **Skill** y una descripción breve en lugar del cuerpo de un prompt. Usa el filtro **Tipo** sobre la lista para ver solo prompts o solo skills.

## Importar un skill

1. Elige **Importar skill** en la cabecera.
2. Selecciona un archivo `.zip`. El `SKILL.md` puede estar en la raíz del archivo o dentro de una única carpeta de primer nivel.
3. Si quieres, añade una categoría y etiquetas, y elige **Importar**.

El skill se guarda en un solo paso: si algo falla con el archivo, no se guarda nada. Cuando la importación funciona, el skill se abre de inmediato.

## Avisos de formato

PromptVault acepta skills aunque no sigan el formato al pie de la letra. Entonces verás un aviso que enumera cada regla incumplida, por ejemplo un nombre ausente, un nombre que no está en minúsculas con guiones, una descripción de más de 1.024 caracteres o un `SKILL.md` colocado en la raíz del archivo en lugar de dentro de una carpeta. Los avisos permanecen en la vista de detalle del skill. Nunca bloquean una importación.

## Límites y archivos rechazados

Un archivo se rechaza, y no se guarda nada, cuando:

- no es un archivo zip válido o está cifrado;
- no tiene `SKILL.md` en su raíz ni en una única carpeta de primer nivel;
- contiene una ruta que sale de la carpeta del skill, un enlace simbólico, una ruta duplicada o un nombre de archivo no válido en los sistemas habituales;
- supera un límite de tamaño de subida (10 MB por defecto), de tamaño descomprimido (50 MB), de número de archivos (500), de profundidad de carpetas (10 niveles) o de tamaño de un archivo (10 MB).

El mensaje indica qué regla se incumple y, cuando corresponde, qué entrada la causó. Los administradores pueden cambiar los límites con los ajustes `SKILL_*` de la guía de despliegue.

## Explorar un skill

La vista de detalle muestra la descripción, las instrucciones ya formateadas y la lista de archivos como un árbol. Las carpetas van primero. Puedes recorrer el árbol con las flechas, abrir una carpeta con la flecha derecha y elegir un archivo con Intro.

Los archivos de texto se muestran como texto de solo lectura. Los archivos binarios muestran su tamaño y un enlace de descarga. Nada de un skill se ejecuta ni se muestra nunca como una página web, y marcadores como `${CLAUDE_SKILL_DIR}` siguen siendo texto sin formato.

## Descargar un skill

**Descargar skill** te da `<nombre-del-skill>.zip` con una sola carpeta dentro, en la disposición estándar. Cada archivo es idéntico al que importaste. El nombre del archivo usa el identificador del skill, así que cambiar el título no lo modifica. También puedes descargar un solo archivo desde el visor.

## Editar, reemplazar y eliminar

- **Editar detalles** cambia el título, la categoría, las etiquetas, la nota y el favorito. Los archivos no se tocan y no se crea historial de versiones.
- **Reemplazar archivos** sube un archivo nuevo. Se conservan el título, la nota, las etiquetas, la categoría y el favorito; la descripción y el identificador provienen del nuevo `SKILL.md`. Si el archivo nuevo se rechaza, el skill queda exactamente como estaba.
- **Eliminar skill** quita el skill y todos sus archivos de forma definitiva. No se puede deshacer, así que se te pide confirmación.

## Búsqueda, copias de seguridad y lo que los skills no hacen

La búsqueda encuentra un skill por su título, su nota y el texto de su `SKILL.md`. No mira dentro de los scripts ni de otros archivos incluidos. Los skills se incluyen en las copias de seguridad completas de la base de datos y vuelven idénticos tras una restauración.

Los skills son privados para quien los importó. No tienen historial de versiones, ni uso compartido, ni marcadores de posición, y la exportación masiva de prompts no los incluye: exporta un skill desde su propia vista.
