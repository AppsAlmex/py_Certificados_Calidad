---
titulo: "Manual de Usuario — Certificados de Calidad"
doc_id: "MAN-CERT-001"
type: manual
version: "1.0"
estado: Draft
autor: "GetseAvila — Desarrollo"
owner: "Departamento de TI"
area: "Departamento de TI"
fecha: 2026-07-31
updated: 2026-07-31
next_review: 2027-07-31
clasificacion: Interno
app_version_verificada: "v1.2.3"
tags: [manual, certificados-calidad]
related: []
---

> **Verificado contra la versión v1.2.3.** Regenerar/revisar tras cada release.

# Introducción

**Certificados de Calidad** es la aplicación de escritorio que permite generar certificados de calidad y etiquetas de producto consultando directamente el sistema corporativo. Puede trabajar de dos formas:

- **Uno por uno:** ingresa el número de lote o pedido y genera el certificado en el momento.
- **De forma masiva:** carga un archivo CSV con varios registros y la aplicación genera todos los documentos en un solo paso.

**¿Para quién es este manual?**
Está dirigido al operador de planta y al inspector de calidad que utilizan la aplicación en su día a día. No se requieren conocimientos técnicos para completar las tareas descritas aquí.

Con este manual podrá resolver la mayor parte de las situaciones que se presenten. Cuando un problema exceda lo indicado en la sección **Solución de problemas**, el manual le indicará cuándo es el momento de contactar al equipo de TI.

![[cert-01-portada.png]]
*Figura 1. Ventana principal de la aplicación Certificados de Calidad.*

# Requisitos

Antes de instalar y usar la aplicación, verifique que cuenta con lo siguiente:

- **Equipo con Windows.** La aplicación funciona en equipos de escritorio o portátiles con sistema operativo Windows.
- **Conexión a la red interna o VPN.** La aplicación necesita comunicarse con el servicio corporativo. Si trabaja fuera de las instalaciones, asegúrese de tener activa la VPN antes de abrirla.
- **Credenciales de acceso.** Necesitará su nombre de usuario y contraseña corporativos para conectarse al servicio.
- **Motor de PDF.** Si la aplicación se instaló con el motor de PDF "local" incluido, podrá generar documentos sin pasos adicionales. Si no es así, utilice la opción **"oracle"** al momento de generar el certificado.

> Si no sabe qué motor de PDF tiene disponible, consulte la sección **Configuración** o contacte a TI.

# Instalación

> **Importante:** No ejecute la aplicación directamente desde dentro del archivo ZIP. Extraiga primero todos los archivos y luego abra el ejecutable desde la carpeta resultante.

Siga estos pasos para instalar la aplicación:

1. **Extraiga el ZIP completo.** Haga clic derecho sobre el archivo ZIP recibido, seleccione *Extraer todo…* y elija una carpeta de destino (por ejemplo, `C:\Aplicaciones\CertificadosCalidad`). Espere a que termine la extracción.

   ![[cert-02-carpeta.png]]
   *Figura 2. Carpeta extraída del ZIP con el ejecutable.*

2. **Abra el ejecutable.** Dentro de la carpeta extraída, haga doble clic sobre **CertificadosCalidad.exe** para iniciar la aplicación.

   ![[cert-03-icono.png]]
   *Figura 3. Icono del ejecutable.*

3. **Primera vez: confirme los datos de acceso.** Al abrir la aplicación por primera vez, diríjase al menú **Configuración (Settings)** y verifique que los datos de acceso al servicio estén correctos (usuario, contraseña y servidor). Guarde los cambios antes de continuar.

# Configuración

La ventana **Configuración (Settings)** se abre con el botón **Settings** ubicado en la barra superior de la aplicación. Dentro encontrará cinco sub-pestañas que agrupan todas las opciones de ajuste. Recuerde pulsar **Guardar y aplicar** después de realizar cualquier cambio.

## Configuración

En esta sub-pestaña se reúnen los parámetros fundamentales para que la aplicación se conecte al servicio corporativo y genere los documentos correctamente.

![[cert-12-config.png]]
*Figura 12. Configuración (Settings) → sub-pestaña Configuración.*

Los campos disponibles son:

- **Host / Servidor:** dirección del servidor corporativo al que se conecta la aplicación (la proporciona TI).
- **Ruta del servicio:** ruta dentro del servidor que identifica el servicio de reportes (la proporciona TI).
- **Connect timeout (seg):** cuántos segundos espera la aplicación para establecer la conexión con el servidor antes de mostrar un error.
- **Read timeout (seg):** cuántos segundos espera la aplicación a que el servidor termine de responder. Si genera reportes largos y obtiene errores de tiempo de espera, TI puede aumentar este valor.
- **Carpeta de salida:** carpeta donde se guardarán los certificados y etiquetas generados.
- **Carpeta de registros (logs):** carpeta donde la aplicación almacena el historial de actividad para diagnóstico.
- **Usuario y Contraseña:** sus credenciales de acceso al servicio corporativo.
- **Verificar certificado TLS:** cuando está activada, la aplicación comprueba que la comunicación con el servidor sea segura. Solo desactívela si TI lo indica explícitamente.
- **Nivel de log:** controla cuánta información se anota en el historial de actividad. Es un desplegable con los valores **DEBUG**, **INFO**, **WARNING** y **ERROR** (INFO es el nivel normal; DEBUG es el más detallado y se usa cuando TI necesita diagnosticar un problema).
- **Reporte por defecto:** el tipo de documento que se seleccionará automáticamente al abrir la pantalla de generación.
- **Número máximo de procesos simultáneos (1–100):** cuántos documentos puede generar la aplicación al mismo tiempo durante un proceso masivo. Un valor más alto acelera la generación pero requiere más recursos del equipo. El valor recomendado para la mayoría de los equipos es **4**.
- **Motor de PDF:** define con qué motor se crea el archivo PDF. Las opciones son **local** (incluido en la instalación) y **oracle** (requiere conexión al servidor).
- **Reportes:** lista de los tipos de documentos disponibles; cada línea asocia un nombre de reporte con la plantilla correspondiente en el servidor. Esta lista la configura TI y no debe modificarse sin su indicación.

Una vez completados todos los campos, haga clic en **Guardar y aplicar**. La aplicación valida los datos al guardar y también al cerrarse; si detecta algún dato incorrecto o faltante, mostrará un aviso indicando qué campo requiere corrección.

## Catálogos

Los catálogos contienen las listas de opciones que usa la aplicación (por ejemplo, la lista de inspectores). Esta sub-pestaña muestra el estado de cada catálogo y le permite mantenerlos actualizados.

![[cert-13-catalogos.png]]
*Figura 13. Sub-pestaña Catálogos con el estado de cada catálogo.*

La tabla principal muestra, por cada catálogo:

| Columna | Descripción |
|---|---|
| **Catálogo** | Nombre del catálogo (por ejemplo, *Inspectores*). |
| **Nº de opciones** | Cuántas entradas tiene actualmente en su equipo. |
| **Estado** | Si está al día o requiere actualización. |
| **Detalle** | Información adicional sobre el estado o el último error. |

Acciones disponibles para cada catálogo:

- **Actualizar desde Oracle:** descarga la lista actualizada desde el servidor y la aplica localmente. Esta acción nunca borra entradas que ya tenga guardadas en su equipo pero que no aparezcan en el servidor. Actualmente solo el catálogo **Inspector** tiene esta función habilitada; los botones de los demás catálogos aparecen deshabilitados hasta que TI configure el reporte correspondiente.
- **Crear archivo por defecto:** genera un archivo de catálogo vacío con la estructura correcta, útil para que TI lo complete manualmente si no existe conexión con el servidor.

> **Recomendación:** actualice el catálogo de Inspectores al comenzar cada jornada o cuando le avisen que se han incorporado nuevos inspectores.

## Health check

La sub-pestaña **Health check** le permite verificar de un vistazo que la aplicación está lista para funcionar correctamente.

![[cert-14-health.png]]
*Figura 14. Sub-pestaña Health check con resultados.*

Al pulsar el botón **Correr health check**, la aplicación revisa automáticamente los siguientes aspectos. Junto al botón hay una casilla marcable **"incluir conectividad al servicio"** que puede activar o desactivar antes de correr el chequeo; cuando está activa, la revisión también prueba la conexión al servidor corporativo.

- **Configuración:** que todos los parámetros obligatorios estén completos.
- **Reportes:** que cada tipo de documento tenga su plantilla asociada.
- **Catálogos:** que los archivos de catálogo existan y sean legibles.
- **Carpetas:** que las carpetas de salida y de registros estén accesibles.
- **Plantillas locales:** que las plantillas de documentos estén presentes y sin daños.
- **Conectividad (opcional):** que la aplicación pueda comunicarse con el servidor corporativo.

El resultado se muestra en una tabla con tres columnas — **Chequeo**, **Estado** (OK o FALLA) y **Detalle** (explicación del resultado) — seguida de un resumen general.

