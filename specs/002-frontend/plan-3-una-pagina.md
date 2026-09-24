---
id: 002-frontend / plan-3-una-pagina
titulo: "Fase 3 — Un enlace, una página, tres vistas"
estado: borrador          # borrador | en-revision | aprobado | completado
aprobado_por:             # lo rellena una persona, nunca un agente
fecha: 2026-09-24
spec: specs/002-frontend/spec.md      # D-06, firmada en 02fc0a0
---

# Fase 3 — Un enlace, una página, tres vistas

**Objetivo:** que `/l/{token}` sea la única dirección de la lectura, y que dentro vivan **leer**, **la entrevista** y **quién es quién**.

**Enfoque:** el router se reduce, la casa se queda. `RUTAS`, los tokens de `estilos.css`, `Pagina` y los cuatro primitivos siguen siendo la base; lo que cambia es cuántas direcciones hay y qué se pinta dentro de una.

**Spec:** [`spec.md`](spec.md), **D-06**, decidida por `maujimenez4` el 2026-09-24.

---

## Lo que esta fase invierte, y por qué se escribe antes de tocar nada

Cinco URLs eran la forma natural de una aplicación web y **la forma equivocada de un regalo**. El enlace se comparte por mensajería, se reenvía y se pega: cada dirección de más es una manera de que alguien reciba la página tres sin saber que hay una uno.

**Lo que no se tira:** T1, T3 y T4 del plan 1 siguen enteras. Las fronteras de ESLint, los tokens, los primitivos y `Pagina` no se tocan.

---

## Requisitos de la 002 que quedan sin efecto

Se declara aquí y no se descubre implementando. **Ninguno se borra de la spec:** se dice qué pasa con él.

| Requisito | Qué le pasa |
| --- | --- |
| **RI-02, RI-03, RI-04, RI-05** | **Decaen como rutas.** Índice, capítulo, ficha y novedades dejan de tener dirección propia |
| **RI-01** | **Se refuerza.** `/l/{token}` pasa de «la portada» a «la lectura entera», y es la única |
| **RF-POR-01, RF-POR-02** | **Vigentes, sin página propia.** Título y dedicatoria abren la vista **Leer**; la dedicatoria sigue sin ser el capítulo cero (regla de dominio 15) |
| **RF-POR-03** | **Modificado.** «Se entra al índice» decae —el índice deja de ser destino—; la ficha pasa a ser pestaña y **el PDF se conserva** |
| **RF-IND-01** | **Vigente como sumario**, no como página: la lista de los diez con su título abre la vista Leer y lleva a su fragmento |
| **RF-IND-02, RF-IND-03** | **Vigentes.** La marca de capítulos cambiados la sigue dando el backend y la sigue pintando el sumario |
| **RF-IND-04** | **Sustituido** por la posición guardada de T3. «Volver al índice lleva a donde lo dejó» pasa a «abrir el enlace lleva a donde lo dejó» |
| **RF-LEC-01, RF-LEC-02** | **Decaen.** En lectura continua no hay «anterior» ni «siguiente»: hay desplazamiento |
| **RF-LEC-03** | **Cambia de sujeto.** Ya no es «un número de capítulo que no existe» sino **un fragmento que no existe**, y sigue sin poder ser una pantalla en blanco |
| **RF-LEC-04, RF-LEC-05** | **Vigentes.** Marcar lo leído y leer la versión fijada no dependen de la forma de la URL |
| **RF-FIC-01 a RF-FIC-06** | **Vigentes**, en una pestaña en vez de una página. Son del plan 2 y esta fase solo les da contenedor |
| **CA-21** | **Decae** en su forma actual —«las cinco rutas responden»— y se sustituye por CA-21′ en T1 |

---

## Restricciones globales

