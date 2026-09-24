"""La dedicatoria, de la entrevista a la tabla.

Es lo unico del producto que escribe una persona y no el modelo, y por eso no
se parece a nada mas del sistema: no es prosa generada, no es una
`VersionDeTexto`, no tiene `run_id` y nadie la valida contra el canon.

**Por que este fichero existe y no basta con el de T1.** `test_esquema.py`
comprueba que la tabla tiene la forma correcta; esto comprueba que **algo la
llena**. Con cero dedicatorias en el sistema, el criterio CA-30 -que la
dedicatoria no aparezca en el manuscrito ensamblado- se cumple por vacio: no
aparece porque no hay ninguna. Es la tercera vez en este proyecto que un
criterio pasa asi, segun la Fase 4 del plan, y las tres veces el arreglo fue el
mismo: **afirmar tambien que hay algo que mirar**.

RD-05, R-6 y la regla de dominio 15.
"""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.manuscrito import dedicatoria_de

COMPLETO: dict[str, Any] = {
    "nombre": "Marta",
    "edad": 34,
    "genero": "romance",
    "tono": "luminoso",
    "nivel_de_calor": 1,
    "elementos_obligatorios": ["el faro"],
}


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    """El doble elige por subcadena del prompt, y el prompt lleva al final el
    `repr` de las respuestas del comprador. Se distingue por el `tono`, que es
    propio de este modulo y no aparece en la plantilla del Entrevistador."""
    return {"luminoso": json.dumps({"faltantes": [], "contradicciones": []})}


def _cerrar_entrevista_con(cliente: TestClient, **extra: Any) -> int:
    """Abre, responde y cierra una entrevista. Devuelve el `obra_id`.

    `extra` son los campos que cada test quiere anadir a las respuestas -aqui,
    la dedicatoria-. Lo demas es el brief minimo que el Entrevistador acepta.
    """
    entrevista_id = cliente.post("/entrevistas").json()["id"]
    cliente.post(
        f"/entrevistas/{entrevista_id}/respuestas",
        json={"respuestas": COMPLETO | extra, "texto_aportado": ""},
    )
    cierre = cliente.post(f"/entrevistas/{entrevista_id}/cerrar")
    assert cierre.status_code == 201, cierre.text
    return int(cierre.json()["obra_id"])


async def test_la_entrevista_recoge_la_dedicatoria(
    cliente: TestClient, sesion: AsyncSession
) -> None:
    """Es lo unico del producto que escribe una persona y no el modelo."""
    obra_id = _cerrar_entrevista_con(cliente, dedicatoria="Para Marta, que nunca se rinde.")

    guardada = await dedicatoria_de(sesion, obra_id)

    assert guardada is not None, "la entrevista no guardo ninguna dedicatoria"
    assert guardada.texto == "Para Marta, que nunca se rinde."


@pytest.mark.parametrize("vacia", [None, "", "   "])
async def test_sin_dedicatoria_la_obra_se_crea_igual(
    cliente: TestClient, sesion: AsyncSession, vacia: str | None
) -> None:
    """R-6: es opcional. Un regalo sin dedicatoria sigue siendo un regalo.

    Y los tres vacios se tratan igual: no se guarda una fila con espacios, que
    luego la portada tendria que distinguir de una dedicatoria de verdad.
    """
    obra_id = _cerrar_entrevista_con(cliente, dedicatoria=vacia)

    assert await dedicatoria_de(sesion, obra_id) is None


async def test_la_dedicatoria_no_es_una_version_de_texto(
    cliente: TestClient, sesion: AsyncSession
) -> None:
    """RD-05. No tiene `run_id`, ni ordinal, ni pasa por puerta de calidad.

    Se comprueba por la forma de lo guardado: si algun dia alguien la modela
    como prosa, este test cae antes de que llegue al ensamblado.
    """
    obra_id = _cerrar_entrevista_con(cliente, dedicatoria="Para Marta.")

    guardada = await dedicatoria_de(sesion, obra_id)

    assert guardada is not None
    for campo_de_prosa in ("run_id", "version_texto_id", "ordinal", "capitulo_id"):
        assert not hasattr(guardada, campo_de_prosa), (
            f"la dedicatoria tiene `{campo_de_prosa}`: se esta modelando como prosa"
        )
