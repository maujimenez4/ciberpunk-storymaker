# Iteración de tuning · `escritor` v1 → v2

**Qué pide el encargo** (§5, *Evaluación del sistema*): «una iteración de tuning documentada, con los resultados antes y después». Esta es real: salió de la primera corrida de evals del 2026-09-24 y se midió sobre la base de datos (`ejecucion`, `intento_descartado`, `version_texto`), sin mirar prosa.

## El síntoma

B3 (`evals/briefs/b3-trampa-temporal.json`) escaló su capítulo 1 con `escritor.v1`:

| Intento | Palabras | Defecto |
| --- | --- | --- |
| 1 | 812 | `EST-02` (extensión fuera de 1.000–1.500) |
| 2 | **141** | `EST-02`. **No era prosa**: el modelo contestó comentando la reparación («He revisado el paquete de reparación dirigida…») |
| 3 | 621 | `EST-02` → **escalado**; la novela se detiene |

Ejecuciones: `v1 rechazada`, `v1 rechazada`, `v1 escalada`.

## El diagnóstico

1. **El prompt v1 no decía cuánto debía medir el capítulo.** La extensión solo aparecía como un dato del paquete («Extensión objetivo: 1200»), no como restricción.
2. **La reparación de `EST-02` era contraproducente**: citaba el capítulo **entero** como «pasaje» —dos veces en el prompt— y ordenaba «corriges exactamente lo que se señala y dejas intacto todo lo demás», lo contrario de ampliar. El intento 2, que respondió hablando de la reparación, lo muestra.

## El cambio (commit `35cca58`)

- **`escritor.v2.md`**: la extensión pasa a **restricción dura**, al principio y al final del prompt (`CLAUDE.md` §10), con qué hacer si se queda corta (dramatizar más, no rellenar). La v1 se conserva sin editar.
- **La reparación de `EST-02`** deja de citar el capítulo y dice **cuántas palabras tiene, cuántas faltan** y cómo ampliar sin añadir hechos (`Reparacion.como_linea`).

## El resultado (misma rúbrica de puertas, `escritor.v2`)

| Obra · capítulo | Intento 1 | Intento 2 | Resultado |
| --- | --- | --- | --- |
| Novela de ejemplo · 1 | 840 (`EST-02`, `SEG-02`) | **1.010** | aprobado |
| Novela de ejemplo · 2 | 884 (`EST-02`) | **1.046** | aprobado |
| Novela de ejemplo · 3 | 802 (`EST-02`) | **1.443** | aprobado |
| B5 (eval, obra 9) · 1 | 935 (`EST-02`) | **1.346** | aprobado |
| B5 (eval, obra 9) · 2 | **1.043** a la primera | — | aprobado |

**Lectura honesta:**

- **La reparación es lo que funcionó.** Con v2, **cinco de cinco capítulos pasan**, cuatro con una sola reparación; con v1, cero de uno, escalado tras dos.
- **El primer intento sigue saliendo corto** (802–935 palabras) en cuatro de cinco: la restricción en el prompt **no basta sola** con Haiku 4.5. Es la siguiente iteración si se quiere ahorrar la llamada de reparación (≈ 0,012 USD y un par de minutos por capítulo): por ejemplo, pedir un borrador por escenas con recuento, o subir el objetivo a 1.300 para que el sesgo a la baja caiga dentro del rango.
- **Versión de prompt trazable:** cada fila de `ejecucion` lleva `prompt_version` (`v1`/`v2`) y cada span de Langfuse el `prompt_id`, la versión y el hash (plan 8 T7), que es lo que §6 pide para que el tuning «muestre qué versión de prompt produjo cada resultado».

## Cómo reproducir las cifras

```bash
uv run python evals/tabla.py        # tabla por brief, desde la base
```

y, para esta tabla, `intento_descartado` (texto y defectos de cada intento rechazado, `GET /trabajos/{id}/intentos`) cruzado con `version_texto` vigente por capítulo.

*Corregido el 2026-09-25:* las dos últimas filas decían «B1»; son de **B5** (obra 9, `evals/resultados/corridas.json`). B1 es la obra 10 y no llegó a integrar ningún capítulo. Las cifras no cambian.
