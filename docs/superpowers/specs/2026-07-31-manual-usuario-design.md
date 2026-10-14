# Spec — Manual de Usuario Completo (ilustrado)

- **Fecha:** 2026-07-31
- **Estado:** Aprobado (diseño, revisado por council)
- **Autor:** GetseAvila
- **Aplicación:** Certificados de Calidad (`py_Certificados_Calidad`)

## 1. Objetivo

Producir un **Manual de Usuario completo e ilustrado** que permita a un operador
usar la aplicación de principio a fin **sin ayuda de IT**, y que deje claro
**cuándo sí debe llamar a IT**. El manual reemplaza el archivo actual
`docs/Manual de Usuario.md`, que está desactualizado respecto a la GUI real.

Este spec separa tres cosas deliberadamente (hallazgo del council):

- **A. Estructura** — el esqueleto de secciones, tomado del template oficial de
  manuales del vault CMMI. No se inventa un índice paralelo.
- **B. Instrucción de generación** — cómo se mapean los hechos de la app y las
  capturas sobre ese esqueleto. Redactada de forma genérica para poder reusarla
  en futuros manuales (pero **no** se construye un skill/pipeline aparte ahora;
  eso queda fuera de alcance).
- **C. Datos de la app** — los hechos verificados de esta app (sección 6), que
  son la *entrada* que se vierte en el esqueleto.

## 2. Audiencia y vocabulario

- **Lector:** operador de planta / inspector de calidad. **No técnico.**
- **Techo de vocabulario:** el cuerpo del manual usa lenguaje de negocio y de la
  interfaz (botones, pestañas, campos tal como aparecen en pantalla). **No** debe
  usar identificadores de código ni jerga de infraestructura en el cuerpo
  (`PARAM_COLUMNS`, `verify_ssl`, `.xdo`, `robocopy`, rutas de módulos, nombres de
  archivos internos).
- Todo ese detalle técnico va a un **apéndice "Para IT"** (bajo Referencias),
  claramente separado, para quien atienda una escalación.

## 3. Estructura del manual — esqueleto canónico (parte A)

El manual **debe** usar como H1 las secciones del template oficial:
`C:\Users\21596\Documents\CMMI\2026-2027\00 Templates\Plantilla Manual.md`
(referenciado por ruta para que, si el template cambia, este spec siga apuntando
a la fuente de verdad). Secciones fijas, en este orden:

1. Introducción
2. Requisitos
3. Instalación
4. Configuración
5. Uso
6. Ejemplos
7. Solución de problemas
8. Preguntas frecuentes
9. Referencias

Motivo (council): mismos encabezados en Markdown y en el template Word =
**cero re-ordenamiento** al formalizar. El usuario formaliza a Word manualmente;
el manual solo debe cumplir esta estructura.

### 3.1 Frontmatter del manual (salida)

El `docs/Manual de Usuario.md` generado inicia con el frontmatter YAML del
template CMMI, para que formalizar sea copiar/pegar y no recapturar:

```yaml
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
app_version_verificada: "vX.Y.Z"   # versión de la app contra la que se verificó
tags: [manual, certificados-calidad]
related: []
---
```

## 4. Mapeo de contenido a las secciones canónicas (parte B)

Regla de generación (genérica): cada bloque de contenido de la app se coloca
**bajo** una de las 9 secciones fijas; no se crean H1 nuevos. Para esta app:

| Sección canónica (H1) | Contenido que la puebla |
|---|---|
| **1. Introducción** | Qué es la app, qué resuelve, para quién (audiencia), y el criterio general "resuélvelo tú vs llama a IT". |
| **2. Requisitos** | Windows; red/VPN para llegar al servicio; credenciales de acceso; (para motor local) que la app traiga Chromium. |
| **3. Instalación** | Extraer el ZIP completo, primer arranque, icono, primera revisión de Configuración. |
| **4. Configuración** | La ventana **Configuración (Settings)** y sus 5 sub-pestañas: Configuración, Catálogos, Health check, Info/Ayuda, Actualizaciones. |
| **5. Uso** | Recorrido de la GUI en el orden pedido: Vista general → pestaña **Certificado individual** → **Ejecución por Lote** → **Etiqueta** → **Logs** → **Motor de PDF** → **Actualizaciones automáticas** → **Reportes externos de LOGS (Compartir ZIP)**. |
| **6. Ejemplos** | Ejemplo CSV comentado; un certificado individual de principio a fin; una etiqueta; compartir un ZIP de diagnóstico a IT. |
| **7. Solución de problemas** | Tabla síntoma·causa·acción. Cada caso marcado **Puedes resolverlo tú** / **Llama a IT** (ver 5.2). |
| **8. Preguntas frecuentes** | Dudas frecuentes derivadas de los problemas comunes y del comportamiento (motor, timeouts largos, detener, qué se preserva al actualizar). |
| **9. Referencias** | Índice de imágenes; glosario breve; **apéndice "Para IT"** con los detalles técnicos/identificadores; y las referencias del template (ISO/OEA) si aplican. |

## 5. Convenciones del manual

### 5.1 Imágenes (Obsidian) y su índice
- Cada figura se inserta con wikilink de Obsidian: `![[cert-NN-descripcion.png]]`.
- **Inmediatamente debajo**, un pie de figura en cursiva que describe *qué se ve
  y qué encuadrar*. Ese pie **es** el contenido del Índice de imágenes: se
  escribe una sola vez y el índice de Referencias solo lo recopila.
- Nota de portabilidad: `![[...]]` es sintaxis de Obsidian; al formalizar a Word
  el usuario re-inserta la imagen a mano (ya previsto). El pie de figura
  sobrevive como texto.

### 5.2 Marcadores de escalamiento
- Usar etiquetas en **negrita**: **Puedes resolverlo tú** / **Llama a IT**.
- El emoji (✅ / 📞) es opcional y solo para la vista Obsidian; el texto en
  negrita es la fuente, para que la formalización a Word quede limpia.

### 5.3 Anti-drift (mantener el manual al día)
- El manual se redacta **desde el código** (`gui/app.py`, `certificados/`), no de
  memoria. El manual viejo se desactualizó justo por no hacer esto.
- Incluir una línea visible al inicio del cuerpo:
  *"Verificado contra la versión vX.Y.Z. Regenerar/revisar tras cada release."*
  y mantener `app_version_verificada` en el frontmatter.

### 5.4 Experiencia en la ayuda in-app (tradeoff aceptado, documentado)
- Como el manual **reemplaza** `docs/Manual de Usuario.md` y ese archivo se
  empaqueta en el `.exe`, la pestaña **Info / Ayuda** lo muestra como **texto
  plano**: el operador verá los `![[...]]` y los emojis como texto crudo, sin
  imágenes.
- Se acepta este tradeoff (una sola fuente). Mitigación: los pies de figura y los
  marcadores en negrita deben ser legibles por sí solos, de modo que el texto
  siga siendo útil aunque no se rendericen las imágenes.

## 6. Hechos verificados de la app (parte C — entrada)

Fuente: `gui/app.py`, `certificados/`. Documentar la app **como es hoy**. En el
cuerpo del manual, expresar esto en lenguaje de usuario (sección 2); los
identificadores entre paréntesis son solo referencia interna para el redactor y
van al apéndice "Para IT".

- **Pestañas principales (4):** `Certificado individual`, `Ejecución por Lote`,
  `Etiqueta`, `Logs`.
- **Barra superior:** botón `Configuración (Settings)` + etiqueta de versión.
- **Settings (ventana modal, 5 sub-pestañas):** `Configuración`, `Catálogos`,
  `Health check`, `Info / Ayuda`, `Actualizaciones`.

### 6.1 Certificado individual
- Formulario con los campos de la solicitud: Embarque, Formato, Inspector,
  Observaciones, Planta producción, Tanque, Sello 1–4, Cantidad 1–4.
- **Cantidad 1–4:** listas "" o 1–10.
- **Formato / Inspector / Planta producción:** listas de catálogo editables
  ("valor - descripción"); se guarda solo el valor.
- **Formato salida:** `pdf` / `xml`. **Nombre archivo:** opcional.
- **Agregar a la cola** → tabla "Certificados en proceso"
  (Embarque, Formato, Estado). **Limpiar formulario.**
