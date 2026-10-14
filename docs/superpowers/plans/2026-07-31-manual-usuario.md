# Manual de Usuario Completo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reescribir `docs/Manual de Usuario.md` como un Manual de Usuario completo e ilustrado, con la estructura canónica del template de manuales CMMI, en Markdown/Obsidian, listo para que el usuario pegue capturas y lo formalice a Word.

**Architecture:** Un solo archivo Markdown construido por secciones. Se sobrescribe el archivo actual (desactualizado). Cada tarea redacta uno o varios de los 9 encabezados canónicos, verifica su estructura con `Grep`, y hace commit. El contenido se toma de los hechos verificados del spec (parte C) y se expresa en lenguaje de usuario.

**Tech Stack:** Markdown (Obsidian flavor), wikilinks `![[...]]` para imágenes. Sin código de app. Verificación con `Grep`/ripgrep.

## Global Constraints

Copiadas del spec `docs/superpowers/specs/2026-07-31-manual-usuario-design.md`:

- **Archivo objetivo (única fuente):** `docs/Manual de Usuario.md` — se reescribe completo.
- **Esqueleto H1 fijo, en este orden (del `Plantilla Manual.md` CMMI):** `Introducción`, `Requisitos`, `Instalación`, `Configuración`, `Uso`, `Ejemplos`, `Solución de problemas`, `Preguntas frecuentes`, `Referencias`. No crear H1 nuevos.
- **Audiencia:** operador de planta / inspector, **no técnico**. Cuerpo en lenguaje de UI/negocio.
- **Prohibido en el cuerpo:** identificadores de código o infraestructura (`PARAM_COLUMNS`, `verify_ssl`, `.xdo`, `robocopy`, `.env`, `config.ini`, rutas de módulos, nombres de módulos `certificados/...`). Todo eso va **solo** al apéndice "Para IT" bajo Referencias.
- **Imágenes:** wikilink `![[cert-NN-descripcion.png]]` + pie de figura en cursiva justo debajo. Son 18 (ver spec §7).
- **Escalamiento:** marcar cada problema con **Puedes resolverlo tú** o **Llama a IT** (negrita; emoji ✅/📞 opcional).
- **Anti-drift:** línea visible "Verificado contra la versión v1.2.3. Regenerar/revisar tras cada release." y `app_version_verificada: "v1.2.3"` en frontmatter.
- **Versión app actual:** `1.2.3` (de `certificados/__init__.py`).
- **Commits:** en la rama `feature/manual-usuario-completo`. Terminar mensajes con `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## File Structure

- **Modify (sobrescribir):** `docs/Manual de Usuario.md` — el manual completo. Único archivo del plan.
- **Referencia (solo lectura):** el spec, `gui/app.py`, `certificados/` para verificar hechos; `00 Templates\Plantilla Manual.md` del vault CMMI para los nombres de sección.

Verificación estándar de cada tarea (sin tests unitarios; es prosa): comprobar con `Grep` que el/los encabezado(s) y placeholders de imagen existen, y revisión visual de que el contenido cubre los puntos del spec.

---

### Task 1: Andamiaje del manual (frontmatter + esqueleto)

**Files:**
- Modify (sobrescribir): `docs/Manual de Usuario.md`

**Interfaces:**
- Produces: archivo con frontmatter CMMI, línea anti-drift, y los 9 H1 canónicos en orden (vacíos, listos para llenar por tareas siguientes).

- [ ] **Step 1: Sobrescribir el archivo con el andamiaje**

Escribir `docs/Manual de Usuario.md` con exactamente este contenido:

```markdown
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

# Requisitos

# Instalación

# Configuración

# Uso

# Ejemplos

# Solución de problemas

# Preguntas frecuentes

# Referencias
```

- [ ] **Step 2: Verificar los 9 H1 en orden**

Run: `rg -n "^# " "docs/Manual de Usuario.md"`
Expected: 9 líneas, en este orden: Introducción, Requisitos, Instalación, Configuración, Uso, Ejemplos, Solución de problemas, Preguntas frecuentes, Referencias.

- [ ] **Step 3: Commit**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): andamiaje con frontmatter y esqueleto canonico"
```

---

### Task 2: Introducción, Requisitos, Instalación

**Files:**
- Modify: `docs/Manual de Usuario.md` (bajo los H1 `Introducción`, `Requisitos`, `Instalación`)

**Interfaces:**
- Consumes: andamiaje de Task 1.
- Produces: secciones 1–3 llenas.