| Restricción | Valor exacto | Origen |
| --- | --- | --- |
| **Una sola dirección** | `/l/{token}`. Ninguna vista añade ruta | D-06 |
| **El `token` es lo único que protege la lectura** | Sigue siendo el identificador no adivinable de `RF-PUB-07` | `RF-LEC-01`, D-06 |
| **`?vista=` se lee y no se escribe** | La aplicación **nunca** lo genera en sus propios `href`. Es superficie de inspección, no forma de compartir | T1, y su test |
| **Contraste AA gana sobre la estética** | `RF-ACC-04` | plan 1 · T4 |
| **Las tres fronteras las falla ESLint** | Sin cambios | plan 1 · T1 |
| **Los vetos no se enseñan nunca** | Ni con permiso del comprador | T5 |
| **La suite pasa sin backend levantado** | El doble de API sigue siendo el de T2 del plan 1 | `CA-15` |
| **Sin dependencias nuevas** | `content-visibility` es CSS; la posición es `localStorage`. Añadir una es pregunta de §3 punto 7 | `CLAUDE.md` §3 |

---

## Foco de revisión

Cinco cosas que la spec implica, que ninguna tarea probaría sola, y que le pasarían a una persona de verdad. Cada una tiene su test en la tarea que la posee.

1. **Alguien abre el enlace con un fragmento de otra versión.** `#capitulo-12` en una novela de diez: no puede quedarse en blanco ni saltar al principio sin decir nada. → T3.
2. **Alguien abre la novela en un teléfono con `localStorage` bloqueado.** Navegación privada, o ajustes estrictos: `localStorage` lanza en vez de devolver `null`, y la lectura entera se cae por la posición. → T3.
3. **Un teléfono abre dos novelas distintas.** Si la clave de posición no lleva el token, la segunda abre donde iba la primera. → T3.
4. **El comprador no contestó nada visible.** La vista de la entrevista se queda vacía, y una pantalla vacía se lee como un fallo. → T5.
5. **La novela tiene un capítulo, no diez.** El sumario, los fragmentos y la posición no pueden dar por hecho que son diez. → T2.

---

## Estructura de ficheros

| Fichero | De qué responde |
| --- | --- |
| `src/app/router.ts` | `RUTAS` reducido a una, y `VISTAS` con los tres valores de `?vista=` |
| `src/app/Aplicacion.tsx` | Una ruta, la página y el 404 |
| `src/features/manuscrito/components/Lectura.tsx` | La página: cabecera, pestañas y la vista activa |
| `src/features/manuscrito/components/Leer.tsx` | Dedicatoria, sumario y los diez capítulos encadenados |
| `src/features/manuscrito/hooks/usePosicion.ts` | Fragmento y posición guardada, con su precedencia |
| `src/features/manuscrito/components/Entrevista.tsx` | Lo que el comprador dejó visible |
| `src/backend/app/features/obra/…` | El campo por respuesta y el endpoint (toca la **001**) |

---

## Tarea 1 · Una ruta, tres vistas, y `?vista=` que solo se lee

Cierra **RI-01**, sustituye **CA-21** por **CA-21′** y cierra el coste 2 de D-06.

**Ficheros:**
- Modificar: `src/frontend/src/app/router.ts`, `src/frontend/src/app/Aplicacion.tsx`
- Crear: `src/frontend/src/features/manuscrito/components/Lectura.tsx`
- Test: `src/frontend/src/app/tests/rutas.test.tsx` (reescribe el de T3 del plan 1)

**Interfaces:**
- Produce: `RUTAS.lectura(t: string) => string` y `VISTAS = { leer, entrevista, quienEsQuien } as const`, que **consumen T2, T4 y T5**.
- Produce: `<Lectura />`, que consume `Pagina` y los primitivos del plan 1.

- [ ] **Paso 1: Escribir el test que falla**

