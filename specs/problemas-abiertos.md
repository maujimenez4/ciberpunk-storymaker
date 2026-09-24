---
id: problemas-abiertos
titulo: "Lo que está roto, a medias o sin dueño, y quién lo cierra"
estado: vivo              # se actualiza al cerrar cada fase; no se aprueba ni se archiva
fecha: 2026-09-24
---

# Problemas abiertos

**Qué es este fichero.** Lo que hoy está **roto, a medias o sin dueño**, con quién lo cierra y qué cuesta dejarlo. No es la lista de lo que falta por construir —eso es [`hoja-de-ruta.md`](hoja-de-ruta.md)— ni el cruce contra el encargo —eso es [`estado-del-entregable.md`](estado-del-entregable.md)—: es **lo que ya está construido y no está bien**.

**Reescrito el 2026-09-24 por la tarde**, con cada entrada comprobada contra el código o `git log`. **Los números no se reutilizan**: las entradas vivas conservan el suyo, las nuevas empiezan en P-19, y las cerradas pasan a la tabla del final con el commit que las cerró.

**Orden:** primero lo que impide generar la novela de ejemplo, después lo que falsea una medida, después las deudas.

---

## Bloquean la novela de ejemplo

### P-19 · El nombre del destinatario sale como `[NOMBRE_ANONIMIZADO]`

**Severidad: una novela de regalo sin el nombre de quien la recibe no es entregable.**

Con el brief de ejemplo el outline sale personalizado —el perro Luna, el verano en Cádiz— y el protagonista se llama `[NOMBRE_ANONIMIZADO]`, con sufijo numerado. No es un defecto del código: es una política de datos personales aplicándose sobre la salida del modelo.

**Solución acordada, sin implementar:** los agentes trabajan con un marcador y el código sustituye el nombre real **al servir**; el canon guarda el marcador, para que la sustitución siga siendo un único punto. `grep` de un marcador en `src/` no encuentra nada; solo lo mencionan `README.md` y `RELEVO.md`.

**Lo que hay que decidir al hacerlo:** contra qué texto comparan los vetos y `nombres_literales` (¿el marcado o el servido?), y el término: `marcador` **no está en `docs/definitions.md`** y `CLAUDE.md` §2 exige confirmarlo antes de escribir código con él.

**Quién:** plan nuevo del backend (tramo 1 de la hoja de ruta), con firma de `maujimenez4`.

### P-20 · Una escalada no deja nada que revisar

**Severidad: «revisión humana» es un estado al que se llega y del que no se sale.**

En la corrida real el capítulo 1 escaló tras tres intentos, con **cero texto, cero filas de defecto** y tres ejecuciones `rechazada` sin código. No se distingue «el modelo escribió mal tres veces» de «un validador atascado rechaza siempre».

Comprobado: `ciclo._retirar_lo_descartado` **borra** las `version_texto` del `run_id` al rechazar, y no existe tabla `defecto` (`Defecto` es un modelo de Pydantic sin persistencia). El `RELEVO.md` decía que el arreglo estaba «en curso»: **no ha entrado nada** en `git log` y el árbol está limpio salvo `src/frontend/.gitignore`.

**Lo que complica:** el borrado existe por R-7 —que la prosa descartada no contamine el paquete del capítulo siguiente—. Conservarla exige que quede **fuera** de lo vigente, no que deje de borrarse. Y guardar defectos es esquema nuevo (`CLAUDE.md` §3 regla 7).

**Quién:** el mismo plan que P-19.

---

## Falsean una medida

### P-21 · Continuista y Crítico corren en serie

`escritura/service.py`: `continuista` y `critico` se esperan uno detrás de otro, sin `gather` ni `TaskGroup`. `CLAUDE.md` §4.1 autoriza solaparlos dentro del techo concurrente. Medido: ~8 minutos por capítulo y ~80–90 por novela; el ahorro estimado es de 10–15 minutos por novela, **no medido**.

**Antes de hacerlo hay que resolver una contradicción:** este fichero midió la sobrecarga del CLI en **~1.800 tokens por llamada**, constante; `RELEVO.md` dice **33.000–49.000 por llamada en corrida real**. Si la segunda es cierta y cuenta para el techo, dos llamadas en vuelo pueden pasar de 100.000 aunque sus paquetes quepan. **Ninguna de las dos cifras se ha podido verificar desde el repositorio.**

