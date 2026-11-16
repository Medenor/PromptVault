---
title: Importar y exportar
sidebar_position: 7
---

# Importar y exportar

Exporte prompts para mover su contenido entre instancias o conservar una copia portátil de su biblioteca. Una exportación no es una copia de seguridad completa: no conserva los permisos de compartición. Use una copia de seguridad completa cuando necesite preservar el estado de control de acceso.

## Formatos de exportación {#export-formats}

Los prompts se exportan en **CSV**, **Markdown** o **JSON**. La exportación en JSON produce el formato de envoltura propio de PromptVault, que es también el formato que el importador reconoce automáticamente al reimportar.

## Modos de importación {#import-modes}

Antes de importar, identifique el modo que corresponde al resultado deseado. Elija **Reemplazar** solo si pretende sustituir toda la biblioteca.

- **Añadir** — cada prompt del archivo se añade, incluso si ya existe un prompt con el mismo título (puede crear duplicados).
- **Fusionar** — un prompt del archivo solo se añade si ningún prompt existente tiene ya exactamente ese título; en caso contrario se omite.
- **Reemplazar** — primero se vacía toda la biblioteca de prompts existente y luego se añade cada prompt del archivo. PromptVault crea una copia de seguridad antes de la importación. Confirme que la copia se completó antes de depender de ella para recuperar la biblioteca anterior.

## El estado de los permisos compartidos no es portable {#sharing-state-is-not-portable}

La importación/exportación nunca incluye los permisos de compartición de prompts — consulta [Compartir](./sharing.md#exportimport-and-sharing) para saber por qué, y cuál es la alternativa recomendada cuando necesitas conservar ese estado.

## Estadísticas de importación y exportación {#importexport-statistics}

Una vista de estadísticas de importación/exportación muestra las cifras de uso actuales de ambas operaciones, útil para confirmar que una importación o exportación grande realmente se completó como se esperaba.