> **Antes de llamar a TI:** ejecute siempre el Health check primero y comuníqueles el resultado. Esto agiliza el diagnóstico y reduce el tiempo de resolución.

## Info / Ayuda

Esta sub-pestaña muestra documentación de referencia directamente dentro de la aplicación, sin necesidad de abrir un navegador o un visor externo.

![[cert-15-info.png]]
*Figura 15. Sub-pestaña Info / Ayuda mostrando este manual.*

Use el selector de documento para elegir el texto que desea consultar (por ejemplo, este manual). El contenido se muestra en modo solo lectura; no puede editarlo desde aquí.

> **Nota:** cuando visualiza el manual dentro de la aplicación, las imágenes aparecen como texto descriptivo en lugar de fotografías. Para ver las imágenes, consulte la versión en PDF o la carpeta de documentación de la instalación.

## Actualizaciones

Desde esta sub-pestaña puede saber si existe una versión más reciente de la aplicación y descargarla sin necesidad de contactar a TI.

![[cert-16-updates.png]]
*Figura 16. Sub-pestaña Actualizaciones.*

La pantalla muestra:

- **Versión instalada:** la versión de la aplicación que tiene actualmente en su equipo.
- **Botón Buscar actualizaciones:** consulta el servidor de actualizaciones y muestra si hay una versión disponible.
- **Notas de la versión disponible:** descripción de las mejoras y correcciones incluidas en la nueva versión.
- **Barra de descarga:** indica el progreso de la descarga cuando inicia la actualización.

> Si el botón **Buscar actualizaciones** no encuentra nada, la aplicación está al día. Si la descarga falla, verifique su conexión a la red o VPN e inténtelo de nuevo.

# Uso

## Vista general

Al abrir la aplicación verá la ventana principal dividida en dos zonas:

- **Barra superior:** muestra el botón **Configuración (Settings)** para ajustar los parámetros de la aplicación y, a la derecha, el número de versión instalada.
- **Área de trabajo con cuatro pestañas:** cada pestaña agrupa una función principal de la aplicación.

| Pestaña | Para qué sirve |
|---|---|
| **Certificado individual** | Generar certificados uno por uno y enviarlos a una cola de procesamiento. |
| **Ejecución por Lote** | Generar varios certificados a la vez cargando un archivo CSV. |
| **Etiqueta** | Generar etiquetas de producto. |
| **Logs** | Consultar el historial de actividad y mensajes de diagnóstico. |

![[cert-04-ventana-completa.png]]
*Figura 4. Ventana principal: barra superior y las cuatro pestañas.*

---

## Certificado individual

Use esta pestaña cuando necesite generar certificados de uno en uno. Cada certificado que complete se agrega a una cola y puede procesarlos todos en un solo paso al final.

### 1. Complete el formulario

Rellene los campos del formulario con los datos del certificado que desea generar:

- **Embarque:** número o código del embarque.
- **Formato:** tipo de plantilla del certificado. Es una lista desplegable con el formato "valor - descripción". Si el valor que necesita no aparece en la lista, puede escribirlo directamente en el campo.
- **Inspector:** nombre del inspector responsable. También es una lista desplegable editable; puede escribir el nombre si no aparece.
- **Observaciones:** texto libre con comentarios adicionales (opcional).
- **Planta producción:** planta donde se originó el producto. Lista desplegable editable.
- **Tanque:** identificador del tanque.
- **Sello 1 – Sello 4:** códigos de sello del embarque (complete los que apliquen).
- **Cantidad 1 – Cantidad 4:** cantidad asociada a cada sello. Seleccione un valor del 1 al 10 en cada lista desplegable.

![[cert-05-form.png]]
*Figura 5. Formulario de Certificado individual.*

> **Limpiar formulario:** si necesita comenzar de nuevo, pulse este botón para vaciar todos los campos del formulario. Los certificados ya agregados a la cola no se eliminan.

### 2. Configure las opciones de envío

Antes de agregar el certificado a la cola, defina cómo se procesará:

- **Reporte:** tipo de documento que se generará.
- **Workers:** cuántos certificados se procesarán simultáneamente al ejecutar la cola. Use un número mayor si tiene varios certificados pendientes y su equipo lo permite.
- **Motor:** seleccione **oracle** para conectarse al servidor corporativo o **local** para usar las plantillas instaladas en su equipo. Con el motor **local**, la lista de **Formato** muestra únicamente los formatos que tienen plantilla disponible localmente.
- **Formato salida:** elija **pdf** o **xml** según el tipo de archivo que necesita.
- **Nombre archivo:** campo opcional. Si lo deja vacío, la aplicación asignará un nombre automáticamente.