**Quién:** el plan del tramo 1. **Coste de dejarlo:** una novela un 15 % más lenta; nada se rompe.

### P-22 · Langfuse: está cableado y nunca se ha visto funcionar

Cuatro cosas, comprobadas en `commons/observabilidad/`:

1. **`_SpanLangfuse.puntuar` descarta `criterio`**: manda `name`, `value` y `comment`. Las seis puntuaciones del juez llegan con **el mismo nombre** y no se pueden separar, que es exactamente lo que `RF-JUZ-05` compara con la revisión humana.
2. **No hay `flush` al apagar**: el `lifespan` de `main.py` no toca el observador. Lo último de una corrida se puede perder.
3. **Ningún span lleva `prompt_id`, versión ni hash**: el protocolo `Span` tiene `entrada`, `salida`, `consumo` y `puntuar`, y nada más. §6 pide los prompts versionados en Langfuse, y **plan-6 T11 da por hecho ese dato**.
4. **El Entrevistador no tiene traza**: la sesión se deriva de `obra_id`, que no existe durante la entrevista. Decisión pendiente en `architecture.md` §9.2.1.

Y el conjunto **nunca se ha ejercitado contra un Langfuse real**: la suite corre con dobles, por diseño (`CA-4`).

**Quién:** 1–3, el plan del tramo 1, **antes de la corrida**; 4 lo decide `maujimenez4`. **Coste de dejarlo:** una corrida cuyas trazas no sirven para el *tuning*, y hay que repetirla.

### P-18 · El coste imputado se queda corto cuando la caché acierta — **a medias**

La primera mitad está cerrada: `Consumo` guarda `cache_read_input_tokens` y `cache_creation_input_tokens` (`1a265b2`). **La segunda no**: `coste_derivado` sigue mirando solo entrada y salida, porque imputar la caché exige **una tarifa declarada**, y eso es decisión de `maujimenez4`, no de implementación. Medido contra el proveedor: 10 tokens de entrada imputados frente a 6.845 leídos.

**Coste:** la comparación de plantillas del *tuning* mide suerte de caché.

### P-27 · Lean no comprueba edades, y el brief de trampa temporal cuenta con que sí

`manuscrito/lean/plantilla.lean` tiene dos invariantes —`sinUbicuidad` y `sinReaparecidos`— y explica por qué **no** incluye el de edad contra fecha de nacimiento: solo el destinatario tiene fecha y no es un `Personaje`, así que sería una tautología. La razón es buena. **Pero tiene dos consecuencias que nadie había cruzado:**

- **§5c pide que el fichero Lean incluya fechas de nacimiento**, y no las incluye.
- **B3 de plan-6** está diseñado para que lo cace exactamente ese invariante. Tal como está, B3 no fallaría en G4 y la tabla de evals mentiría en su fila más importante.

**Quién:** `maujimenez4` elige entre rediseñar B3 contra los invariantes que existen o dar fecha de nacimiento a los personajes y añadir el invariante. **Antes de ejecutar plan-6 T10.**

### P-28 · Si Lean falla, el fallo no vuelve a nadie

§5c y `RF-FOR-03` dicen que el fallo «vuelve al editor como feedback». `CronologiaIncoherente` solo se captura en tests: en producción acaba en un `409` al frontend. No existe el Editor de línea ni ningún camino que devuelva el fallo a un rol.

**Quién:** sin dueño. **Coste:** la mitad de un requisito M del encargo; se puede declarar como decisión en `trade-offs.md` si no da tiempo.

---

## Contratos que nadie comprueba

### P-23 · `openapi.json` no tiene test contra la app

Los tests que miran el OpenAPI piden `/openapi.json` **a la app viva**, no al fichero commiteado del que `pnpm install` genera el cliente. Ya se desincronizó una vez hoy (`ee5a265`). **Quién:** quien toque el próximo endpoint; es un test de diez líneas.

### P-3 · `CA-33` vuelve a no poder cumplirse

Se cerró con la spec v3.3 (`6248b53`), que fija **dieciséis** endpoints de `RI-01` a `RI-12` más `RI-15`. Hay **quince**, y no son esos: faltan `RI-09` y `RI-10` (plan 5), falta `RI-12` (`GET /obras/{id}/canon`), `RI-11` se implementó como `/lectura/{token}/…` en vez de `/obras/{id}/versiones/…` —por decisión de la 002, razonada en `manuscrito/router.py`— y sobra `GET /obras/{id}/novela`, que la spec no nombra.