- [ ] **Step 1: Redactar Introducción**

Bajo `# Introducción`, cubrir (spec §6 encabezado, §2 audiencia):
- Qué es: app para generar **certificados de calidad** (uno por uno o de forma masiva desde un archivo) y **etiquetas**, consultando el sistema corporativo.
- Para quién: operador de planta / inspector de calidad.
- Criterio general: la mayoría de las tareas las resuelves tú con este manual; hay una sección de problemas que indica **cuándo llamar a IT**.
- Insertar figura de portada:

```markdown
![[cert-01-portada.png]]
*Figura 1. Ventana principal de la aplicación Certificados de Calidad.*
```

- [ ] **Step 2: Redactar Requisitos**

Bajo `# Requisitos`, en lenguaje de usuario:
- Equipo con Windows.
- Conexión a la red interna / VPN para llegar al servicio.
- Tus credenciales de acceso (usuario y contraseña).
- Para el motor de PDF "local": que la app se haya instalado con ese motor incluido (si no, usa "oracle").

- [ ] **Step 3: Redactar Instalación**

Bajo `# Instalación`:
- Extraer **todo** el ZIP antes de usar; ejecutar desde la carpeta extraída (no solo el `.exe`, no desde dentro del ZIP).
- Abrir `CertificadosCalidad.exe` (doble clic).
- Primera vez: abrir **Configuración (Settings)** y confirmar datos de acceso.
- Figuras:

```markdown
![[cert-02-carpeta.png]]
*Figura 2. Carpeta extraída del ZIP con el ejecutable.*

![[cert-03-icono.png]]
*Figura 3. Icono del ejecutable.*
```

- [ ] **Step 4: Verificar encabezados y figuras**

Run: `rg -n "cert-01-portada|cert-02-carpeta|cert-03-icono" "docs/Manual de Usuario.md"`
Expected: 3 coincidencias (una por figura).

- [ ] **Step 5: Commit**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): introduccion, requisitos e instalacion"
```

---

### Task 3: Configuración (las 5 sub-pestañas de Settings)

**Files:**
- Modify: `docs/Manual de Usuario.md` (bajo `# Configuración`)

**Interfaces:**
- Produces: sección Configuración con subsecciones H2 por sub-pestaña.

- [ ] **Step 1: Redactar la sección Configuración**

Bajo `# Configuración`, explicar que se abre con el botón **Configuración (Settings)** (barra superior) como ventana aparte con 5 sub-pestañas. Crear H2 por cada una (spec §6.5–6.9):

- `## Configuración` — datos de conexión (Host, Service path), tiempos de espera, carpetas de salida y de logs, usuario/contraseña, verificar TLS, nivel de log, reporte por defecto, número máximo de workers (1–100), motor de PDF, y la lista de **Reportes** (una línea por reporte: `clave = ruta`). Botón **Guardar y aplicar** (valida y guarda; al cerrar, la app revalida).
- `## Catálogos` — tabla de estado (catálogo, opciones, estado, detalle). Acciones por catálogo: **Actualizar desde Oracle** (hoy solo Inspector; los demás deshabilitados) y **Crear archivo por defecto**. Nunca borra entradas locales que no estén en el reporte.
- `## Health check` — botón para correr un chequeo general (configuración, reportes, catálogos, carpetas, plantillas locales, conectividad opcional); tabla OK/FALLA + resumen. Úsalo antes de llamar a IT.
- `## Info / Ayuda` — selector de documento que muestra este manual dentro de la app (solo lectura); las imágenes aquí aparecen como texto.
- `## Actualizaciones` — versión instalada, botón **Buscar actualizaciones**, notas de la versión y barra de descarga.

- [ ] **Step 2: Insertar figuras**

```markdown
![[cert-12-config.png]]
*Figura 12. Configuración (Settings) → sub-pestaña Configuración.*

![[cert-13-catalogos.png]]
*Figura 13. Sub-pestaña Catálogos con el estado de cada catálogo.*

![[cert-14-health.png]]
*Figura 14. Sub-pestaña Health check con resultados.*

![[cert-15-info.png]]
*Figura 15. Sub-pestaña Info / Ayuda mostrando este manual.*

![[cert-16-updates.png]]
*Figura 16. Sub-pestaña Actualizaciones.*
```

- [ ] **Step 3: Verificar figuras y ausencia de jerga**