### 3. Agregue el certificado a la cola

Pulse **Agregar a la cola**. El certificado aparecerá en la lista **Certificados en proceso** con las columnas:

| Columna | Descripción |
|---|---|
| **Embarque** | Número de embarque ingresado. |
| **Formato** | Tipo de plantilla seleccionada. |
| **Estado** | Estado actual del certificado en la cola. |

![[cert-06-cola.png]]
*Figura 6. Lista "Certificados en proceso" con los estados por fila.*

Repita los pasos 1 a 3 para cada certificado adicional que necesite generar.

### 4. Procese la cola

Cuando haya agregado todos los certificados que desea generar, pulse **Procesar cola**. La aplicación comenzará a procesarlos y el estado de cada fila cambiará en tiempo real:

| Estado | Significado |
|---|---|
| **En cola** | El certificado está esperando su turno. |
| **Procesando** | La aplicación está generando el documento en este momento. |
| **OK** | El certificado se generó correctamente y se guardó en la carpeta de salida. |
| **ERROR** | Ocurrió un problema al generar el documento. Consulte la pestaña **Logs** para ver el detalle. |
| **INVALIDO** | Los datos del certificado no son válidos. Revise el formulario y vuelva a agregarlo. |

Durante el procesamiento dispone de los siguientes botones de control:

- **Detener:** cancela el proceso. Los certificados que ya terminaron conservan su estado; los pendientes quedan en la cola.
- **Quitar seleccionado:** elimina de la lista el certificado que esté seleccionado (haga clic en su fila primero).
- **Limpiar completados:** retira de la lista todos los certificados en estado **OK**, dejando visibles solo los pendientes o con error.

---

## Ejecución por Lote

Use esta pestaña cuando necesite generar muchos certificados a la vez. En lugar de ingresar los datos uno por uno, los prepara en un archivo CSV y la aplicación los procesa todos en un solo paso.

### 1. Prepare el archivo CSV

El archivo debe tener una fila de encabezados seguida de una fila por cada certificado. Los encabezados **obligatorios** son:

| Encabezado | Descripción |
|---|---|
| `embarque` | Número o código del embarque. |
| `formato` | Tipo de plantilla del certificado. |
| `inspector` | Nombre del inspector responsable. |
| `planta_prod` | Planta de producción. |
| `tanque` | Identificador del tanque. |

Los demás campos son opcionales y pueden incluirse o dejarse en blanco según lo que aplique para cada certificado. La columna `formato_salida` acepta los valores **pdf**, **xml** o **xlsx**.

![[cert-08-csv.png]]
*Figura 8. Ejemplo de archivo CSV (encabezados y una fila).*

> **Consejo:** abra el CSV en Excel o en el Bloc de notas para revisarlo antes de cargarlo. Asegúrese de que los encabezados obligatorios estén escritos exactamente como se indica (en minúsculas y sin espacios extra).

### 2. Configure y ejecute el lote

1. Pulse **Examinar…** junto al campo **Archivo CSV** y seleccione el archivo que preparó.
2. Elija el **Reporte**, los **Workers** (cuántos certificados procesar en paralelo) y el **Motor de PDF** que correspondan.
3. Pulse **Ejecutar** para iniciar el proceso.

![[cert-07-lote.png]]
*Figura 7. Pestaña Ejecución por Lote: CSV, barra de progreso y registro en vivo.*

Durante la ejecución:

- La **barra de progreso** muestra el avance del lote. Por ejemplo, si van 3 de 10 certificados, la barra indica el 30 %.
- El **Registro en vivo** muestra el detalle de cada certificado conforme se procesa: nombre del archivo generado, advertencias y errores.

Para cancelar antes de que termine, pulse **Detener**. La solicitud que ya estaba en curso concluirá normalmente; no se iniciarán nuevas solicitudes a partir de ese momento. Los archivos ya generados quedan guardados en la carpeta de salida.

---

## Etiqueta

Use esta pestaña para generar una etiqueta de producto en formato PDF (tamaño 3×2 pulgadas) para **ALMIDONES MEXICANOS S.A. DE C.V.**

### Campos del formulario

Rellene los siguientes siete campos antes de generar la etiqueta:

