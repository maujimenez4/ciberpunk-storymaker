---
id: issue-report
---

Los validadores devuelven incidencias con esta forma:

```json
{
  "issues": [
    {
      "severity": "blocker",
      "kind": "canon-conflict",
      "where": "ch03 ¶4",
      "claim": "El personaje entra con su propia credencial.",
      "canon": "bible/characters.md#credenciales-revocadas",
      "fix": "Necesita una credencial prestada o forzar la entrada."
    }
  ]
}
```

- `where` — localiza en el capítulo y el párrafo. Sin esto, el escritor tiene que
  adivinar dónde mirar y reescribe de más.
- `claim` — qué dice el texto, citado o parafraseado corto.
- `canon` — la entrada de biblia o de notas con la que choca, o `null`.
- `fix` — qué habría que hacer. Concreto y accionable, no «revisar esto».

## Severidad: la decisión cara

| | Qué es | Qué provoca |
|---|---|---|
| `blocker` | Contradice el canon, afirma un hecho sin respaldo de forma sustantiva, o usa un término prohibido. | **Reescribe el capítulo entero.** |
| `warning` | Debilita el texto, pero no lo hace falso ni incoherente. | Se imprime en la compuerta para que juzgue una persona. |
| `note` | Observación de oficio. | Se imprime en la compuerta. |

**Solo `blocker` dispara reescritura.** Si toda observación forzara reintento, se
gastarían todos los intentos en comas y el capítulo nunca llegaría a la compuerta.

Antes de marcar un `blocker`, pregúntate si un lector atento se detendría. Si solo se
detendría un corrector, es `warning`.

Si no encuentras nada, devuelve la lista vacía. No inventes una incidencia menor para
justificar el turno: cuesta dinero y no ayuda a nadie.
