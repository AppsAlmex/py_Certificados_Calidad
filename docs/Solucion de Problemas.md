# Solución de Problemas

Guía rápida para resolver los problemas más frecuentes.

---

## La aplicación no abre / parpadea y se cierra

**Causa más común:** se está ejecutando el `.exe` sin los archivos que lo
acompañan.

- Asegúrate de **extraer el ZIP completo** a una carpeta.
- Ejecuta `CertificadosCalidad.exe` **desde esa carpeta** (debe estar junto a la
  carpeta `_internal` y los archivos `config.ini`, `layouts`, `catalogos`).
- No ejecutes el `.exe` desde dentro del ZIP ni lo copies solo a otro lugar.

Si aun así se cierra, revisa el archivo **error.log** que la app deja junto al
`.exe`: contiene el detalle del error.

---

## "Windows protegió tu PC" (SmartScreen)

Es un aviso de Windows para programas sin firma digital. No es un virus.

- Presiona **Más información → Ejecutar de todos modos**.

---

## El antivirus lo bloquea o lo borra

Los ejecutables generados con estas herramientas a veces dan **falso positivo**.

- Agrega una **exclusión** para la carpeta de la aplicación en tu antivirus.

---

## Error de credenciales / autenticación

- Abre **Configuración → Configuración** y verifica **Usuario** y **Contraseña**.
- Guarda y vuelve a intentar.

---

## No hay conexión al servicio

- Revisa tu conexión a Internet / VPN.
- Abre **Configuración → Health check** y córrelo: te dice si el servicio
  responde y qué falla.
- Si los reportes tardan mucho, sube el **Read timeout** en Configuración.

---

## Una fila del CSV falla (ERROR / INVALIDO)

- El proceso **continúa** con las demás.
- Abre la pestaña **Logs**, selecciona la ejecución y revisa el **mensaje** de esa
  fila para saber la causa.
- **INVALIDO** = falta un dato obligatorio o un valor no es válido.

---

## Falta una opción en Inspector / Planta / Formato

Las listas vienen de los CSV en la carpeta `catalogos`.

1. Edita el CSV correspondiente (`inspector.csv`, `planta.csv`, `formato.csv`).
   Columnas: `valor,descripcion`.
2. En **Configuración → Catálogos**, presiona **Recargar y validar catálogos**.
3. Verifica que no aparezcan problemas (valores vacíos o duplicados).

---

## El motor "local" da error

- El motor local necesita componentes adicionales incluidos en la distribución.
- Si no están, usa el motor **oracle** (funciona siempre) o pide la distribución
  con el motor local incluido.
