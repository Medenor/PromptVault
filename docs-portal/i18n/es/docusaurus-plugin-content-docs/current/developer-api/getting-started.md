---
title: Realizar sus primeras llamadas a la API
sidebar_position: 2
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Realizar sus primeras llamadas a la API

Lea una página de prompts y después cree y busque un prompt de prueba en su instancia.

## Preparar la prueba {#before-you-start}

Necesita una instancia de prueba, Bash y `curl` con `--json` (7.82 o posterior). Si la autenticación está activa, necesita una cuenta activa y, cuando corresponda, su aplicación de autenticación. Sustituya localmente los marcadores entre corchetes angulares. No comparta contraseñas, tokens ni respuestas de inicio de sesión. Use HTTPS para instancias remotas.

## Definir la dirección de la aplicación {#set-the-application-address}

Use la dirección de la aplicación, no la del portal. El ejemplo corresponde a un despliegue local. Conserve cualquier prefijo de despliegue, sin barra final.

```bash
BASE_URL='http://localhost:8001'
```

## Iniciar sesión {#sign-in}

Omita este paso solo si su instancia aislada ya está configurada con `AUTH_ENABLED=false`; en ese caso, omita la cabecera de autorización en las solicitudes siguientes. No desactive la autenticación para que funcione una integración. Consulte [Configuración](../configuration/index.md).

Envíe las credenciales en JSON:

```bash
curl --silent --show-error --fail-with-body \
  "$BASE_URL/api/auth/login" \
  --json '{"username_or_email":"<USERNAME>","password":"<PASSWORD>"}'
```

Una sesión iniciada devuelve `access_token` y `refresh_token`. Si recibe `challenge_token`, complete la solicitud siguiente con ese token y un código actual de su aplicación de autenticación o un código de recuperación sin usar. El token de verificación no es un token de acceso. Si se exige configurar la 2FA, hágalo primero en la aplicación; consulte [autenticación de dos factores](../user-guide/two-factor-auth.md).

```bash
curl --silent --show-error --fail-with-body \
  "$BASE_URL/api/auth/login/2fa" \
  --json '{"challenge_token":"<CHALLENGE_TOKEN>","code":"<CODE>"}'
```

Copie el `access_token` obtenido. Ejecute este comando, pegue el token y pulse Intro. Bash oculta la entrada y no guarda el propio token en el historial de comandos:

```bash
read -r -s TOKEN
```

## Leer una página de prompts {#read-a-page-of-prompts}

```bash
curl --silent --show-error --fail-with-body --include \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts?page=1&limit=10&item_type=prompt"
```

La respuesta esperada es HTTP 200 con `prompts`, `page`, `limit`, `total_count`, `total_pages`, `has_next` y `has_previous`. `prompts` es un objeto cuyas claves son los identificadores, no una lista. Una página vacía es válida. Con autenticación activa, los resultados dependen de su identidad y sus permisos.

## Crear un prompt de prueba {#create-a-disposable-prompt}

Esta solicitud crea datos. Use una cuenta de prueba y contenido ficticio. La creación acepta campos de formulario, no JSON:

```bash
curl --silent --show-error --fail-with-body --include \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts" \
  --data-urlencode 'title=API tutorial' \
  --data-urlencode 'prompt=Summarize this sample text.' \
  --data-urlencode 'tags=api-tutorial'
```

Espere HTTP 201 con `{"success":true,"prompt_id":...}`. Copie ese `prompt_id` en el comando siguiente:

```bash
PROMPT_ID='<PROMPT_ID>'
```

## Buscar y consultar versiones {#search-and-inspect-versions}

La búsqueda utiliza `search`, no `q`. Use `item_type=prompt` para excluir skills de la lista y la búsqueda.

```bash
curl --silent --show-error --fail-with-body --get \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts/search" \
  --data-urlencode 'search=API tutorial' \
  --data-urlencode 'item_type=prompt'
```

```bash
curl --silent --show-error --fail-with-body \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts/$PROMPT_ID/versions"
```

La respuesta del historial contiene `versions`. Consulte las rutas de modificación, restauración y eliminación en la [referencia](reference.md). Elimine únicamente su prompt de prueba. Al terminar, retire el token local con `unset TOKEN`; esto no revoca la sesión del servidor. Si una llamada falla, consulte la [ayuda para errores](reference.md#resolve-a-failed-call) antes de repetirla.