- **Opciones de envío:** Reporte, Workers (1–100), Motor (oracle/local). Con
  Motor `local`, la lista de Formato muestra solo plantillas locales.
- **Procesar cola / Detener / Quitar seleccionado / Limpiar completados.**
- Estados por fila: En cola → Procesando → OK / ERROR / INVALIDO.
- *(Para IT: campos = `PARAM_COLUMNS`; catálogos en `catalogos/`.)*

### 6.2 Ejecución por Lote
- Archivo CSV (Examinar…), Reporte, Workers (1–100), Motor de PDF.
- **Ejecutar / Detener**, barra de progreso + `%`, "Registro en vivo", barra de
  estado inferior.
- Formato CSV: encabezados obligatorios embarque, formato, inspector,
  planta_prod, tanque; opcionales el resto; formato_salida = pdf|xml|xlsx.

### 6.3 Etiqueta
- 7 campos (cliente, sucursal, producto, transporte, lote, equipo, fecha; fecha
  por defecto = ahora, editable) + Generar PDF (no congela) + Limpiar. Genera un
  PDF 3×2" para ALMIDONES MEXICANOS S.A. DE C.V.

### 6.4 Logs
- Tabla de ejecuciones (Fecha, Reporte, Total, OK, Error, Inválido), más
  recientes primero.
- Detalle en sub-pestañas: **Resultados** (fila, estado con color, formato,
  duración, parámetros legibles, archivo, mensaje) y **Log completo** (texto).
- Botones: **Refrescar**, **Compartir (ZIP)**.

### 6.5 Settings — Configuración
Host, Service path, Read timeout, Connect timeout, Carpeta salida, Carpeta logs,
Usuario, Contraseña, Verificar TLS, Nivel de log, Reporte por defecto, Max
workers (1–100), Motor de PDF, y catálogo de **Reportes** (una línea
`clave = ruta`). **Guardar y aplicar** valida y guarda; al cerrar, la app recarga
y revalida. *(Para IT: escribe `config.ini`/`.env`; `verify_ssl`; rutas `.xdo`.)*

### 6.6 Settings — Catálogos
Tabla de estado (catálogo, opciones, estado, detalle). Acciones por catálogo:
**Actualizar desde Oracle** (hoy solo Inspector tiene reporte; los demás
deshabilitados) y **Crear archivo por defecto**. La sincronización nunca borra
entradas locales ausentes del reporte.

### 6.7 Settings — Health check
Corre chequeos (config, catálogo de reportes, cada catálogo, carpetas
escribibles, plantillas locales + Chromium si motor local, conectividad
opcional). Resultado en tabla OK/FALLA + resumen. Es la herramienta de
autodiagnóstico antes de llamar a IT.

### 6.8 Settings — Info / Ayuda
Selector de documento (lee `docs/`) en modo solo lectura. Aquí se lee este
manual dentro de la app (ver 5.4).

### 6.9 Settings — Actualizaciones
Muestra versión instalada, botón **Buscar actualizaciones**, notas de la versión
disponible, barra de descarga.

### 6.10 Motor de PDF
`oracle` (predeterminado, PDF original del sistema) vs `local` (arma el PDF con
plantilla propia; solo PDF; solo formatos con plantilla). Se elige por corrida en
cada pestaña. *(Para IT: `local` usa XML de Oracle + HTML vía Chromium/Playwright.)*

### 6.11 Actualizaciones automáticas
Chequeo silencioso al arrancar; si hay versión más nueva, avisa. Al aceptar,
descarga con barra de progreso, la app se cierra y se vuelve a abrir sola ya
actualizada. **Se preservan** los datos del usuario: configuración, credenciales,
catálogos, logs y salidas. Solo aplica al `.exe` instalado.
*(Para IT: `certificados/updater.py`; GitHub Releases `AppsAlmex/py_Certificados_Calidad`;
`.bat` + robocopy; preserva `.env`, `config.ini`, `catalogos/`, `logs/`, `output/`,
`ms-playwright/`.)*