Run: `rg -n "cert-1[23456]-" "docs/Manual de Usuario.md"`
Expected: 5 coincidencias (cert-12..16).

Run: `rg -n "verify_ssl|config\.ini|\.env|\.xdo|robocopy|PARAM_COLUMNS" "docs/Manual de Usuario.md"`
Expected: **sin coincidencias** (esa jerga aún no debe aparecer; irá solo en el apéndice Para IT de Task 9).

- [ ] **Step 4: Commit**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): seccion Configuracion (5 sub-pestanas de Settings)"
```

---

### Task 4: Uso — parte 1 (Vista general, Certificado individual, Ejecución por Lote)

**Files:**
- Modify: `docs/Manual de Usuario.md` (bajo `# Uso`)

**Interfaces:**
- Produces: inicio de la sección Uso con H2 `Vista general`, `Certificado individual`, `Ejecución por Lote`.

- [ ] **Step 1: Redactar "Vista general"**

Bajo `# Uso`, H2 `## Vista general`: describir la barra superior (botón Configuración + versión) y las 4 pestañas: **Certificado individual**, **Ejecución por Lote**, **Etiqueta**, **Logs**. Figura:

```markdown
![[cert-04-ventana-completa.png]]
*Figura 4. Ventana principal: barra superior y las cuatro pestañas.*
```

- [ ] **Step 2: Redactar "Certificado individual"**

H2 `## Certificado individual` (spec §6.1), en lenguaje de usuario:
- Llenar el formulario: Embarque, Formato, Inspector, Observaciones, Planta producción, Tanque, Sello 1–4, Cantidad 1–4.
- Cantidad 1–4 son listas de 1 a 10; Formato/Inspector/Planta son listas ("valor - descripción") editables (si falta un valor puedes escribirlo).
- Formato salida: pdf o xml. Nombre archivo: opcional.
- **Agregar a la cola** → aparece en "Certificados en proceso" (Embarque, Formato, Estado). **Limpiar formulario**.
- **Opciones de envío:** Reporte, Workers, Motor (oracle/local). Con Motor local, la lista de Formato muestra solo los formatos con plantilla local.
- **Procesar cola** ejecuta; estados por fila: En cola → Procesando → OK / ERROR / INVALIDO. Botones **Detener**, **Quitar seleccionado**, **Limpiar completados**.
- Figuras:

```markdown
![[cert-05-form.png]]
*Figura 5. Formulario de Certificado individual.*

![[cert-06-cola.png]]
*Figura 6. Lista "Certificados en proceso" con los estados por fila.*
```

- [ ] **Step 3: Redactar "Ejecución por Lote"**

H2 `## Ejecución por Lote` (spec §6.2):
- Elegir **Archivo CSV** con *Examinar…*, el **Reporte**, **Workers** (cuántos a la vez) y **Motor de PDF**.
- **Ejecutar** inicia; la **barra** muestra el avance (p. ej. 3/10 = 30%) y el "Registro en vivo" el detalle; **Detener** cancela (la solicitud en curso termina, no se lanzan más).
- Formato del CSV: encabezados obligatorios embarque, formato, inspector, planta_prod, tanque; el resto opcional; formato_salida puede ser pdf, xml o xlsx. Los archivos quedan en la carpeta de salida.
- Figuras:

```markdown
![[cert-07-lote.png]]
*Figura 7. Pestaña Ejecución por Lote: CSV, barra de progreso y registro en vivo.*

![[cert-08-csv.png]]
*Figura 8. Ejemplo de archivo CSV (encabezados y una fila).*
```

- [ ] **Step 4: Verificar figuras**

Run: `rg -n "cert-04-|cert-05-|cert-06-|cert-07-|cert-08-" "docs/Manual de Usuario.md"`
Expected: 5 coincidencias.

- [ ] **Step 5: Commit**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): Uso parte 1 (vista general, individual, lote)"
```

---

### Task 5: Uso — parte 2 (Etiqueta, Logs, Motor de PDF)

**Files:**
- Modify: `docs/Manual de Usuario.md` (bajo `# Uso`)

**Interfaces:**
- Produces: H2 `Etiqueta`, `Logs`, `Motor de PDF`.

- [ ] **Step 1: Redactar "Etiqueta"**

H2 `## Etiqueta` (spec §6.3): formulario de 7 campos (cliente, sucursal, producto, transporte, lote, equipo, fecha; la fecha viene con la actual y es editable). **Generar PDF** crea una etiqueta de 3×2 pulgadas para ALMIDONES MEXICANOS S.A. DE C.V.; **Limpiar** vacía el formulario. Figura:

```markdown
![[cert-09-etiqueta.png]]
*Figura 9. Pestaña Etiqueta con los datos capturados.*
```

- [ ] **Step 2: Redactar "Logs"**

H2 `## Logs` (spec §6.4):
- Lista de ejecuciones (Fecha, Reporte, Total, OK, Error, Inválido), más recientes primero.
- Al seleccionar una: **Resultados** (fila, estado con color, formato, duración, parámetros, archivo, mensaje) y **Log completo** (texto).
- Botones **Refrescar** y **Compartir (ZIP)** (se detalla en "Reportes externos de LOGS").
- Figuras:

```markdown
![[cert-10-logs.png]]
*Figura 10. Pestaña Logs: lista de ejecuciones.*

![[cert-11-detalle.png]]
*Figura 11. Detalle de una ejecución: Resultados y Log completo.*
```

- [ ] **Step 3: Redactar "Motor de PDF"**

H2 `## Motor de PDF` (spec §6.10): **oracle** (predeterminado, usa el PDF original del sistema) vs **local** (arma el PDF con una plantilla propia; solo para PDF y solo formatos con plantilla). Se elige por corrida en cada pestaña. Sin jerga técnica en el cuerpo.

- [ ] **Step 4: Verificar figuras**

Run: `rg -n "cert-09-|cert-10-|cert-11-" "docs/Manual de Usuario.md"`
Expected: 3 coincidencias.

- [ ] **Step 5: Commit**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): Uso parte 2 (etiqueta, logs, motor de PDF)"
```

---

### Task 6: Uso — parte 3 (Actualizaciones automáticas, Reportes externos de LOGS)

**Files:**
- Modify: `docs/Manual de Usuario.md` (bajo `# Uso`)

**Interfaces:**
- Produces: H2 `Actualizaciones automáticas`, `Reportes externos de LOGS (Compartir ZIP)`.

- [ ] **Step 1: Redactar "Actualizaciones automáticas"**

H2 `## Actualizaciones automáticas` (spec §6.11), en lenguaje de usuario:
- Al abrir la app, revisa sola si hay una versión más nueva (sin molestar si no la hay).
- Si la hay, avisa; al aceptar, descarga con una barra de progreso, la app **se cierra y se vuelve a abrir sola** ya actualizada.
- **Se conservan** tus datos: configuración, credenciales, catálogos, logs y archivos generados.
- También puedes buscar manualmente en Configuración → Actualizaciones.
- Figura:

```markdown
![[cert-17-update.png]]
*Figura 17. Aviso de actualización disponible y barra de descarga.*
```

- [ ] **Step 2: Redactar "Reportes externos de LOGS (Compartir ZIP)"**

H2 `## Reportes externos de LOGS (Compartir ZIP)` (spec §6.12):
- Desde **Logs**, selecciona una ejecución y pulsa **Compartir (ZIP)**: se guarda un archivo ZIP para enviar a IT.
- Qué incluye: el registro, los resultados, un diagnóstico detallado, el contexto de la corrida y una copia de la configuración **sin usuario ni contraseña**, más un LEEME.
- Qué NO incluye: tus credenciales, nunca.
- Para qué sirve: que IT diagnostique un problema sin pedirte datos sensibles.
- Figura:

```markdown
![[cert-18-compartir.png]]
*Figura 18. Diálogo "Guardar diagnóstico" al usar Compartir (ZIP).*
```

- [ ] **Step 3: Verificar figuras y credenciales**

Run: `rg -n "cert-17-|cert-18-" "docs/Manual de Usuario.md"`
Expected: 2 coincidencias.

- [ ] **Step 4: Commit**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): Uso parte 3 (actualizaciones y compartir ZIP)"
```

---

### Task 7: Ejemplos

**Files:**
- Modify: `docs/Manual de Usuario.md` (bajo `# Ejemplos`)

**Interfaces:**
- Produces: sección Ejemplos con casos concretos.

- [ ] **Step 1: Redactar Ejemplos**

Bajo `# Ejemplos`, tres casos guiados (spec §4 fila Ejemplos):

1. **CSV comentado** — bloque con encabezados y una fila real, p. ej.:

