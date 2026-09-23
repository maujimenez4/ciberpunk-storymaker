# Bitácora — Jose

## 2026-09-23 · Auditoría de la corrida del 22-sep · terminado

**Qué.** Verifiqué el proceso de la sesión Julio y audité `manuscrito-real.txt`
contra la base de su corrida. El manuscrito se contradecía a sí mismo con cero
defectos registrados. Causa: la biblia guardada era `{}` y las capas del paquete
eran constantes en las diez escenas (canon 36, estado 32, memoria 32).

**Ficheros.** Ninguno. Solo lectura.

**Estado.** terminado.

## 2026-09-23 · El Continuista, en el bucle · terminado

**Qué.** G1a invocaba tres de los once validadores y el Continuista no existía
como agente. Cableado en TDD, con la fase 11 del plan de 001.

**Ficheros.** `features/calidad/agents.py` y `repository.py` (nuevos),
`features/calidad/{__init__,schemas,defectos}.py`, `features/escritura/
{router,service}.py`, `commons/llm/json_de_modelo.py`, `corrida.py`,
`specs/001-backend-v1/{plan,spec}.md`. Commits `2193724` y `9e02d50`.

**Ojo.** `Dependencias` gana dos campos **obligatorios**, `continuista` y
`defectos`. Quien construya el ciclo en un sitio nuevo los necesita. Y CAN-01 y
CON-03 **no bloquean G1a** por decisión de maujimenez4 del 2026-09-23: daban
falsos positivos. Volver a meterlos en `BLOQUEANTES_EN_G1A` es una decisión
nueva, no una restauración.

**Estado.** terminado.

## 2026-09-23 · Los siete defectos de `validadores.py` · terminado

**Qué.** Los seis de la spec 002 (Gustavo) más H-7 (Hernán). Autorizado de viva
voz por maujimenez4; **la spec 002 sigue en `borrador` y sin `plan.md`**, así que
esto es código por delante de su spec y conviene que se vea. Dos de los siete
—el nivel de calor fuera de escala y `validar_discurso` con persona o tiempo
desconocidos— fallaban **en abierto**: devolvían `[]`, que la puerta lee como
«limpio».

**Ficheros.** `features/calidad/validadores.py`, `commons/errors/` (nueva
`EntradaFueraDeDominio`), `features/calidad/prompts/continuista.v2.md`,
`features/calidad/tests/test_invariantes.py` (nuevo),
`calidad/tests/{test_validadores,test_puerta}.py`,
`escritura/tests/test_continuidad_en_g1a.py`, `specs/002-.../sonda_invariantes.py`.

**Ojo.** `Afirmacion.objeto` se parte en `objeto` (cosa física, CON-02) e
`informacion` (lo que alguien sabe, CON-03). Quien construya una `Afirmacion`
tiene que elegir campo. Y `solo_narracion` ya no se come la narración tras el
inciso, así que **VOZ-03 empieza a ver** lo que llevaba sin ver desde que existe:
puede aparecer VOZ-03 donde antes no salía nada.

**Estado.** terminado. 436 tests, cinco puertas en verde, sin commitear.

## 2026-09-23 · Auditoría del manuscrito del 23-sep · terminado

**Qué.** Auditoría de `evidencia-corridas/corrida-real-2026-09-23/`. La
continuidad mejora mucho respecto al 22-sep, pero el manuscrito **no está
cerrado**: es8 escaló por SEG-01 y aun así aparece entera en el `.md` y el `.pdf`.

**Ficheros.** Ninguno. Solo lectura.

**Ojo.** `RepositorioDeManuscrito.ensamblar` selecciona por `version_texto.
vigente = 1` y **no mira el estado del trabajo**, así que una escena rechazada por
la puerta de calidad entra igual en el entregable. Afecta a quien dé por bueno un
manuscrito exportado.

**Estado.** terminado.