| Campo | Descripción |
|---|---|
| **Cliente** | Nombre del cliente al que va dirigida la etiqueta. |
| **Sucursal** | Sucursal o destino del producto. |
| **Producto** | Nombre o código del producto. |
| **Transporte** | Número o identificador del transporte. |
| **Lote** | Número de lote del producto. |
| **Equipo** | Equipo o línea de producción involucrado. |
| **Fecha** | Fecha y hora de la etiqueta. Se completa automáticamente con la fecha y hora actuales; puede modificarla si necesita una fecha diferente. |

![[cert-09-etiqueta.png]]
*Figura 9. Pestaña Etiqueta con los datos capturados.*

### Generar y limpiar

- **Generar PDF:** crea el archivo de etiqueta y lo guarda en la carpeta de salida. La aplicación no se congela mientras genera el documento; puede seguir trabajando en otras pestañas.
- **Limpiar:** vacía todos los campos del formulario para que pueda comenzar una captura nueva desde cero.

---

## Logs

La pestaña **Logs** muestra el historial completo de ejecuciones realizadas en la aplicación, con el resultado de cada una.

### Lista de ejecuciones

La tabla principal presenta una fila por cada ejecución, ordenadas de la más reciente a la más antigua:

| Columna | Descripción |
|---|---|
| **Fecha** | Fecha y hora en que se realizó la ejecución. |
| **Reporte** | Tipo de documento que se procesó. |
| **Total** | Número total de registros procesados en la ejecución. |
| **OK** | Cuántos documentos se generaron correctamente. |
| **Error** | Cuántos documentos fallaron. |
| **Inválido** | Cuántos registros tenían datos que no pudieron procesarse. |

![[cert-10-logs.png]]
*Figura 10. Pestaña Logs: lista de ejecuciones.*

### Detalle de una ejecución

Al hacer clic sobre cualquier fila de la lista, el panel inferior muestra el detalle de esa ejecución en dos sub-pestañas:

- **Resultados:** una fila por cada registro procesado, con las columnas Fila, Estado (resaltado con color según el resultado), Formato, Duración, Parámetros, Archivo generado y Mensaje de resultado o error.
- **Log completo:** texto íntegro del registro de actividad de esa ejecución, útil para compartir con TI cuando se necesita diagnosticar un problema.

![[cert-11-detalle.png]]
*Figura 11. Detalle de una ejecución: Resultados y Log completo.*

### Botones disponibles

- **Refrescar:** actualiza la lista de ejecuciones para mostrar las actividades más recientes.
- **Compartir (ZIP):** empaqueta el registro de la ejecución seleccionada en un archivo ZIP listo para enviar. Consulte la subsección **Reportes externos de LOGS** para conocer el proceso completo.

---

## Motor de PDF

Al generar un certificado o ejecutar un lote, puede elegir con qué motor se construye el archivo PDF. Esta opción está disponible en cada pestaña y se aplica únicamente a esa corrida en particular.

### oracle (predeterminado)

La aplicación solicita al sistema corporativo que genere el PDF y le devuelve el documento terminado. Es la opción estándar y funciona con todos los tipos de reporte. Si no tiene una razón específica para cambiarla, deje seleccionada esta opción.

### local

La aplicación arma el PDF por sí misma usando las plantillas instaladas en su equipo. Esto le da mayor consistencia visual en el resultado. Tenga en cuenta lo siguiente:

- Solo aplica cuando el **Formato de salida** es **PDF**. Si elige xml o xlsx, la aplicación utilizará el sistema estándar independientemente del motor seleccionado.
- Solo están disponibles los formatos de documento que cuenten con una plantilla local instalada. Los demás formatos no aparecerán en la lista o se procesarán con el motor oracle automáticamente.

> Si el motor **local** no produce el resultado esperado, cambie a **oracle** e intente de nuevo. Si el problema persiste, contacte a TI.

---

## Actualizaciones automáticas

Al abrir la aplicación, ésta revisa sola si hay una versión más nueva disponible. Si todo está al día, no aparece ningún aviso y puede continuar trabajando normalmente.

Si existe una versión más reciente, la aplicación muestra un aviso con la opción de descargarla. Al aceptar, se inicia la descarga con una barra de progreso que indica el avance. Una vez completada, **la aplicación se cierra y se vuelve a abrir sola** ya con la versión actualizada; no necesita hacer nada más.

**Sus datos se conservan intactos durante la actualización:** configuración, credenciales, catálogos, registros de actividad y archivos generados permanecen exactamente como los dejó.

Si prefiere buscar actualizaciones en un momento diferente, puede hacerlo desde **Configuración → Actualizaciones** usando el botón **Buscar actualizaciones**.

