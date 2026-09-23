"""Excepciones de dominio.

Ningun servicio lanza HTTPException (RI-11, architecture.md §5.2 regla 4): lanza
una de estas y el handler central de `manejadores.py` la traduce. La razon es que
un servicio que conoce codigos HTTP no se puede reutilizar fuera de una peticion
—en un trabajo en segundo plano, por ejemplo—, que es justo donde corre el ciclo
de una escena.
"""

from typing import Any


class ErrorDeDominio(Exception):
    """Raiz de todo lo que el handler central sabe traducir."""

    def datos(self) -> dict[str, Any]:
        """Lo que hace accionable el fallo, mas alla del codigo HTTP."""
        return {}


class ContextBudgetExceeded(ErrorDeDominio):
    """El paquete no cabe ni tras recortar (RF-CTX-05).

    Es fallo de diseno del ensamblado, no de ejecucion: se lanza **antes** de
    llamar al modelo, asi que no hay coste asociado.
    """

    def __init__(self, capa: str, tokens: int, tope: int) -> None:
        super().__init__(f"la capa {capa} necesita {tokens} tokens y su tope es {tope}")
        self.capa = capa
        self.tokens = tokens
        self.tope = tope

    def datos(self) -> dict[str, Any]:
        return {"capa": self.capa, "tokens": self.tokens, "tope": self.tope}


class TiempoAgotado(ErrorDeDominio):
    """Un paso supera su plazo, o vence la espera de turno (§2.2, §3.6)."""

    def __init__(self, paso: str, relanzable_sin_coste: bool) -> None:
        super().__init__(f"el paso {paso} agoto su plazo")
        self.paso = paso
        self.relanzable_sin_coste = relanzable_sin_coste

    def datos(self) -> dict[str, Any]:
        return {
            "paso": self.paso,
            "relanzable_sin_coste": self.relanzable_sin_coste,
        }


class ReglaDeDominioViolada(ErrorDeDominio):
    """Un axioma de definitions.md §11 no se cumple."""

    def __init__(self, axioma: int, detalle: str) -> None:
        super().__init__(f"axioma {axioma}: {detalle}")
        self.axioma = axioma
        self.detalle = detalle

    def datos(self) -> dict[str, Any]:
        return {"axioma": self.axioma, "detalle": self.detalle}


class RecursoNoEncontrado(ErrorDeDominio):
    """El identificador no corresponde a nada."""

    def __init__(self, recurso: str, identificador: str) -> None:
        super().__init__(f"no existe {recurso} {identificador}")
        self.recurso = recurso
        self.identificador = identificador

    def datos(self) -> dict[str, Any]:
        return {"recurso": self.recurso, "identificador": self.identificador}


class FalloDeProveedor(ErrorDeDominio):
    """El proveedor falla tras agotar los reintentos (RNF-FIA-02)."""

    def __init__(self, intentos: int) -> None:
        super().__init__(f"el proveedor fallo tras {intentos} intentos")
        self.intentos = intentos

    def datos(self) -> dict[str, Any]:
        return {"intentos": self.intentos}


class EntradaFueraDeDominio(ErrorDeDominio):
    """A un validador mecanico le entra algo que no sabe evaluar (RF-CAL-13).

    **Existe para que los guardarrailes fallen cerrados.** `validar_nivel_de_calor`
    devolvia lista vacia ante un `nivel_de_calor` que no estaba en la escala, y
    lista vacia significa «no he encontrado nada malo»: una errata en el nivel
    declarado apagaba entero el validador de la regla 5 de §8 sin hacer ruido.
    Un validador que no puede evaluar tiene que decirlo, no callar.
    """

    def __init__(self, parametro: str, valor: str, esperado: str) -> None:
        super().__init__(
            f"{parametro}={valor!r} no pertenece al dominio del validador: "
            f"se esperaba {esperado}"
        )
        self.parametro = parametro
        self.valor = valor
        self.esperado = esperado

    def datos(self) -> dict[str, Any]:
        return {
            "parametro": self.parametro,
            "valor": self.valor,
            "esperado": self.esperado,
        }
