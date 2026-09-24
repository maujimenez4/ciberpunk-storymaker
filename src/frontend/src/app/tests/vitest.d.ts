/**
 * Los matchers de `vitest-axe` no traen tipos para `expect.extend`: sin esto,
 * `toHaveNoViolations` existe en tiempo de ejecucion y no para `tsc`.
 *
 * Las dos interfaces amplian las de `vitest` y por eso **no declaran miembros
 * propios**; la regla que lo prohibe se apaga aqui y solo aqui, que es el unico
 * sitio donde una interfaz vacia significa algo.
 */
import "vitest";

interface MatchersDeAxe<R = unknown> {
  toHaveNoViolations(): R;
}

declare module "vitest" {
  /* eslint-disable @typescript-eslint/no-empty-object-type */
  interface Assertion<T = unknown> extends MatchersDeAxe<T> {}
  interface AsymmetricMatchersContaining extends MatchersDeAxe {}
  /* eslint-enable @typescript-eslint/no-empty-object-type */
}