![[cert-17-update.png]]
*Figura 17. Aviso de actualización disponible y barra de descarga.*

---

## Reportes externos de LOGS (Compartir ZIP)

Esta función le permite enviar a TI la información de una ejecución cuando necesita ayuda para resolver un problema, sin compartir datos confidenciales.

### Cómo generar el ZIP

1. Diríjase a la pestaña **Logs**.
2. Haga clic sobre la ejecución que desea reportar para seleccionarla.
3. Pulse el botón **Compartir (ZIP)**.
4. Elija la carpeta donde desea guardar el archivo y confirme.

La aplicación genera el ZIP de inmediato y lo guarda en la ubicación que seleccionó.

### Qué incluye el ZIP

| Contenido | Descripción |
|---|---|
| Registro de la corrida | El historial de actividad de esa ejecución. |
| Resultados | El detalle de cada registro procesado (estado, errores, archivos generados). |
| Diagnóstico detallado | Información técnica que TI necesita para identificar la causa del problema. |
| Contexto de la ejecución | Parámetros generales con los que se lanzó el proceso. |
| Copia de la configuración | Los ajustes de la aplicación **sin usuario ni contraseña**; las credenciales nunca se incluyen. |
| Archivo LEEME | Explicación del contenido del ZIP para orientar a quien lo reciba. |

> **Sus credenciales no se incluyen nunca.** Puede compartir el ZIP con TI con total confianza.

### Para qué sirve

Adjunte el archivo ZIP en su correo o ticket a TI. Con esa información, el equipo técnico puede diagnosticar el problema sin necesidad de pedirle datos sensibles ni acceso a su equipo.

![[cert-18-compartir.png]]
*Figura 18. Diálogo "Guardar diagnóstico" al usar Compartir (ZIP).*

# Ejemplos

### Ejemplo 1: archivo CSV para carga masiva

El archivo CSV que se carga en la pestaña **Ejecución por Lote** debe seguir esta estructura: la primera fila contiene los encabezados de las columnas y cada fila siguiente representa un certificado. Los cinco encabezados obligatorios son `embarque`, `formato`, `inspector`, `planta_prod` y `tanque`; los demás campos son opcionales y pueden dejarse en blanco.

Cuando el valor de una columna contiene una coma —como ocurre con el nombre de una planta que incluye ciudad y estado—, ese valor debe escribirse entre comillas dobles para que la aplicación lo interprete como un solo campo y no lo separe en columnas adicionales.

El siguiente bloque muestra la fila de encabezados y un certificado de ejemplo:

```csv
embarque,formato,inspector,observaciones,planta_prod,tanque,sello1,cantidad1,sello2,cantidad2,sello3,cantidad3,sello4,cantidad4,formato_salida,nombre_archivo
256436,1,003,,"MARSHALL, MN",ADMX0106215_221209,951,2,,,,,,,pdf,
```

Observe que:

- El campo `observaciones` está vacío (dos comas seguidas).
- El valor `"MARSHALL, MN"` va entre comillas dobles porque contiene una coma.
- Los campos de sello y cantidad no utilizados se dejan en blanco.
- El campo `nombre_archivo` también está vacío; la aplicación asignará un nombre automáticamente.

Puede preparar o editar este archivo en Excel o en el Bloc de notas antes de cargarlo.

---

### Ejemplo 2: generar un certificado individual

Este ejemplo muestra cómo generar un único certificado y verificar que se procesó correctamente.

1. Abra la pestaña **Certificado individual**.
2. Llene el formulario con los datos del certificado:
   - **Embarque:** ingrese el número o código del embarque.
   - **Formato:** seleccione el tipo de plantilla en la lista desplegable o escríbalo directamente.
   - **Inspector:** seleccione el nombre del inspector en la lista o escríbalo.
   - **Planta producción:** seleccione la planta correspondiente.
   - **Tanque:** ingrese el identificador del tanque.
   - **Sello 1 / Cantidad 1** (y los demás sellos que apliquen): complete los códigos de sello y sus cantidades.
3. En la sección **Opciones de envío**, ubique el campo **Reporte** y seleccione el reporte que corresponda a su certificado.
4. Pulse **Agregar a la cola**. El certificado aparecerá en la lista **Certificados en proceso** con el estado **En cola**.
5. Pulse **Procesar cola**. El estado de la fila cambiará a **Procesando** y, al terminar, a **OK** si el documento se generó sin problemas.
6. Si la fila muestra el estado **ERROR** o **INVALIDO**, abra la pestaña **Logs**, haga clic sobre la ejecución correspondiente y revise el mensaje de resultado en el panel de detalle para identificar qué dato debe corregir.