```csv
embarque,formato,inspector,observaciones,planta_prod,tanque,sello1,cantidad1,sello2,cantidad2,sello3,cantidad3,sello4,cantidad4,formato_salida,nombre_archivo
256436,1,003,,"MARSHALL, MN",ADMX0106215_221209,951,2,,,,,,,pdf,
```
   Explicar que los valores con comas van entre comillas dobles y que las columnas obligatorias son embarque, formato, inspector, planta_prod, tanque.

2. **Un certificado individual de principio a fin** — llenar el formulario, Agregar a la cola, elegir Reporte y Procesar cola; leer el estado OK.

3. **Compartir un diagnóstico a IT** — abrir Logs, elegir la ejecución con error, Compartir (ZIP), y adjuntarlo en el correo a IT.

- [ ] **Step 2: Verificar la sección**

Run: `rg -n "^# Ejemplos" "docs/Manual de Usuario.md"`
Expected: 1 coincidencia, con contenido debajo.

- [ ] **Step 3: Commit**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): seccion Ejemplos"
```

---

### Task 8: Solución de problemas (con escalamiento a IT)

**Files:**
- Modify: `docs/Manual de Usuario.md` (bajo `# Solución de problemas`)

**Interfaces:**
- Produces: tabla/lista de problemas con marcador de escalamiento.

- [ ] **Step 1: Redactar Solución de problemas**

Bajo `# Solución de problemas`, una tabla síntoma · causa · acción, y en cada fila el marcador **Puedes resolverlo tú** o **Llama a IT**. Casos mínimos (spec §7; derivados del comportamiento real):

| Síntoma | Causa probable | Acción | Escalamiento |
|---|---|---|---|
| Al abrir "parpadea y se cierra" | Se ejecutó el `.exe` sin su carpeta completa | Extraer todo el ZIP y ejecutar desde la carpeta | **Puedes resolverlo tú** |
| Error de credenciales | Usuario/contraseña incorrectos | Revisar usuario/contraseña en Configuración | **Puedes resolverlo tú** |
| No hay conexión | Red / VPN | Revisar tu red/VPN; correr **Health check** | **Puedes resolverlo tú** |
| Una fila sale ERROR | Dato o servicio | El resto continúa; revisar el mensaje en Logs | **Puedes resolverlo tú** |
| Falta una opción en una lista | Catálogo incompleto | Configuración → Catálogos → actualizar/crear | **Puedes resolverlo tú** |
| Health check marca FALLA en el servicio | Servicio/host caído o mal configurado | Enviar diagnóstico con **Compartir (ZIP)** | **Llama a IT** |
| La actualización falla repetidamente | Permisos/instalación | Enviar diagnóstico y avisar | **Llama a IT** |
| Reporte muy largo se corta | Corte de red intermedio (gateway) | Reintentar; si persiste, reportar | **Llama a IT** |

Añadir una frase: antes de llamar a IT, corre **Health check** y adjunta el ZIP de **Compartir**.

- [ ] **Step 2: Verificar marcadores**

Run: `rg -n "Puedes resolverlo tú|Llama a IT" "docs/Manual de Usuario.md"`
Expected: varias coincidencias de ambos marcadores.

- [ ] **Step 3: Commit**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): Solucion de problemas con escalamiento a IT"
```

---

### Task 9: Preguntas frecuentes y Referencias (índice de imágenes, glosario, apéndice Para IT)

**Files:**
- Modify: `docs/Manual de Usuario.md` (bajo `# Preguntas frecuentes` y `# Referencias`)

**Interfaces:**
- Produces: FAQ; y Referencias con Índice de imágenes + Glosario + apéndice "Para IT".

- [ ] **Step 1: Redactar Preguntas frecuentes**

Bajo `# Preguntas frecuentes`, Q/A cortas (spec §4 fila FAQ), p. ej.:
- ¿Qué motor de PDF elijo? → oracle por defecto; local solo si necesitas la plantilla propia.
- ¿Puedo generar muchos a la vez? → sí, sube Workers en Lote o en Opciones de envío.
- Si detengo, ¿qué pasa con lo que ya corría? → la solicitud en curso termina; no se lanzan más.
- Al actualizar, ¿pierdo mi configuración? → no; se conservan configuración, credenciales, catálogos, logs y salidas.
- ¿El ZIP de Compartir lleva mi contraseña? → no, nunca.

- [ ] **Step 2: Redactar Referencias → Índice de imágenes**

Bajo `# Referencias`, H2 `## Índice de imágenes`: recopilar las 18 figuras (Figura 1–18) con su archivo y su pie (el mismo texto de cada caption). Tabla con columnas: Figura, Archivo, Qué encuadrar (copiar de spec §7).

