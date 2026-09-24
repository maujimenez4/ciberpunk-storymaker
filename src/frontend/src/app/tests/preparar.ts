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