```tsx
// src/frontend/src/app/tests/rutas.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Aplicacion } from "@/app/Aplicacion";
import { RUTAS, VISTAS } from "@/app/router";

function abrir(ruta: string) {
  window.history.pushState({}, "", ruta);
  return render(<Aplicacion />);
}

describe("una sola direccion", () => {
  it("la lectura es una ruta y ninguna vista anade otra", () => {
    expect(RUTAS.lectura("T")).toBe("/l/T");
    expect(Object.keys(RUTAS)).toEqual(["lectura"]);
  });

  it("las tres vistas se alcanzan sin cambiar de ruta", () => {
    for (const vista of Object.values(VISTAS)) {
      abrir(`/l/T?vista=${vista}`);
      expect(window.location.pathname).toBe("/l/T");
      expect(screen.getByRole("tab", { selected: true })).toHaveAccessibleName(
        new RegExp(vista.replace("-", " "), "i"),
      );
    }
  });

  it("sin `?vista=` se abre leyendo, que es para lo que se manda el enlace", () => {
    abrir(RUTAS.lectura("T"));
    expect(screen.getByRole("tab", { selected: true })).toHaveAccessibleName(/leer/i);
  });

  it("una vista inventada cae en leer y no en una pantalla vacia", () => {
    abrir("/l/T?vista=loquesea");
    expect(screen.getByRole("tab", { selected: true })).toHaveAccessibleName(/leer/i);
  });
});
```

- [ ] **Paso 2: Ejecutarlo y ver que falla**

Ejecutar: `pnpm test rutas`
Esperado: **FAIL** — `VISTAS` no existe.

- [ ] **Paso 3: Reducir el router**

```ts
// src/frontend/src/app/router.ts
export const RUTAS = {
  lectura: (t: string) => `/l/${t}`,
} as const;

export const PATRON_DE_LECTURA = "/l/:token";

/**
 * Los tres valores de `?vista=`. **Es superficie de inspección**
 * (`RF-VAL-08` de la 001), no forma de compartir: la aplicación los lee y
 * **nunca** los escribe en un `href`.
 */
export const VISTAS = {
  leer: "leer",
  entrevista: "entrevista",
  quienEsQuien: "quien-es-quien",
} as const;

export type Vista = (typeof VISTAS)[keyof typeof VISTAS];

export function vistaDe(busqueda: string): Vista {
  const pedida = new URLSearchParams(busqueda).get("vista");
  const conocida = Object.values(VISTAS).find((v) => v === pedida);
  return conocida ?? VISTAS.leer;
}
```

- [ ] **Paso 4: Ejecutar y ver que pasa**

Ejecutar: `pnpm test rutas` · Esperado: **PASS**.

- [ ] **Paso 5: El test que impide que `?vista=` se convierta en una ruta**

```tsx
it("la aplicacion no escribe `?vista=` en ningun enlace", () => {
  for (const vista of Object.values(VISTAS)) {
    const { container } = abrir(`/l/T?vista=${vista}`);
    const enlaces = [...container.querySelectorAll("a")].map((a) => a.getAttribute("href") ?? "");
    expect(enlaces.filter((h) => h.includes("vista="))).toEqual([]);
  }
});
```

Sin este test, `?vista=` **es una ruta con otro nombre**: en cuanto un enlace lo escriba, alguien lo comparte y vuelve el problema que D-06 quita.

- [ ] **Paso 6: Verde y commit**

```bash
git add src/frontend/src/app/router.ts src/frontend/src/app/Aplicacion.tsx \
        src/frontend/src/features/manuscrito/components/Lectura.tsx \
        src/frontend/src/app/tests/rutas.test.tsx
git commit -F <mensaje> -- <las mismas rutas>
```

---

## Tarea 2 · La novela entera, y que un móvil no sufra

Cierra **RF-POR-01**, **RF-POR-02**, **RF-IND-01**, **RF-IND-02**, **RF-IND-03**, **RF-LEC-05** y el coste 3 de D-06.

**Ficheros:**
- Crear: `src/frontend/src/features/manuscrito/components/Leer.tsx`
- Modificar: `src/frontend/src/app/estilos.css`
- Test: `src/frontend/src/features/manuscrito/components/Leer.test.tsx`

**Interfaces:**
- Consume: `useVersion(token)` y `useCapitulo(token, numero)` de la T2 del plan 1.
- Produce: `<Leer token={string} />`, y el `id` de cada capítulo —`capitulo-{numero}`— que **consume T3** para los fragmentos.

- [ ] **Paso 1: Escribir los tests que fallan**

