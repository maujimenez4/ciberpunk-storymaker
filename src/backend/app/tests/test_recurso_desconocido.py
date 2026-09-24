"""Pedir algo que no existe responde 404, y no 409.

El manejador central bajaba a 404 **una** excepcion concreta, por `isinstance`
sobre su clase. Cada feature que anadia la suya —`ObraDesconocida` en la ola 2,
`CapituloDesconocido` en la ola 3— respondia 409, que significa «el estado
actual no admite esta peticion» y no «esto no existe».

Y no se podia arreglar dentro de una tarea: el manejador vive en `commons/`,
que por el primer contrato de `import-linter` **no puede importar de ninguna
feature**. Hacia falta invertir la dependencia -- `commons` declara el concepto,
las features lo heredan --, y eso es trabajo de integrador.
"""

import pytest

from app.commons.domain.errores import (
    ErrorDeDominio,
    RecursoDesconocido,
)
from app.commons.errors.manejador import _codigo
from app.features.contexto import CapituloDesconocido
from app.features.outline import ObraDesconocida


@pytest.mark.parametrize(
    "error",
    [
        ObraDesconocida(7),
        CapituloDesconocido(7),
    ],
)
def test_lo_que_no_existe_responde_404(error: ErrorDeDominio):
    assert _codigo(error) == 404


@pytest.mark.parametrize("clase", [ObraDesconocida, CapituloDesconocido])
def test_cada_una_declara_que_es_un_recurso_que_no_existe(clase: type) -> None:
    """La marca es la que hace el mapeo, no el nombre de la clase.

    Sin heredar de `RecursoDesconocido` una feature nueva volveria al 409 en
    silencio, que es exactamente lo que paso dos veces.
    """
    assert issubclass(clase, RecursoDesconocido)


def test_un_error_de_dominio_cualquiera_no_baja_a_404():
    """Contraste: si todo fuera 404, el test de arriba no comprobaria nada."""

    class Cualquiera(ErrorDeDominio):
        pass

    assert _codigo(Cualquiera()) != 404
