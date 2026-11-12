---
title: Autenticación de dos factores
sidebar_position: 5
---

# Autenticación de dos factores

La autenticación de dos factores (2FA) añade una comprobación más al iniciar sesión. Tras tu contraseña, PromptVault pide un código de 6 dígitos de una app de autenticación, o uno de tus códigos de recuperación. La 2FA es opcional para la mayoría de usuarios. Los administradores pueden exigirla para roles concretos.

## Activar la 2FA

1. Abre tu perfil y busca la tarjeta **Autenticación de dos factores**. Selecciona **Configurar la autenticación de dos factores**.
2. Escanea el código QR con una app de autenticación como Google Authenticator, Authy o 1Password. Si no puedes escanearlo, despliega **¿No puedes escanear el código?** y escribe a mano la **clave de configuración** en la app.
3. Introduce el código de 6 dígitos que muestra tu app y selecciona **Verificar y activar**.
4. Guarda tus códigos de recuperación. PromptVault los muestra solo una vez: 10 códigos. Cópialos o descárgalos como archivo de texto y guárdalos en un lugar seguro.

La 2FA no se activa hasta que completes el paso 3. Si vuelves a empezar la configuración antes de confirmarla, la nueva clave de configuración sustituye a la anterior.

## Iniciar sesión con 2FA

1. Introduce tu contraseña como de costumbre.
2. En la pantalla **Autenticación de dos factores**, introduce el código de 6 dígitos de tu app y selecciona **Verificar**.

El paso de inicio de sesión caduca a los 2 minutos. Si caduca, vuelve a empezar desde el paso de la contraseña.

Los códigos de la app cambian cada 30 segundos. Un código también funciona un intervalo antes o después de la hora actual, así que un reloj de teléfono ligeramente desajustado sigue sirviendo.

## Iniciar sesión con un código de recuperación

En la misma pantalla, introduce un código de recuperación en lugar del código de la app. Los códigos de recuperación tienen el formato `xxxx-xxxx`. Cada código funciona una sola vez. Después de usarlo, deja de funcionar para siempre.

Usa un código de recuperación para volver a entrar si pierdes el teléfono. Después, regenera tus códigos.

## Regenerar los códigos de recuperación

Desde tu perfil, selecciona **Regenerar códigos de recuperación**. Introduce tu contraseña actual y un código actual de la app o un código de recuperación. PromptVault crea 10 códigos nuevos. Todos los anteriores dejan de funcionar de inmediato.

## Desactivar la 2FA

Desde tu perfil, selecciona **Desactivar la autenticación de dos factores**. Introduce tu contraseña actual y un código actual de la app o un código de recuperación. Al desactivarla se eliminan tu configuración de 2FA y todos los códigos de recuperación restantes. A partir de entonces, inicias sesión solo con tu contraseña.

## Exigir 2FA para un rol

En la sección **Política de autenticación de dos factores** de la administración, elige qué roles (lector, editor, administrador) deben usar 2FA. Un cambio se aplica en el siguiente inicio de sesión de cada usuario. No cierra las sesiones existentes.

- Un usuario de un rol obligatorio que no ha configurado 2FA pasa a un paso de configuración justo después de iniciar sesión. No puede usar el resto de la aplicación hasta completar la configuración.
- Un usuario de un rol obligatorio que ya tiene 2FA inicia sesión con el paso de código habitual.
- Quitar un requisito no elimina la configuración de 2FA existente de nadie.

## Si pierdes la app y los códigos de recuperación

En este caso PromptVault no puede restablecer la 2FA por ti. Hoy no hay ninguna opción de administración que quite la 2FA de una cuenta. Ponte en contacto con la persona que administra tu servidor de PromptVault, y guarda tus códigos de recuperación en un lugar seguro para no llegar nunca a esta situación.

## Notas de seguridad

- Tu configuración de 2FA se guarda cifrada. Los códigos de recuperación se guardan de forma que no se pueden leer de nuevo, por lo que no pueden volver a mostrarse.
- Los códigos incorrectos cuentan para el mismo bloqueo que las contraseñas incorrectas. Demasiados intentos fallidos bloquean la cuenta durante un breve periodo.
- El registro de auditoría recoge la activación o desactivación de 2FA, la regeneración de códigos de recuperación y los cambios en el requisito de un rol.
- PromptVault limita la frecuencia con la que se pueden intentar la configuración, la verificación, la desactivación y la regeneración. Si ves un mensaje sobre demasiados intentos, espera un minuto e inténtalo de nuevo.
- El operador del servidor debe definir `TOTP_ENCRYPTION_KEY`. Consulta [Configuración](../configuration/index.md).