```tsx
describe("la lectura continua", () => {
  it("abre con la dedicatoria, que no es el capitulo cero", () => {
    render(<Leer token="T" />, { wrapper: conDoble(dobleDeNovela({ dedicatoria: "Para Marta." })) });
    expect(screen.getByText("Para Marta.")).toBeInTheDocument();
    expect(screen.queryByText(/Cap[ií]tulo 0/)).toBeNull();
  });

  it("el sumario lleva al fragmento de cada capitulo, no a otra pagina", () => {
    render(<Leer token="T" />, { wrapper: conDoble(dobleDeNovela({ capitulos: 10 })) });
    const enlaces = screen.getAllByRole("link", { name: /Cap[ií]tulo/ });
    expect(enlaces).toHaveLength(10);
    expect(enlaces[3]).toHaveAttribute("href", "#capitulo-4");
  });

  it("marca los cambiados con el dato del backend, sin calcularlo", () => {
    render(<Leer token="T" />, { wrapper: conDoble(dobleDeNovela({ cambiados: [4, 7] })) });
    expect(screen.getByTestId("sumario-4")).toHaveAttribute("data-cambiado", "true");
    expect(screen.getByTestId("sumario-5")).toHaveAttribute("data-cambiado", "false");
  });

  it("una novela de un capitulo no se rompe", () => {
    // Foco de revisión 5: nada da por hecho que son diez.
    render(<Leer token="T" />, { wrapper: conDoble(dobleDeNovela({ capitulos: 1 })) });
    expect(screen.getAllByRole("link", { name: /Cap[ií]tulo/ })).toHaveLength(1);
  });

  it("cada capitulo declara su tamano para que la barra no baile", () => {
    const { container } = render(<Leer token="T" />, { wrapper: conDoble(dobleDeNovela({})) });
    const seccion = container.querySelector("#capitulo-1");
    expect(seccion).toHaveClass("capitulo");
  });
});
```

- [ ] **Paso 2: Ejecutarlo y ver que falla** · `pnpm test Leer` → **FAIL**, no existe `Leer`.

- [ ] **Paso 3: El CSS que hace barata la página larga**

```css
/* src/frontend/src/app/estilos.css */

/**
 * Doce mil palabras en una sola página.
 *
 * `content-visibility: auto` deja que el navegador **salte el renderizado** de
 * lo que no se ve, y `contain-intrinsic-size` le da un tamaño estimado para que
 * la barra de desplazamiento no dé saltos mientras se pinta.
 *
 * **No se virtualiza, y el motivo no es la dependencia: es Ctrl+F.** Una lista
 * virtualizada solo tiene montado lo visible, así que buscar «el verano» en la
 * novela encuentra lo que hay en pantalla y nada más. En un libro, buscar una
 * frase es una función que el lector espera.
 */
.capitulo {
  content-visibility: auto;
  contain-intrinsic-size: auto 1200px;
  margin-block-start: 3rem;
  /* El fragmento lleva aquí, y el título no puede quedar pegado al borde
     superior ni tapado por nada fijo. */
  scroll-margin-block-start: 1.5rem;
}
```

- [ ] **Paso 4: Implementar `Leer`** con la dedicatoria, el sumario y los capítulos en `<section id="capitulo-N" class="capitulo">`.

- [ ] **Paso 5: Verde** · `pnpm test Leer` → **PASS**.

- [ ] **Paso 6: Commit.**

---

## Tarea 3 · Dónde estabas y dónde te mandaron

Cierra **RF-IND-04** en su forma nueva, **RF-LEC-03** en su forma nueva y el coste 1 de D-06.

**Ficheros:**
- Crear: `src/frontend/src/features/manuscrito/hooks/usePosicion.ts`
- Test: `src/frontend/src/features/manuscrito/hooks/usePosicion.test.ts`

**Interfaces:**
- Produce: `usePosicion(token: string, capitulos: number[])`, que devuelve `{ inicial: number | null, recordar(numero: number): void }`.

- [ ] **Paso 1: Escribir los tests que fallan**

