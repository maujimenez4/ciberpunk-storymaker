# Validación visual de la lectura publicada

**Qué cubre.** El último punto de la validación programática del encargo (§5a): *«el agente
abre la novela en el browser, navega por los capítulos y verifica que el índice, la ficha de
personajes y la portada renderizan correctamente; si detecta un error visual, lo registra como
fallo»*, y el requisito de la sección «Claude Code»: *«el uso real del browser MCP debe estar
documentado en `/docs`: qué inspeccionó el agente, qué detectó y qué cambio provocó»*.

Son **dos navegadores distintos** (`architecture.md` §3.5.1) y aquí se documentan los dos:

| | Validador en código | Browser MCP |
| --- | --- | --- |
| Qué es | `app/features/calidad/visual.py`, Chromium de Playwright conducido por código | El servidor Playwright MCP de `.claude/mcp.json`, usado por Claude Code |
| Quién decide | Nadie: reglas fijas, sin modelo | El agente de código, mirando |
| Qué mira | Lo comprobable: que abre la vista pedida, `h1`, dedicatoria, índice contra capítulos, prosa, enlace al PDF, ficha | Lo que un test no mira: jerarquía de encabezados, foco visible, contraste, que se lea bien |
| Qué deja | Defectos `REN-01`, *scores* `rutas_estables` e `inspeccion_visual` | Una fila en la tabla de resultados de abajo |

**Estado a 2026-09-24:** el validador en código existe y tiene tests (`2b4e3fa`). **Todavía no
se ha corrido contra una novela publicada real, ni se ha usado el browser MCP.** Las tablas de
resultados están vacías a propósito: se rellenan después de la corrida real y no antes.

---

## 1 · El validador en código

Dos validadores, con los nombres de `verification.md` §8.1, y en este orden:

1. **`rutas_estables`**: cada vista responde con 200 **y abre la pestaña pedida**. Protege al
   siguiente: si la dirección cambia, `inspeccion_visual` estaría mirando otra pantalla y daría
   verde (R-8). Una vista que no pasa este no se inspecciona.
2. **`inspeccion_visual`**, sobre `?vista=leer` y `?vista=quien-es-quien`:
   - portada con un solo `h1` y **dedicatoria** (se desactiva con `--sin-dedicatoria`);
   - **índice** con exactamente las entradas `1..N` (`--capitulos`, 10 por defecto): once para
     diez renderiza perfectamente y aquí falla;
   - un capítulo pintado por cada entrada, **con prosa**, sin aviso de error, y **alcanzable**:
     el validador pulsa cada entrada del índice y comprueba que el capítulo queda en pantalla;
   - enlace al PDF;
   - la ficha «Quién es quién» pintada y sin aviso de error. **No se exige que tenga entradas**:
     el revelado es progresivo y un navegador limpio no ha leído nada.

Cada fallo es un `REN-01` con una **cita estructural** («vista=leer: capitulo 3 sin prosa»),
nunca prosa del manuscrito. Cada validador **que corrió** emite su *score* (1 pasa, 0 falla);
si no se pudo abrir ninguna página, `inspeccion_visual` no puntúa, porque no corrió.

### Cómo se lanza

Con la novela publicada y la lectura levantada (backend en `:8000`, `pnpm dev` en `:5173`),
desde la raíz del repositorio:

```bash
uv run python src/backend/scripts/validacion_visual.py --token <token de la versión publicada>
# opciones: --base http://127.0.0.1:5173  --capitulos 10  --sin-dedicatoria
#           --capturas <directorio fuera del repo>  --obra-id <id>  --json
```

- Sale con **0** si aprueba y **1** si hay algún `REN-01`.
- `--obra-id` manda los dos *scores* a la sesión de Langfuse de esa novela (traza
  `validacion_visual`, span `inspeccion_visual`). Sin las credenciales de Langfuse no se emite nada
  y se avisa.
- Las capturas (una por vista y una por capítulo navegado) van por defecto al directorio
  temporal. **Contienen prosa: no se commitean** (`CLAUDE.md` §16).
- No llama al modelo. Necesita el Chromium de Playwright (`uv run playwright install chromium`).

### Lo que no hace, dicho

- **No devuelve el fallo al Escritor.** El encargo dice «lo devuelve al writer»; un `REN-01` es
  un fallo de la interfaz, no de la prosa, y reescribir un capítulo no arregla un índice que no
  pinta. Queda declarado en `proceso/trade-offs.md` T-36.
- **No está en `CATALOGO_DE_MANUSCRITO`.** G4 corre dentro de `publicar`, en proceso y sin la
  lectura levantada: engancharlo ahí haría que la puerta dependiera de un servidor de frontend.
  Se corre a mano tras publicar, y por eso emite a Langfuse por su cuenta.
- **No juzga la estética ni la accesibilidad.** Eso es del paso 2.

### Resultado de la corrida real

*Pendiente. Se rellena tras correrlo contra la versión publicada de la novela de ejemplo.*

| Fecha | Versión publicada | `rutas_estables` | `inspeccion_visual` | Defectos `REN-01` | Qué se cambió después |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

---

## 2 · El browser MCP (Claude Code)

`.claude/mcp.json` declara el servidor:

```json
{ "mcpServers": { "playwright": { "command": "npx",
  "args": ["-y", "@playwright/mcp@latest", "--browser", "chromium"] } } }
```

### Procedimiento

1. Levantar backend y frontend con la novela publicada, y tener su token.
2. Abrir una sesión de Claude Code en la raíz del repositorio y comprobar con `/mcp` que el
   servidor `playwright` está conectado. **Anotar la versión que `npx` resolvió** (no se inventa:
   se copia de la ejecución).
3. Pedir al agente que abra `http://127.0.0.1:5173/?token=<token>&vista=leer` y
   `...&vista=quien-es-quien`, y que inspeccione:
   - jerarquía de encabezados (un `h1`, capítulos en `h2`, etiquetas de la ficha en `h3`);
   - foco visible recorriendo con Tab las pestañas y el índice, y flechas entre pestañas;
   - contraste de texto e interfaz en los tres temas de «Aa»;
   - que el índice tiene **diez** entradas y cada una lleva a su capítulo;
   - que la dedicatoria está antes del índice y no aparece como capítulo;
   - el PDF: que se descarga y abre.
4. Por cada hallazgo: si es un fallo, se arregla con su test y se vuelve a mirar; si no hay
   ninguno, se escribe eso y **por qué es creíble**.
5. Rellenar las tablas de abajo con el commit de cada cambio.

### Qué inspeccionó el agente

*Pendiente.*

| Fecha | Versión de `@playwright/mcp` | URL / vista | Qué miró |
| --- | --- | --- | --- |
| | | | |

### Qué detectó y qué cambio provocó

*Pendiente.*

| Hallazgo | Dónde | Qué cambió (código o prompt) | Commit |
| --- | --- | --- | --- |
| | | | |

### Qué no detectó

*Pendiente.* Lo que esta inspección no puede ver por construcción: la calidad de la prosa, la
personalización, y cualquier cosa de una vista que no se abrió.
