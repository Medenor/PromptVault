---
title: Copias de seguridad
sidebar_position: 2
---

# Copias de seguridad

PromptVault incluye funciones de copia de seguridad y restauración para copias programadas, verificación de integridad, cifrado y almacenamiento opcional en la nube. Una copia de seguridad ayuda a recuperar datos; una exportación no la sustituye cuando se deben conservar los permisos de compartición.

## Copias de seguridad programadas

Los administradores configuran las copias de seguridad automáticas desde la página de gestión de copias de seguridad. Elija una programación diaria, semanal o mensual y una hora; después active la programación. Si una copia programada se iniciara mientras otra sigue en ejecución, PromptVault omite la nueva ejecución y registra esa decisión.

La primera copia de seguridad de una instalación (o la primera después de que una copia anterior deje de ser utilizable) siempre es una copia completa; las copias de seguridad programadas posteriores son incrementales, almacenando solo lo que cambió desde la última copia completa para mantener bajo el uso de almacenamiento.

## Verificación de integridad

El contenido de cada copia de seguridad se valida después de crearla, y el resultado se registra. Se almacena una suma de comprobación junto a los metadatos de cada copia de seguridad para poder volver a verificar su integridad más adelante. También puede activar manualmente una prueba de integridad en cualquier copia de seguridad existente en cualquier momento desde la página de gestión de copias de seguridad — útil antes de necesitar realmente confiar en una restauración.

## Cifrado

Las copias de seguridad se pueden cifrar con una clave que usted proporcione antes de escribirlas en el almacenamiento; PromptVault nunca almacena claves de cifrado en texto plano. Se admite la rotación de claves — las copias de seguridad ya cifradas con una clave anterior permanecen accesibles durante la transición a una nueva.

## Almacenamiento en la nube

Puede configurar un proveedor compatible con S3, Google Drive o Dropbox como destino de copia de seguridad desde la interfaz de administración. Siempre se conserva una copia local incluso cuando se configura la carga a la nube, y puede restaurar directamente desde el almacenamiento en la nube, no solo desde copias de seguridad locales.

Las credenciales del proveedor de la nube (clave de acceso/clave secreta) se cifran en reposo usando `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` — vea [Configuración](../configuration/index.md#copias-de-seguridad). Esta variable es obligatoria antes de poder añadir un proveedor de nube.

## Vista previa de restauración y restauración selectiva

Antes de aplicar una restauración, revise la vista previa: enumera los prompts que se añadirán, actualizarán o eliminarán. Seleccione solo los prompts que pretende restaurar, o restaure la copia de seguridad completa. No aplique la restauración hasta entender los cambios indicados.

## Retención

Un período de retención configurable (en días) determina cuándo las copias de seguridad más antiguas quedan disponibles para su limpieza, de modo que el almacenamiento de copias de seguridad no crezca sin límite.

## Notas prácticas

- Mantenga `PROMPTVAULT_DATA_DIR` distinto por entorno (dev/staging/prod) — compartir un directorio de datos entre entornos puede hacer que las copias de seguridad y restauraciones programadas colisionen entre sí, ya que las copias de seguridad se almacenan en relación con ese directorio.
- Pruebe una restauración de vez en cuando, no solo una copia de seguridad — la verificación de integridad confirma que el archivo de copia de seguridad es legible, pero solo una ejecución completa de vista previa de restauración confirma que los datos que contiene son realmente los que espera.
