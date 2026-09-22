"""P-08: el contador de tokens es local y no estima por caracteres.

RNF-TOK-02 y D-07. Las tres propiedades que se comprueban son las tres que
hacen util a un contador en este sistema: que cuente de verdad, que no necesite
red en cada llamada, y que se pueda sustituir por un doble en pruebas.
"""

import socket

import pytest

from app.commons.llm import ContadorBPE, ContadorDeTokens


@pytest.fixture(scope="module")
def contador() -> ContadorBPE:
    c = ContadorBPE()
    c.contar("calienta el vocabulario")
    return c


def test_no_estima_por_caracteres(contador: ContadorBPE) -> None:
    """Dos textos donde el recuento por caracteres da la respuesta contraria.

    `repetido` tiene el doble de caracteres que `denso` y bastantes menos
    tokens. Cualquier estimacion proporcional a la longitud los ordena al reves,
    y por eso este par distingue un contador de una regla de tres.
    """
    repetido = "a" * 400
    denso = "函数式编程，测试！" * 22

    assert len(repetido) > len(denso)
    assert contador.contar(repetido) < contador.contar(denso)


def test_contar_no_usa_la_red(
    contador: ContadorBPE, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-07: local. Si contar necesitara red, el ensamblado no cumpliria
    RNF-REN-01 y ademas fallaria sin conexion."""

    def prohibido(*_: object, **__: object) -> None:
        raise AssertionError("el contador intento abrir un socket")

    monkeypatch.setattr(socket, "socket", prohibido)
    assert contador.contar("una escena cualquiera") > 0


def test_el_contador_se_inyecta(contador: ContadorBPE) -> None:
    """RNF-TOK-02 y RI-13: es una dependencia, no una funcion global."""

    class ContadorDeDoble:
        def contar(self, texto: str) -> int:
            return len(texto.split())

    doble: ContadorDeTokens = ContadorDeDoble()
    real: ContadorDeTokens = contador
    assert doble.contar("una escena cualquiera") == 3
    assert real.contar("una escena cualquiera") > 0


def test_el_vacio_cuesta_cero(contador: ContadorBPE) -> None:
    assert contador.contar("") == 0
