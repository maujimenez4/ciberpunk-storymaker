---
name: sourced-notes-format
description: Forma de una nota con fuente: afirmación, fuente, fecha de consulta y confianza. Y cómo se declara un hueco.
---

Una nota con fuente tiene esta forma exacta:

```markdown
### <la afirmación, en una frase>

- **Fuente:** <publicación o institución> — <URL>
- **Consultado:** <YYYY-MM-DD>
- **Confianza:** alta | media | baja
- **Matiz:** <opcional: qué no dice la fuente, o dónde deja de valer>
```

Reglas que hacen que el formato sirva de algo:

- **Una afirmación por nota.** Si un párrafo afirma tres cosas, son tres notas. Media
  nota no se puede verificar.
- **Sin fuente no hay nota.** Cuando algo no se pueda respaldar, se escribe así:

  ```markdown
  ### HUECO: <la pregunta que quedó sin respuesta>

  - **Buscado:** <qué se intentó>
  - **Resultado:** sin fuente utilizable.
  ```

  Un hueco declarado es información útil: el escritor sabe que no puede afirmar nada
  ahí. Un hueco tapado con una invención es una avería que se detecta tres pasos después.
- **La fecha de consulta es obligatoria**, incluso para lo que parece estable. Es lo que
  permite decir más tarde que una nota envejeció.
- **Confianza baja no es inútil**: es una nota que el escritor usará con cautela y el
  verificador tratará con manga ancha.
