---
title: Autenticación de dos factores
sidebar_position: 5
---

# Autenticación de dos factores

## Estado actual

La autenticación de dos factores mediante contraseña de un solo uso basada en tiempo (TOTP) **aún no está disponible** en PromptVault. Es un endurecimiento planificado del sistema de autenticación, incluido en la hoja de ruta del proyecto, pero hoy no existe en la aplicación ningún flujo de inscripción, paso de desafío en el inicio de sesión ni política de aplicación por parte del administrador.

## Lo que ya existe

Aunque el 2FA dedicado aún no está disponible, la pila de autenticación de PromptVault ya incluye varias capas de protección para su cuenta:

- **Hash de contraseñas robusto** (Argon2id) con una política de contraseñas aplicada (longitud mínima y requisitos de clases de caracteres).
- **Bloqueo de cuenta** tras intentos de inicio de sesión fallidos repetidos, durante una duración configurable.
- **Tokens JWT de acceso/actualización de corta duración y rotativos** con detección de reutilización — un token de actualización robado no puede reproducirse indefinidamente.
- **Un límite de sesiones simultáneas por cuenta**, con seguimiento de dispositivo/IP y la posibilidad de revocar cualquier sesión activa.
- **Un flujo de restablecimiento de contraseña sin enumeración** — las solicitudes de restablecimiento nunca revelan si una dirección de correo electrónico tiene una cuenta.

Consulte `docs/AUTHENTICATION_SECURITY.md` del proyecto para todos los detalles sobre estos controles.

## Diseño planificado

La hoja de ruta describe el 2FA TOTP como una inscripción opcional (código QR + secreto, con códigos de recuperación de un solo uso) que inserta un paso de desafío en el inicio de sesión una vez habilitado para una cuenta, más una política de administrador para exigirlo en roles específicos. Los intentos de verificación tendrían límite de tasa, y los eventos de inscripción/desactivación/desafío quedarían registrados en auditoría, de forma coherente con cómo ya se registran hoy otras acciones sensibles a la seguridad en PromptVault.

## Recomendación mientras tanto

Si su implementación necesita hoy una protección más fuerte que una simple contraseña, las opciones prácticas son: mantener `AUTH_ENABLED=true` (nunca ejecute una instancia multiusuario en red con la autenticación deshabilitada), aplicar una política de contraseñas robusta mediante las variables de entorno `PASSWORD_*`, y confiar en el límite de sesiones existente y en los controles de revocación para limitar el alcance de una credencial comprometida. Esta página se actualizará una vez que se publique el soporte de TOTP.