---

### Ejemplo 3: enviar un diagnóstico a IT

Cuando una ejecución presenta un error que no puede resolver con la información del formulario, puede empaquetar el registro de esa ejecución y enviárselo al equipo de TI.

1. Abra la pestaña **Logs**.
2. Haga clic sobre la fila de la ejecución que presentó el problema para seleccionarla.
3. Pulse el botón **Compartir (ZIP)**.
4. En el diálogo que aparece, elija la carpeta donde desea guardar el archivo y confirme.
5. La aplicación genera el archivo ZIP de inmediato y lo guarda en la ubicación que seleccionó.
6. Adjunte ese archivo ZIP en su correo o ticket dirigido a TI.

> **Importante:** el ZIP no incluye su contraseña ni ninguna otra credencial de acceso. Puede compartirlo con total confianza.

# Solución de problemas

| Síntoma | Causa probable | Acción | Escalamiento |
|---|---|---|---|
| Al abrir "parpadea y se cierra" | Se ejecutó el programa sin su carpeta completa | Extraer todo el ZIP y ejecutar desde la carpeta | **Puedes resolverlo tú** |
| Error de credenciales | Usuario o contraseña incorrectos | Revisar usuario/contraseña en Configuración | **Puedes resolverlo tú** |
| No hay conexión | Problema de red o VPN | Revisar tu red/VPN; correr **Health check** | **Puedes resolverlo tú** |
| Una fila sale ERROR | Dato de esa fila o el servicio | El resto continúa; revisar el mensaje en Logs y corregir la fila | **Puedes resolverlo tú** |
| Falta una opción en una lista (Inspector/Planta/Formato) | Catálogo incompleto | Configuración → Catálogos → actualizar o crear el catálogo | **Puedes resolverlo tú** |
| Health check marca FALLA en el servicio | Servicio caído o mal configurado | Enviar diagnóstico con **Compartir (ZIP)** a IT | **Llama a IT** |
| La actualización falla repetidamente | Permisos o instalación | Enviar diagnóstico y avisar a IT | **Llama a IT** |
| Un reporte muy largo se corta antes de terminar | Corte de red intermedio | Reintentar; si persiste, reportar a IT | **Llama a IT** |

**Antes de llamar a IT**, corre **Health check** (en Configuración) y adjunta el ZIP de **Compartir (ZIP)** de la pestaña Logs; eso acelera el diagnóstico.

# Preguntas frecuentes

**¿Qué motor de PDF debo elegir?**
Use **oracle** (la opción predeterminada); conecta con el servidor corporativo y funciona con todos los tipos de reporte. Elija **local** únicamente si necesita aplicar la plantilla propia instalada en su equipo.

**¿Puedo generar varios certificados a la vez?**
Sí. En la pestaña **Ejecución por Lote**, suba el número de **Workers** para procesar más certificados en paralelo. También puede hacerlo en las **Opciones de envío** del certificado individual antes de procesar la cola.

**Si pulso Detener, ¿qué pasa con lo que ya se estaba generando?**
La solicitud que ya estaba en curso termina normalmente y el archivo queda guardado en la carpeta de salida. No se inician nuevas solicitudes a partir de ese momento; los certificados pendientes permanecen en la cola.

**Al actualizar la app, ¿pierdo mi configuración?**
No. Durante una actualización se conservan intactos su configuración, credenciales, catálogos, registros de actividad y todos los archivos que ya había generado.

**El ZIP de Compartir, ¿lleva mi contraseña?**
No, nunca. El archivo ZIP no contiene su contraseña ni ninguna otra credencial. Puede enviárselo a TI con total confianza.

**¿Dónde quedan los archivos generados?**
En la carpeta de salida que haya configurado en **Configuración → Carpeta de salida**. Si no la cambió, pregunte a TI cuál es la ruta predeterminada en su equipo.

# Referencias

## Índice de imágenes

