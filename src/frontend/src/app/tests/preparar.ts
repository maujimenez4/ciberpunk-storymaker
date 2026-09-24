import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, expect } from "vitest";
import * as matchers from "vitest-axe/matchers";

expect.extend(matchers);

/**
 * Sin `globals: true`, Testing Library **no desmonta sola** entre tests: el
 * segundo `render` se suma al primero en el mismo documento y cualquier
 * `getByRole` encuentra dos. Se limpia aquí, una vez, en vez de en cada suite.
 */
afterEach(cleanup);

/**
 * La novela en curso se apunta en `localStorage`, y jsdom lo comparte entre
 * los tests de un fichero: sin esto, el que deja una obra apuntada hace que el
 * siguiente arranque reanudándola en vez de en la entrevista.
 */
afterEach(() => {
  window.localStorage.clear();
});
