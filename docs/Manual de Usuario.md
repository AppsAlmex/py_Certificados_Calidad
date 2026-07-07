# Manual de Usuario — Certificados de Calidad

Aplicación para generar certificados de calidad de forma masiva (desde un CSV) o
uno por uno (con un formulario), consultando el sistema Oracle BI Publisher.

---

## 1. Antes de empezar

- Recibes una **carpeta** con la aplicación. **Extrae el ZIP completo** antes de
  usarla y ejecuta desde la carpeta extraída. No copies solo el `.exe` ni lo
  ejecutes desde dentro del ZIP (no funcionaría).
- Abre **CertificadosCalidad.exe** (doble clic).
- La primera vez, revisa **Configuración** (botón arriba) y confirma tus datos de
  acceso (usuario/contraseña) en la pestaña Configuración.

---

## 2. Pantalla principal

Arriba está el botón **Configuración (Settings)** y abajo tres pestañas.

### Pestaña "Ejecución (CSV)" — generación masiva

1. **Archivo CSV**: presiona *Examinar…* y elige tu archivo de solicitudes.
2. **Reporte**: elige el reporte a usar.
3. **Workers**: cuántos certificados generar a la vez (1 = uno por uno). Súbelo
   para ir más rápido cuando hay muchos.
4. **Motor de PDF**: `oracle` (PDF original) o `local` (plantilla propia).
5. **Ejecutar**: inicia el proceso. La **barra** muestra el avance real
   (por ejemplo 3/10 = 30%).
6. **Detener**: cancela; la solicitud en curso termina y no se lanzan más.
7. El **registro en vivo** muestra el detalle; al terminar ves un resumen.

### Pestaña "Certificado individual" — uno por uno

1. Llena el formulario (mismos campos del CSV). Inspector, Planta y Formato son
   listas; Cantidades van de 1 a 10.
2. **Agregar a la cola**: el certificado entra a la lista "Certificados en proceso".
3. Repite para agregar varios.
4. En **Opciones de envío** elige Reporte, Workers y Motor.
5. **Procesar cola**: genera los certificados en cola. Cada fila cambia de estado:
   En cola → Procesando → OK / ERROR / INVALIDO.
6. Botones: *Detener*, *Quitar seleccionado*, *Limpiar completados*.

### Pestaña "Logs" — historial

- Lista de ejecuciones anteriores (más recientes primero) con el reporte usado y
  los conteos OK / Error / Inválido.
- Al seleccionar una, abajo ves el **detalle por certificado** (con colores) y el
  **log completo** en texto.

---

## 3. Configuración (Settings)

Botón **Configuración (Settings)** arriba. Abre una ventana con pestañas:

### Configuración
Datos internos: servidor, tiempos de espera (timeout), carpetas de salida y logs,
credenciales (usuario/contraseña), catálogo de reportes, workers por defecto y
motor de PDF. Presiona **Guardar y aplicar**; al cerrar, la app revalida y avisa.

### Catálogos
Las listas de Inspector, Planta y Formato salen de archivos CSV en la carpeta
`catalogos`. Para personalizarlas, edita esos CSV (columnas `valor,descripcion`) y
usa **Recargar y validar catálogos**: verás cuántas opciones tiene cada uno y si
hay problemas (valores vacíos o duplicados).

### Health check
Corre un **chequeo general** de la app y muestra si todo está bien: configuración,
reportes, catálogos, carpetas, y conexión al servicio. Úsalo si algo no funciona.

### Info
Esta ayuda. Aquí puedes leer los manuales.

---

## 4. Formato del CSV

Encabezados (una fila por certificado):

```
embarque,formato,inspector,observaciones,planta_prod,tanque,
sello1,cantidad1,sello2,cantidad2,sello3,cantidad3,sello4,cantidad4,
formato_salida,nombre_archivo
```

- Obligatorios: `embarque`, `formato`, `inspector`, `planta_prod`, `tanque`.
- Valores con comas van entre comillas dobles, ej. `"MARSHALL, MN"`.
- `formato_salida`: `pdf` (por defecto), `xml` o `xlsx`.

Los archivos generados quedan en la carpeta **output**.

---

## 5. Motor de PDF

- **oracle**: usa el PDF original del sistema (comportamiento estándar).
- **local**: la app arma el PDF con una plantilla propia (más control visual).
  Requiere que la app se haya distribuido con el motor local incluido.

Puedes elegir el motor en cada ejecución (pestañas de Ejecución e Individual).

---

## 6. Problemas comunes

- **"parpadea y cierra" al abrir**: estás corriendo el `.exe` sin su carpeta
  completa. Extrae todo el ZIP y ejecuta desde la carpeta.
- **Error de credenciales**: revisa usuario/contraseña en Configuración.
- **No hay conexión**: revisa tu red/VPN; usa Health check para confirmar.
- **Una fila sale ERROR**: el resto continúa; revisa el mensaje en Logs.
- **Falta una opción en una lista**: edita el CSV del catálogo y usa
  "Recargar y validar catálogos".

Para más detalle técnico, consulta el documento de Solución de Problemas.