**Quién:** una persona, con la spec delante, cuando cierre el plan 5. **Es cambio de requisito y vuelve a firma.**

### P-29 · El plan 3 del frontend está implementado y sin firmar

`002-frontend/plan-3-una-pagina.md` está en `borrador` y su trabajo entró en `fccc576` y `e306770`. Es la puerta Código de `CLAUDE.md` §3.2 cruzada sin abrir. Y el patrón inverso: los planes 4, 6 y 7 del backend y 1 y 2 del frontend dicen `aprobado` con tareas hechas y otras sin empezar, sin que nada lo refleje.

**Quién:** `maujimenez4`. Un agente no puede firmar ni marcar `completado`.

---

## Flecos con dueño claro

### P-24 · Frontend

| Qué | Evidencia |
| --- | --- |
| La ficha **no enlaza a los capítulos** en producción | `QuienEsQuien` acepta `onIrACapitulo`; `Paginas.tsx:172` no se lo pasa. §2 lo pide |
| «+N» sin revelar | Necesita que el backend mande un número (`RF-FIC-05`) sin filtrar las entradas |
| La posición guardada no se usa al abrir | `Sumario` solo usa `recordar` de `usePosicion`; nadie hace *scroll* a lo guardado |
| Código muerto | `components/Lectura.tsx` (solo lo exporta el `index.ts`) y `app/Muestra.tsx` (no lo importa nadie) |
| `src/frontend/.gitignore` modificado sin commitear | El diff es **una línea en blanco al final**, no una entrada `.env` |

**Quién:** una sesión de frontend. **Coste:** el primero incumple §2; el resto es limpieza.

### P-25 · Reanudación vista desde fuera

- **Entre el outline y `POST /novela`, una recarga se queda en «escribiendo» para siempre**: `avance_de_la_novela` devuelve `escribiendo` sin `en_curso` cuando hay capítulos y ningún trabajo (`novela.py:349`), y el frontend nunca lanza la novela.
- **No hay latido**: un trabajo vivo de un proceso muerto se lee como «escribiendo» hasta la próxima reanudación. Lo dice el propio docstring.
- **`POST /obras/{id}/publicar` sobre una obra inexistente responde `409`**, no `404`: `publicar` lanza `ObraSinCapitulos` antes de mirar si la obra existe.
- **El docstring de `ObraDesconocida`** (`outline/service.py:49`) dice que se traduce a 409; hereda de `RecursoDesconocido` y da **404**.

**Quién:** plan del tramo 1 o sesión suelta. **Coste:** el primero deja a un comprador mirando una espera eterna.

### P-26 · Forma

`ruff format --check` marca **dos** ficheros —`escena/agents.py` y `obra/agents.py`—; `outline/agents.py` ya pasa. Y `obra/agents.py` llama `PLANTILLA_V1` a la plantilla que lee `entrevistador.v2.md`: un nombre que miente sobre la versión, en el proyecto que prohíbe editar plantillas en sitio.

### P-30 · `docs/proceso/` se ha quedado atrás

`registro-de-iteraciones.md` §«Lo que este registro todavía no puede tener» afirma que no hay `.tla` ni fallo de Lean, y los dos existen. No recoge los seis arreglos de la corrida real de hoy. El uso real del browser MCP no consta porque no ha ocurrido. **Es eliminatorio** y es barato. **Quién:** cualquier sesión, con `coherencia-docs`.

### P-31 · Qué son «dos hooks» no está razonado

El encargo §3 pone los hooks junto a `CLAUDE.md` y la skill, que son artefactos de Claude Code. El proyecto los implementa como puntos de enganche en código (`CLAUDE.md` §11), lo cual es defendible, pero **ningún documento discute la otra lectura** y no hay `.claude/settings.json`. Tampoco hay comandos `/` propios ni ficheros de memoria en `.claude/`. **Quién:** `maujimenez4`, una línea en `trade-offs.md`.

---

## Deudas que vencen al regenerar · plan 5

### P-6 · `evento` y `hecho_canon` no tienen `run_id`

