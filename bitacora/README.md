# Bitácora de agentes

Qué está haciendo cada agente **ahora mismo**, para que ninguno tenga que
deducirlo del `git status` ni preguntar. El reparto de tareas lo decide
`maujimenez4`; esto solo lo deja escrito.

No es documentación. `docs/` describe lo que es verdad del sistema (§3.1); esto
describe lo que está haciendo una sesión, y envejece a propósito.

## Un fichero por agente

`bitacora/<nombre-en-minusculas>.md`, uno por sesión: `nubia.md`, `jose.md`,
`gustavo.md`…

**No es capricho.** Somos seis sesiones escribiendo a la vez sobre el mismo
directorio de trabajo. Un único fichero compartido se pierde escrituras: dos
agentes leen, los dos añaden su línea, el segundo guarda encima del primero y
esa entrada desaparece sin que nadie se entere. Un fichero por agente no tiene
ese problema, porque cada uno solo escribe el suyo.

**Escribes el tuyo y lees los demás.** Nadie edita la bitácora de otro. Si
quieres corregir a alguien, se lo dices por mensaje y lo corrige él.

## Formato

Se **añade al final**, nunca se reescribe lo anterior: es un registro, no un
estado. Lo que dejó de ser cierto se corrige con una entrada nueva que lo diga.

```markdown
## 16:20 · Cableo el Continuista a G1a

- **Qué:** la puerta invocaba tres de los once validadores; le añado los de continuidad.
- **Ficheros:** `features/calidad/agents.py`, `features/escritura/service.py`
- **Estado:** en curso
- **Ojo:** `Dependencias` gana dos campos obligatorios; si construyes uno, los necesita.
```

- **Qué** — en una frase, y el porqué si no es evidente.
- **Ficheros** — dónde estás tocando, para que otro vea la colisión antes de abrirlo.
- **Estado** — `en curso`, `terminado` o `bloqueado`. Si es `bloqueado`, di por quién o por qué.
- **Ojo** — solo cuando afecta al trabajo de otro: una firma que cambia, una
  premisa que deja de valer, un fichero que alguien más tiene abierto. Si no
  afecta a nadie, se omite.

## Cuándo se escribe

Al empezar algo, al terminarlo, y cuando cambie algo que otro esté dando por
cierto. No hace falta narrar cada comando: la bitácora es para que otro sepa si
te pisa, no para reconstruir tu sesión.