| Figura | Archivo | Qué encuadrar |
|---|---|---|
| 1 | cert-01-portada.png | Ventana principal abierta (o logo) como portada. |
| 2 | cert-02-carpeta.png | Carpeta extraída del ZIP con el ejecutable visible. |
| 3 | cert-03-icono.png | El icono del ejecutable. |
| 4 | cert-04-ventana-completa.png | Ventana completa: barra superior + las 4 pestañas. |
| 5 | cert-05-form.png | Formulario de Certificado individual lleno. |
| 6 | cert-06-cola.png | Tabla "Certificados en proceso" con estados. |
| 7 | cert-07-lote.png | Pestaña Ejecución por Lote con CSV, barra y registro. |
| 8 | cert-08-csv.png | Un CSV de ejemplo abierto (encabezados + 1 fila). |
| 9 | cert-09-etiqueta.png | Pestaña Etiqueta con campos llenos (y/o el PDF). |
| 10 | cert-10-logs.png | Pestaña Logs: lista de ejecuciones. |
| 11 | cert-11-detalle.png | Detalle: sub-pestañas Resultados y Log completo. |
| 12 | cert-12-config.png | Settings → sub-pestaña Configuración. |
| 13 | cert-13-catalogos.png | Settings → sub-pestaña Catálogos. |
| 14 | cert-14-health.png | Settings → Health check con resultados. |
| 15 | cert-15-info.png | Settings → Info / Ayuda mostrando el manual. |
| 16 | cert-16-updates.png | Settings → Actualizaciones. |
| 17 | cert-17-update.png | Aviso de "Actualización disponible" / barra de descarga. |
| 18 | cert-18-compartir.png | Diálogo "Guardar diagnóstico" al Compartir (ZIP). |

## Glosario

- **Embarque** — número o código que identifica un envío de producto.
- **Formato** — tipo de plantilla usada para generar el certificado; determina la presentación y estructura del documento.
- **Inspector** — persona responsable de verificar la calidad del producto y firmar el certificado.
- **Planta producción** — instalación donde se fabricó o procesó el producto.
- **Tanque** — contenedor identificado por un código donde se almacena o transporta el producto.
- **Sello** — código que identifica el precinto o cierre de seguridad aplicado al embarque.
- **Reporte** — tipo de documento que genera la aplicación (certificado de calidad u otro documento oficial).
- **Workers** — número de documentos que la aplicación puede generar al mismo tiempo; a mayor número, mayor velocidad (si el equipo lo permite).
- **Motor de PDF** — mecanismo interno que construye el archivo PDF; puede ser **oracle** (usa el servidor corporativo) o **local** (usa plantillas instaladas en el equipo).
- **Catálogo** — lista de opciones válidas que la aplicación carga para rellenar campos como Inspector o Planta producción.
- **Health check** — revisión automática que hace la aplicación para comprobar que todo está listo antes de trabajar.
- **Log (registro)** — historial de actividad que guarda la aplicación con el resultado de cada operación realizada.

## Apéndice — Para IT

> Sección para el Departamento de TI; el operador no necesita esto.

### Archivos editables

- **`config.ini`** — archivo de configuración principal de la aplicación. Contiene todos los parámetros de conexión, rutas de carpetas, nivel de log y motor de PDF predeterminado.
- **`.env`** — archivo de credenciales (usuario y contraseña del servicio corporativo). No se incluye en ningún ZIP de diagnóstico.
- **Opción `verify_ssl`** — controla la verificación de certificados TLS al conectarse al servidor. Se configura en `config.ini`; desactivarla solo debe hacerse en entornos internos controlados.
- **Rutas de reporte** — cada tipo de reporte se asocia a una plantilla en el servidor mediante una ruta con extensión `.xdo`. Estas rutas se editan en el catálogo de Reportes dentro de `config.ini`.

### Actualización automática

- Módulo responsable: `certificados/updater.py`.
- Consulta **GitHub Releases** del repositorio `AppsAlmex/py_Certificados_Calidad` para detectar nuevas versiones.
- El proceso de actualización utiliza un `.bat` externo que invoca `robocopy` para reemplazar los archivos del ejecutable preservando las carpetas de datos del usuario: `.env`, `config.ini`, `catalogos/`, `logs/`, `output/`, `ms-playwright/`.

### Compartir ZIP (diagnóstico)

- Módulo responsable: `certificados/log_share.py`.
- Contenido del ZIP generado: `ejecucion.log`, `resultados.csv`, `diagnostico.jsonl`, `contexto.txt`, `config_saneado.ini` (sin usuario ni contraseña), `LEEME.txt`.
- El archivo `.env` **nunca** se incluye en el ZIP.

### Motor local

- Construye el PDF mediante una plantilla HTML propia renderizada con **Chromium/Playwright** (`ms-playwright`).
- Solo está disponible cuando la aplicación se empaquetó incluyendo ese motor; si el paquete distribuido no lo trae, la opción local no funcionará aunque esté seleccionada.