```ts
describe("la posicion de lectura", () => {
  it("si la URL trae fragmento, manda el fragmento", () => {
    // Alguien te mandó ese punto adrede: llevarte a otro sitio seria ignorarle.
    localStorage.setItem("posicion:T", "3");
    window.history.pushState({}, "", "/l/T#capitulo-7");
    const { result } = renderHook(() => usePosicion("T", [1, 2, 3, 4, 5, 6, 7]));
    expect(result.current.inicial).toBe(7);
  });

  it("sin fragmento, se vuelve donde lo dejaste", () => {
    localStorage.setItem("posicion:T", "3");
    window.history.pushState({}, "", "/l/T");
    const { result } = renderHook(() => usePosicion("T", [1, 2, 3]));
    expect(result.current.inicial).toBe(3);
  });

  it("un fragmento de una novela mas larga no deja la pagina en blanco", () => {
    // Foco de revisión 1.
    window.history.pushState({}, "", "/l/T#capitulo-12");
    const { result } = renderHook(() => usePosicion("T", [1, 2, 3]));
    expect(result.current.inicial).toBeNull();
  });

  it("dos novelas en el mismo telefono no se pisan", () => {
    // Foco de revisión 3.
    localStorage.setItem("posicion:T", "3");
    const { result } = renderHook(() => usePosicion("OTRA", [1, 2, 3]));
    expect(result.current.inicial).toBeNull();
  });

  it("con `localStorage` bloqueado se lee igual", () => {
    // Foco de revisión 2: en navegación privada, `localStorage` **lanza**.
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("denied");
    });
    const { result } = renderHook(() => usePosicion("T", [1, 2, 3]));
    expect(result.current.inicial).toBeNull();
    expect(() => result.current.recordar(2)).not.toThrow();
  });

  it("recordar no apila historial: el boton atras sale de la novela", () => {
    window.history.pushState({}, "", "/l/T");
    const largo = window.history.length;
    const { result } = renderHook(() => usePosicion("T", [1, 2, 3]));
    act(() => result.current.recordar(2));
    expect(window.history.length).toBe(largo);
    expect(window.location.hash).toBe("#capitulo-2");
  });
});
```

- [ ] **Paso 2: Ejecutarlo y ver que falla** · `pnpm test usePosicion` → **FAIL**.

- [ ] **Paso 3: Implementar**, con las tres reglas: `replaceState` y nunca `pushState`; clave `posicion:{token}`; y todo acceso a `localStorage` dentro de `try/catch`.

- [ ] **Paso 4: Verde. Paso 5: Commit.**

---

## Tarea 4 · Quién es quién, como pestaña

Cierra **RF-POR-03** en su forma nueva. **No reimplementa la ficha**: le da contenedor.

**Ficheros:**
- Modificar: `src/frontend/src/features/manuscrito/components/Lectura.tsx`
- Test: junto a él.

**Interfaces:** consume lo que el plan 2 produce. **Si el plan 2 aún no está, esta tarea monta la pestaña con su estado vacío** y el plan 2 la llena.

- [ ] **Paso 1: El test**

```tsx
it("la ficha vive en una pestana y no en una direccion", () => {
  abrir("/l/T?vista=quien-es-quien");
  expect(window.location.pathname).toBe("/l/T");
  expect(screen.getByRole("tabpanel")).toHaveAccessibleName(/qui[eé]n es qui[eé]n/i);
});

it("el PDF se sigue pudiendo descargar", () => {
  // RF-POR-03 conserva esta mitad aunque el indice deje de ser destino.
  abrir("/l/T");
  expect(screen.getByRole("link", { name: /descargar/i })).toHaveAttribute(
    "href",
    expect.stringContaining("/pdf"),
  );
});
```

- [ ] **Pasos 2-5:** rojo, implementar, verde, commit.

---

## Tarea 5 · La entrevista, y lo que no se enseña

Alcance **nuevo**. Toca la **001**: campo y endpoint.

**Ficheros:**
- Modificar (backend, spec 001): el esquema del brief — un campo por respuesta — y una ruta de lectura
- Crear (frontend): `src/frontend/src/features/manuscrito/components/Entrevista.tsx`
- Test: en los dos lados