Siguen sin él. El guardia de idempotencia los reconoce por escena; **deja de ser exacto al regenerar**. Y `una_sola_vez` sigue **sin un solo llamador de producción** (solo `idempotencia.py` y `escritura/__init__.py`). **Plan-5 T1.**

### P-7 · `resumen_capitulo` tiene `UNIQUE(capitulo_id)` y siempre inserta

Inalcanzable hoy; regenerar un capítulo integrado lo alcanza. **Plan-5 T1.**

### P-8 · `hecho_canon.sustituye_a` sigue sin llamador de producción

**Plan-5 T2.** Es literalmente «el perro se llama Nala».

---

## Deudas de estructura y vocabulario

### P-9 · `hecho_canon` vive en `features/obra` y lo escribe `canon`

Sigue igual (`obra/modelos.py:146`). Sin fecha: decidir antes de que una tercera feature escriba ahí.

### P-10 · `SalidaMalFormada` va por cinco copias

`outline`, `obra`, `escena`, `canon` y `calidad`. `CLAUDE.md` §5.1 regla 4 pide subirla al tercer uso. Vencida desde la Fase 3.

### P-11 · `checkpoint` no está en `docs/definitions.md`

Cero apariciones. Y ahora hay más vocabulario de la máquina fuera del documento: `PROCESO_INTERRUMPIDO`. **Una persona.**

---

## Lo que impone el entorno

### P-13 · `tiktoken` descarga su vocabulario la primera vez

`ContadorTiktoken` sigue cargando `cl100k_base` con `tiktoken.get_encoding`. En una máquina sin red y sin caché, el primer `contar()` falla. Cerrarlo pide vendorizar ~1,6 MB.

### P-14 · La semilla no hace reproducible la llamada

El proveedor no la admite. Sigue siendo cierto y no tiene arreglo: se registra para reconstruir el paquete, no la prosa.

### P-15 · «Autenticado» no lo comprueba nadie — **reformulado**

**El binario no es el problema:** `claude_agent_sdk` trae el suyo (`_bundled/claude.exe`, ~240 MB), así que `uv sync` ya lo instala. El `README.md` y `.env.example` piden instalar `claude` aparte, **lo cual sobra**. Lo que falta es la **autenticación de la cuenta**: ninguna puerta la comprueba al arrancar, y sin ella el fallo aparece a mitad de una corrida. Además el backend **no carga `.env`** (cargarlo exigiría `python-dotenv`, dependencia nueva que se pregunta); hoy se lanza con un script fuera del repositorio.

**Quién:** plan del tramo 1 o sesión suelta; corregir el `README.md` es inmediato.

---

## Una del proceso

### P-16 · El reparto por fichero corta las tareas por donde pasa el cable

Sigue siendo cierto y `RELEVO.md` lo recoge como regla: **las junturas tienen dueño desde el reparto**. Se mantiene hasta que un plan lo aplique y se vea que basta.

---

## Cerrados

| Id | Qué era | Cerrado por |
| --- | --- | --- |
| **P-1** | El CLI cargaba el `CLAUDE.md` del repositorio y la entrevista respondía sobre el proyecto | `bf0edc8` — `setting_sources=[]`; `None` significa «todas» |
| **P-2** | `elementos_obligatorios` sin columna: la cobertura aprobaba sin comprobar | `edb8edc`, `0d25b26` |
| **P-4** | `CON-03` era una opinión del modelo, no un contraste contra el ledger | `1d92785` |
| **P-5** | El hook de policy no existía | `168461a` |
| **P-12** | `Senal` no tenía causa para «el proceso murió» | `2de6027` — `PROCESO_INTERRUMPIDO` |
| **P-17** | El Continuista estaba construido y no lo llamaba nadie | `1899ccf`, `bab4dd7` |
| **P-3** | Catorce endpoints en `CA-33` y había quince | `6248b53` — **reabierto** arriba con otra forma |
| **P-18**, primera mitad | Los tokens de caché se perdían | `1a265b2` — la imputación sigue abierta |
| *(sin número)* | Formulario con otro contrato · `database is locked` en RI-02 · el frontend publicaba sin escribir · obra sin capítulos publicable · `openapi.json` sin `/publicar` · Arquitecto rechazado por `tipo_de_corte_final` | `e275c8e` · `596faba` · `d887bb0`, `0662fcb`, `a045100`, `38a260d` · `b0871ac` · `ee5a265` · `0513035` |
