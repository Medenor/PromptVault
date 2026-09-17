---
title: Importar y exportar
sidebar_position: 7
---

# Importar y exportar

Los prompts pueden exportarse a un archivo y reimportarse más tarde, ya sea como copia de seguridad portátil de tu propia biblioteca o para mover prompts entre instancias.

## Formatos de exportación

Los prompts se exportan en **CSV**, **Markdown** o **JSON**. La exportación en JSON produce el formato de envoltura propio de PromptVault, que es también el formato que el importador reconoce automáticamente al reimportar.

## Modos de importación

Al importar un archivo, eliges cómo interactúa con tus prompts existentes:

- **Añadir** — cada prompt del archivo se añade, incluso si ya existe un prompt con el mismo título (puede crear duplicados).
- **Fusionar** — un prompt del archivo solo se añade si ningún prompt existente tiene ya exactamente ese título; en caso contrario se omite.
- **Reemplazar** — primero se vacía toda tu biblioteca de prompts existente, y luego se añade cada prompt del archivo. PromptVault crea automáticamente una copia de seguridad antes de ejecutar una importación de reemplazo, para que el estado anterior no se pierda.

## El estado de los permisos compartidos no es portable

La importación/exportación nunca incluye los permisos de compartición de prompts — consulta [Compartir](./sharing.md#exportaciónimportación-y-compartición) para saber por qué, y cuál es la alternativa recomendada cuando necesitas conservar ese estado.

## Estadísticas de importación y exportación

Una vista de estadísticas de importación/exportación muestra las cifras de uso actuales de ambas operaciones, útil para confirmar que una importación o exportación grande realmente se completó como se esperaba.