**La decisión, escrita donde se lee:** el brief lo escribió **otra persona, sobre el destinatario, para una máquina**. Enseñárselo entero no es obviamente lo que el comprador quería, y **los vetos son lo peor que se puede enseñar**: «no menciones la enfermedad de su padre», leído por el hijo, es peor que el silencio que compraba, porque ahí aparece como instrucción.

**Y el fallo es asimétrico: enseñar de más no se deshace.** Quien ve poco pregunta; quien vio lo que no debía, ya lo vio.

Por eso:

1. **Por defecto no se enseña nada del brief.** Se enseña la dedicatoria y los elementos obligatorios que el comprador pidió **y aparecen** — que el destinatario va a leer igualmente.
2. **Lo demás lo elige el comprador**, respuesta a respuesta, al cerrar la entrevista. Es un **campo**, no una heurística.
3. **Los vetos no se enseñan nunca**, ni con permiso.

**Aflojarlo es cambiar un defecto, no rehacer la vista:** el campo es `visible_para_destinatario: bool = False` por respuesta. Si `maujimenez4` prefiere lo contrario, se cambia el valor por defecto y la vista no se toca. Lo que **no** cambia con un defecto es la regla 3: los vetos se filtran en el servidor y no viajan.

- [ ] **Paso 1: El test del backend que falla**

```python
async def test_la_entrevista_publicada_no_lleva_los_vetos(cliente, obra_con_entrevista):
    cuerpo = cliente.get(f"/lectura/{obra_con_entrevista.token}/entrevista").json()
    texto = json.dumps(cuerpo, ensure_ascii=False).lower()
    assert "no menciones" not in texto
    assert all(v.lower() not in texto for v in obra_con_entrevista.vetos)


async def test_por_defecto_no_se_publica_ninguna_respuesta(cliente, obra_con_entrevista):
    cuerpo = cliente.get(f"/lectura/{obra_con_entrevista.token}/entrevista").json()
    assert cuerpo["respuestas"] == []


async def test_lo_que_el_comprador_marco_visible_si_sale(cliente, obra_con_entrevista):
    await marcar_visible(obra_con_entrevista, pregunta="un recuerdo", visible=True)
    cuerpo = cliente.get(f"/lectura/{obra_con_entrevista.token}/entrevista").json()
    assert [r["pregunta"] for r in cuerpo["respuestas"]] == ["un recuerdo"]
```

- [ ] **Paso 2: Verlo fallar. Paso 3: el campo y el endpoint.** El filtrado va **en el servidor**: lo no visible no se envía, por el mismo motivo que `RF-FIC-04` — un `display:none` es un spoiler a un «inspeccionar elemento» de distancia.

- [ ] **Paso 4: El test del frontend**

```tsx
it("una entrevista sin nada visible no parece un fallo", () => {
  // Foco de revisión 4.
  abrir("/l/T?vista=entrevista");
  expect(screen.getByRole("tabpanel")).toHaveTextContent(
    /esta novela se escribió a partir de lo que .* contó/i,
  );
});
```

- [ ] **Pasos 5-6: verde y commit.**

---

## Lo que esta fase deja cerrado

| Criterio | Qué demuestra |
| --- | --- |
| **CA-21′** | Una sola ruta; las tres vistas se alcanzan sin cambiarla, y `?vista=` no aparece en ningún `href` |
| **CA-2** | La dedicatoria abre la lectura y no es el capítulo cero |
| **CA-3** | Los diez capítulos, con su marca de cambiados |
| Foco 1 a 5 | Fragmento imposible, `localStorage` bloqueado, dos novelas, entrevista vacía, novela de un capítulo |

## Lo que NO hace

- **No implementa la ficha**: es el plan 2. Aquí solo tiene pestaña.
- **No toca las fronteras, los tokens ni los primitivos.** Siguen siendo los del plan 1.
- **No resuelve la petición de cambio.** Sigue siendo de su fase.
- **No decide la tarifa de nada ni toca el backend más allá del campo y el endpoint de T5.**

---

## Desviaciones

*Se anotan **antes** de seguir, no después (`CLAUDE.md` §3.4).*

| Fecha | Paso | Qué se desvió y por qué |
| --- | --- | --- |
| — | — | — |
