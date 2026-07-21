# Flujo de trabajo Git por Pull Request

Objetivo: **main es intocable**. Solo entra codigo por Pull Request, con tests
verdes y coverage >= 80%. Los releases (tag + .exe) salen **solos los lunes 7am**.

## Modelo de ramas

```
feature/xxxx  --(push directo o PR)-->  dev  --(PR)-->  main
                                         │                 │
                                    integras aqui     solo lunes 7am
                                    libremente        (auto-merge + auto-tag)
```

- **feature/xxxx**: tu trabajo del dia. Sale de `dev`.
- **dev**: rama de integracion. Puedes empujar directo (no esta protegida).
- **main**: protegida. Solo por PR desde `dev`. Cada merge = un Release.

## Qué hace la automatización

| Evento | Workflow | Resultado |
|--------|----------|-----------|
| PR hacia `main` o `dev`, push a `dev` | `ci.yml` | corre tests + coverage 80% (check obligatorio) |
| Lunes 13:00 UTC (07:00 MX) | `release-monday.yml` | mergea el PR `dev -> main`, crea el tag `vX.Y.Z` |
| Se crea un tag `v*` | `build.yml` | compila el `.exe` y publica el Release |

El tag se auto-incrementa **patch** (v1.2.3 -> v1.2.4). Si el PR `dev -> main`
lleva la etiqueta `minor` o `major`, sube ese numero.

---

## Configuración inicial (una sola vez)

Hazlo **en este orden**. Los pasos 1-2 con main todavia sin proteger.

### Paso 1 — Subir los workflows a main

Los 3 archivos en `.github/workflows/` (`build.yml`, `ci.yml`,
`release-monday.yml`) deben estar en `main` antes de proteger. Commitea y
pushea a main una ultima vez de forma directa.

### Paso 2 — Crear la rama dev

```
git checkout main
git pull
git checkout -b dev
git push -u origin dev
```

### Paso 3 — Crear el secret RELEASE_PAT

El auto-merge y el auto-tag necesitan un token propio (el `GITHUB_TOKEN` normal
**no** dispara el build al crear el tag).

1. GitHub -> tu foto -> **Settings** -> **Developer settings** ->
   **Personal access tokens** -> **Fine-grained tokens** -> **Generate new token**.
2. **Resource owner**: la organizacion `AppsAlmex`. **Repository access**: *Only
   select repositories* -> `py_Certificados_Calidad`.
3. **Permissions** (Repository):
   - **Contents**: Read and write
   - **Pull requests**: Read and write
4. Expiracion: 90 dias (renovar cuando caduque).
5. Copia el token.
6. En el repo: **Settings** -> **Secrets and variables** -> **Actions** ->
   **New repository secret**. Nombre: `RELEASE_PAT`. Valor: el token.

> Ya existe `UPDATE_TOKEN` (para la autoactualizacion del .exe). Este es otro,
> distinto, con permiso de escritura.

### Paso 4 — Proteger main (Ruleset)

**Settings** -> **Rules** -> **Rulesets** -> **New ruleset** -> **New branch ruleset**.

- **Ruleset Name**: `Proteger main`
- **Enforcement status**: **Active**
- **Target branches** -> **Add target** -> **Include by pattern**: `main`
- Activa estas reglas:
  - ☑ **Restrict deletions** (no borrar main)
  - ☑ **Block force pushes** (no reescribir historia)
  - ☑ **Require a pull request before merging**
    - Required approvals: **0** *(por ahora te auto-apruebas; el trabajo entra
      sin revisor externo. Subelo a 1 cuando tengas equipo.)*
    - ☑ Dismiss stale approvals (opcional)
  - ☑ **Require status checks to pass**
    - ☑ Require branches to be up to date before merging
    - **Add checks** -> busca y agrega **`tests`** (el job de `ci.yml`).
      *(Aparece en la lista tras la primera corrida de un PR; si no sale,
      abre un PR de prueba dev -> main y vuelve.)*
- **Create**.

Con esto: nadie puede pushear directo a main, ni mergear sin el check `tests`
verde (que incluye el coverage 80%).

> **Bypass list**: dejala vacia. Si te pones a ti como bypass, podrias saltarte
> la proteccion sin querer.

---

## Día a día

```
# 1. Nueva feature desde dev
git checkout dev && git pull
git checkout -b feature/mi-cambio

# 2. Trabajas, commiteas
git add -A && git commit -m "feat: ..."
git push -u origin feature/mi-cambio

# 3. La integras a dev (PR o push directo a dev)
#    Si haces PR feature -> dev, ci.yml corre los tests.

# 4. Cuando dev tiene lo que va al proximo release, abres el PR dev -> main:
gh pr create --base main --head dev --title "Release semanal" --body "..."
#    (para minor/major:  gh pr create ... --label minor)
```

El PR `dev -> main` queda **abierto**. El **lunes 7am** el workflow lo mergea
solo, crea el tag y sale el Release con el `.exe`. No tienes que hacer nada mas.

### Forzar un release fuera del lunes

**Actions** -> **Release lunes (dev -> main)** -> **Run workflow**. Corre el
mismo proceso al instante (util para probar).

---

## Coverage 80%

Ya esta forzado en `pytest.ini` (`--cov-fail-under=80`). `ci.yml` corre `pytest`
en cada PR, asi que un PR con coverage < 80% **falla el check `tests`** y main no
lo deja mergear. No hay que configurar nada extra en GitHub.

---

## Notas / gotchas

- **Timezone**: Mexico City es UTC-6 todo el ano (sin horario de verano desde
  2022). Por eso el cron es `0 13 * * 1`. Si cambia la zona, ajusta la hora UTC.
- **El PR debe existir el lunes**: si no hay PR abierto `dev -> main`, el
  workflow no hace nada (no falla).
- **Checks en rojo el lunes**: si el PR no esta verde, el merge falla y no hay
  release esa semana. Se reintenta el siguiente lunes (o a mano con Run workflow).
- **RELEASE_PAT caduca**: cuando expire, el auto-merge dejara de funcionar.
  Renueva el token y actualiza el secret.
- **minor/major**: agrega la etiqueta `minor` o `major` al PR `dev -> main`
  antes del lunes. Crea esas labels en **Issues -> Labels** si no existen.
