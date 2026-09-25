# Presentación · StoryMaker

Propuesta formal de **Qaracter** a **Regalos con Historia S.A. de C.V.** (cliente ficticio, mercado México): un sistema
agéntico que escribe novelas de regalo de diez capítulos, personalizadas y verificadas.

**Idioma:** español, con los términos técnicos en inglés (*harness*, *guardrails*, *evals*,
*LLM-as-judge*, *model checking*…), que es como se usan en el sector.

**Duración:** 10 minutos, más los anexos para las preguntas.

## Contenido

| Fichero | Qué es |
| --- | --- |
| `storymaker-deck.pdf` | El deck principal: 16 slides |
| `storymaker-deck.pptx` | El mismo deck en formato editable (PowerPoint) |
| `anexo-arquitectura-codigo.pdf` | A1 · Arquitectura del código: features, fronteras y tests |
| `anexo-tla-spec.pdf` | A2 · TLA+ del harness: invariantes, liveness y resultado de TLC |
| `anexo-evals-tuning.pdf` | A3 · Evals y la iteración de *tuning* del Escritor, antes y después |
| `anexo-modelo-de-datos.pdf` | A4 · El modelo de datos en SQLite: la *story bible* |
| `anexo-red-team.pdf` | A5 · Red-team: lo que rompió la corrida real y cómo se cerró |
| `anexo-modelos-y-coste.pdf` | A6 · Modelos y coste medido en Langfuse, por rol |
| Vídeo de demo, en Loom | [Ver el vídeo](https://www.loom.com/share/1df6cf16505d4c3dbfc48a39d6112a03) |

## Estructura del deck

1. Portada
2. El problema y el cliente: matriz de posicionamiento
3. Configuración: la entrevista
4. Lectura y corrección
5. Arquitectura del harness
6. Contexto, memoria, tools y hooks
7. Validadores
8. Evaluación: los cinco briefs y el *tuning*
9. Verificación formal: Lean y TLC
10. Observabilidad en Langfuse
11. Guardrails
12. Presupuesto y coste
13. Escenarios de volumen y sensibilidad
14. Riesgos y siguientes pasos
15. Demo y cierre
16. Contraportada

## De dónde salen las cifras

- **Coste por novela**: medido en Langfuse sobre la novela de ejemplo (capítulos 4 a 10, con
  reintentos): 3,45 USD en 79 llamadas, unos 4,9 USD por novela.
- **Resto del coste, en USD y para México** (1 USD ≈ 17,6 MXN): tarifa de Stripe México, soporte
  tercerizado, planes de Langfuse y DigitalOcean y tarifas de desarrollo en México. Fuentes en las
  notas de cada slide.
- **Evals**: `evals/resultados/corridas.json` y [`evals/tuning.md`](../evals/tuning.md).
- **TLC**: `formal/tla/`. **Lean**: `formal/lean/` y la puerta de publicación.
- **Hallazgos de la corrida real**: `docs/proceso/`.

El deck se hizo con Claude Design sobre el sistema de diseño de Qaracter.
