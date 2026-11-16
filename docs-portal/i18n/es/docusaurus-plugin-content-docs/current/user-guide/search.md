---
title: Búsqueda
sidebar_position: 4
---

# Búsqueda

La búsqueda de PromptVault se ejecuta contra un índice de texto completo real en lugar de un simple escaneo de subcadenas, de modo que los resultados se ordenan por relevancia y se mantienen rápidos a medida que crece su biblioteca de prompts.

## Cómo funciona la clasificación {#how-ranking-works}

Las coincidencias en el **título** de un prompt tienen la mayor ponderación, luego en el **contenido**, luego en la **nota** — de modo que un prompt cuyo título coincide con su consulta aparece por encima de uno que solo menciona el término de pasada. Las consultas de varias palabras simples se combinan con OR: los prompts que coinciden solo con algunas de las palabras siguen apareciendo, aunque clasificados por debajo de los que coinciden con todas.

Si elige explícitamente una opción de ordenación (por ejemplo, ordenar por fecha), esto anula la clasificación por relevancia, ya que ha solicitado un orden específico.

## Resaltado de términos coincidentes {#matched-term-highlighting}

Los resultados de búsqueda incluyen un fragmento resaltado que muestra los términos coincidentes en contexto, para que pueda saber de un vistazo por qué coincidió un prompt determinado sin necesidad de abrirlo.

## Coincidencia exacta y de frase {#exact-and-phrase-matching}

- Las búsquedas con `case_sensitive=true` conservan la coincidencia exacta de mayúsculas/minúsculas.
- Poner una consulta entre comillas (`"frase exacta"`) busca esa frase exacta en lugar de tratarla como palabras separadas combinadas con OR.

## Fiabilidad {#reliability}

Cualquier consulta que PromptVault no pueda interpretar como una búsqueda estructurada (por ejemplo, una compuesta enteramente por operadores de búsqueda sin términos de búsqueda reales) recurre de forma transparente a una búsqueda de subcadena simple en lugar de devolver un error — una búsqueda nunca debería fallar por completo solo por cómo se formuló.

## Rendimiento {#performance}

La búsqueda se mantiene rápida a medida que crece su biblioteca: la latencia de las consultas permanece prácticamente constante en lugar de degradarse linealmente con el número de prompts almacenados, ya que el índice subyacente — no un escaneo completo — realiza el trabajo de coincidencia.