### 6.12 Reportes externos de LOGS — Compartir ZIP
Desde Logs → **Compartir (ZIP)**, empaqueta la ejecución seleccionada en un ZIP
para enviar a IT: incluye el log, los resultados, un diagnóstico detallado, el
contexto y una copia de la configuración **sin usuario ni contraseña**, más un
LEEME. Las credenciales **nunca** se incluyen.
*(Para IT: `certificados/log_share.py`; miembros `ejecucion.log`, `resultados.csv`,
`diagnostico.jsonl`, `contexto.txt`, `config_saneado.ini`, `LEEME.txt`; el `.env`
nunca se incluye.)*

## 7. Imágenes requeridas (18)

El nombre es el archivo a pegar en Obsidian; "Qué encuadrar" es el pie de figura.

| Archivo | Sección | Qué encuadrar |
|---|---|---|
| `cert-01-portada.png` | Introducción | Ventana principal abierta (o logo) como portada. |
| `cert-02-carpeta.png` | Instalación | Carpeta extraída del ZIP con el `.exe` visible. |
| `cert-03-icono.png` | Instalación | El icono del ejecutable. |
| `cert-04-ventana-completa.png` | Uso (Vista general) | Ventana completa: barra superior + las 4 pestañas. |
| `cert-05-form.png` | Uso (Individual) | Formulario de Certificado individual lleno. |
| `cert-06-cola.png` | Uso (Individual) | Tabla "Certificados en proceso" con estados. |
| `cert-07-lote.png` | Uso (Lote) | Pestaña Ejecución por Lote con CSV, barra y registro. |
| `cert-08-csv.png` | Uso (Lote) / Ejemplos | Un CSV de ejemplo abierto (encabezados + 1 fila). |
| `cert-09-etiqueta.png` | Uso (Etiqueta) | Pestaña Etiqueta con campos llenos (y/o el PDF). |
| `cert-10-logs.png` | Uso (Logs) | Pestaña Logs: lista de ejecuciones. |
| `cert-11-detalle.png` | Uso (Logs) | Detalle: sub-pestañas Resultados y Log completo. |
| `cert-12-config.png` | Configuración | Settings → sub-pestaña Configuración. |
| `cert-13-catalogos.png` | Configuración | Settings → sub-pestaña Catálogos. |
| `cert-14-health.png` | Configuración | Settings → Health check con resultados. |
| `cert-15-info.png` | Configuración | Settings → Info / Ayuda mostrando el manual. |
| `cert-16-updates.png` | Configuración | Settings → Actualizaciones. |
| `cert-17-update.png` | Uso (Actualizaciones) | Aviso de "Actualización disponible" / barra de descarga. |
| `cert-18-compartir.png` | Uso (Compartir ZIP) | Diálogo "Guardar diagnóstico" al Compartir (ZIP). |

## 8. Criterios de aceptación

- El manual usa como H1 **exactamente** las 9 secciones del `Plantilla Manual`,
  en orden, con el frontmatter CMMI (3.1).
- Cada pestaña y control de la GUI actual está documentado bajo "Uso" o
  "Configuración" (paridad con `gui/app.py`).
- El cuerpo respeta el techo de vocabulario (sección 2); los identificadores
  técnicos viven solo en el apéndice "Para IT".
- Cada sección con UI tiene al menos una figura `![[...]]` con pie de figura, y
  el Índice de imágenes recopila esos pies (las 18 capturas).
- Actualizaciones automáticas y Compartir ZIP están cubiertas con
  qué/cómo/qué-se-preserva/qué-NO-se-incluye.
- Solución de problemas marca cada caso **Puedes resolverlo tú** / **Llama a IT**.
- Incluye la línea anti-drift y `app_version_verificada`.
- Sin secciones "TBD"; describe la app como es hoy.

## 9. Fuera de alcance

- No se cambia código de la app ni la lógica de la pestaña Info/Ayuda.
- No se crean los archivos de imagen (los pega el usuario en Obsidian) ni se
  formaliza el Word (lo hace el usuario).
- **No** se construye un skill/pipeline genérico de generación de manuales; la
  parte B queda como guía dentro de este spec, no como herramienta aparte.
- No se toca el vault CMMI (esos manuales son administrativos, solo referencia).
