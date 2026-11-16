---
title: Usar la API existente
sidebar_position: 1
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Usar la API existente

La interfaz de programación de aplicaciones (API) permite conectar scripts y herramientas con PromptVault. Este espacio está dirigido a quienes utilizan un terminal y solicitudes HTTP. Para trabajar en la aplicación, consulte la [guía del usuario](../user-guide/prompt-management.md). Para desplegar o configurar el servidor, siga [Instalación](../installation/index.md) y [Configuración](../configuration/index.md).

## Elegir un punto de partida {#choose-your-starting-point}

- [Realizar sus primeras llamadas a la API](getting-started.md): leer, crear y buscar un prompt de prueba.
- [Referencia de la API](reference.md): consultar operaciones, formatos, permisos y soluciones a errores.

## Abrir la referencia de su instancia {#open-the-reference-on-your-instance}

El portal de documentación y la aplicación pueden tener direcciones distintas. En la dirección de la **aplicación**, abra:

| Ruta            | Uso                                     |
| --------------- | --------------------------------------- |
| `/docs`         | Referencia interactiva de la API        |
| `/redoc`        | Vista alternativa de la referencia      |
| `/openapi.json` | Descripción de la API para herramientas |

Si la aplicación está en `http://localhost:8001`, abra `http://localhost:8001/docs`. Conserve cualquier prefijo de dirección indicado para su despliegue.

Puede leer estas guías sin una instancia en ejecución. Para enviar solicitudes necesita una aplicación disponible y las credenciales que esta exija. **Try it out** envía solicitudes reales. Use prompts de prueba para modificar o eliminar datos.

## Conocer el alcance actual {#know-the-current-boundaries}

Las rutas actuales empiezan por `/api/...`, sin `/v1`. Autentique las solicitudes de sus scripts con el token de sesión explicado en el tutorial.

La referencia de la instancia muestra las rutas habilitadas. Las de autenticación y administración no están disponibles cuando la autenticación está desactivada. Algunas descripciones conservan indicaciones antiguas sobre la visibilidad; consulte los permisos en la [referencia](reference.md). Identifique la versión instalada en el pie de la aplicación y consulte las [notas de la versión](../release-notes/index.md).