- [ ] **Step 3: Redactar Referencias → Glosario**

H2 `## Glosario`: términos de usuario (Embarque, Formato, Inspector, Planta, Tanque, Sello, Reporte, Workers, Motor de PDF, Catálogo, Health check, Log/Registro).

- [ ] **Step 4: Redactar Referencias → Apéndice "Para IT"**

H2 `## Apéndice — Para IT`: aquí sí van los detalles técnicos (spec §6 notas *(Para IT: ...)*): archivos `config.ini`/`.env`, `verify_ssl`, rutas de reporte `.xdo`, módulos `certificados/updater.py` y `certificados/log_share.py`, el mecanismo de actualización (GitHub Releases + `.bat`/robocopy y qué carpetas preserva: `.env`, `config.ini`, `catalogos/`, `logs/`, `output/`, `ms-playwright/`), y los miembros del ZIP de diagnóstico. Encabezar con una nota: "Sección para el Departamento de TI; el operador no necesita esto."

- [ ] **Step 5: Verificar separación de jerga**

Run: `rg -n "robocopy|ms-playwright|updater\.py|log_share\.py" "docs/Manual de Usuario.md"`
Expected: coincidencias **solo** dentro del apéndice Para IT (verificar visualmente que están bajo `## Apéndice — Para IT`).

- [ ] **Step 6: Commit**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): FAQ y Referencias (indice de imagenes, glosario, apendice IT)"
```

---

### Task 10: Verificación final contra criterios de aceptación

**Files:**
- Modify (solo si algo falla): `docs/Manual de Usuario.md`

**Interfaces:**
- Consumes: manual completo.
- Produces: manual verificado contra spec §8.

- [ ] **Step 1: Verificar los 9 H1 canónicos**

Run: `rg -n "^# " "docs/Manual de Usuario.md"`
Expected: exactamente los 9 encabezados del esqueleto, en orden.

- [ ] **Step 2: Verificar las 18 imágenes**

Run: `rg -c "!\[\[cert-" "docs/Manual de Usuario.md"`
Expected: `18`.

- [ ] **Step 3: Verificar frontmatter y anti-drift**

Run: `rg -n "app_version_verificada|Verificado contra la versión v1.2.3" "docs/Manual de Usuario.md"`
Expected: ambas coincidencias presentes.

- [ ] **Step 4: Verificar que la jerga técnica solo esté en el apéndice**

Run: `rg -n "verify_ssl|\.xdo|robocopy|PARAM_COLUMNS|config\.ini|\.env" "docs/Manual de Usuario.md"`
Expected: todas las coincidencias caen bajo `## Apéndice — Para IT` (revisión visual). Si alguna aparece antes, moverla al apéndice.

- [ ] **Step 5: Revisión visual final**

Leer el archivo completo: paridad con la GUI (todas las pestañas y sub-pestañas), pies de figura legibles como texto (por la ayuda in-app), y marcadores de escalamiento presentes. Corregir lo que falte.

- [ ] **Step 6: Commit final (si hubo correcciones)**

```bash
git add "docs/Manual de Usuario.md"
git commit -m "docs(manual): verificacion final contra criterios de aceptacion"
```

---

## Self-Review (autor del plan)

**Cobertura del spec §8 (criterios de aceptación):**
- 9 H1 canónicos + frontmatter → Task 1, verificado en Task 10.
- Paridad GUI (pestañas + Settings) → Tasks 3–6.
- Techo de vocabulario + apéndice Para IT → Global Constraints + Task 9; verificado Tasks 3/9/10.
- 18 figuras con pie + índice → Tasks 2–6 (figuras), Task 9 (índice); verificado Task 10.
- Actualizaciones + Compartir ZIP con qué/cómo/preserva/NO-incluye → Task 6.
- Escalamiento usuario/IT → Task 8.
- Anti-drift + `app_version_verificada` → Task 1; verificado Task 10.
- Sin "TBD" → ninguna tarea deja placeholders.

**Escaneo de placeholders:** el plan da encabezados exactos, wikilinks exactos y los puntos de contenido de cada sección desde el spec; la prosa la redacta el ejecutor (es el entregable). Sin "TBD/TODO".

**Consistencia:** nombres de figura `cert-01..18` consistentes entre tareas y con spec §7; H1 idénticos al `Plantilla Manual`; marcadores de escalamiento con el mismo texto en Tasks 8 y Global Constraints.
