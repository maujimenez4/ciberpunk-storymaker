"""Los briefs de `ejemplos/` **validan de verdad** contra `BriefEntrada`.

**Por que existe este fichero.** El brief de ejemplo del `README.md` llevaba
desde que se escribio poniendo `nombre`, `edad`, `rasgos` y
`recuerdos_aportados` **al nivel de arriba**, cuando `BriefEntrada` los quiere
dentro de `destinatario`. Nadie lo noto porque **nada lo ejecutaba**: era un
bloque de codigo en un documento, y un bloque de codigo en un documento no
falla nunca.

Lo que se arregla aqui **no es el JSON**: es que vuelva a poder pasar. Los
ejemplos salen del documento a `ejemplos/`, que es un directorio con ficheros
de verdad, y este test los carga todos. El dia que `BriefEntrada` gane un campo
obligatorio, el ejemplo se pone rojo en la misma suite que el codigo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.features.obra.schemas import BriefEntrada

EJEMPLOS = Path(__file__).resolve().parents[6] / "ejemplos"


def _briefs() -> list[Path]:
    return sorted(EJEMPLOS.glob("brief-*.json"))


def test_hay_ejemplos_que_mirar() -> None:
    """Sin esto, el test de abajo pasa el dia que el directorio se renombre o
    se vacie, y nadie se entera de que ha dejado de comprobar nada.

    Es la misma salvaguarda que `len(manuscrito) > 0` en el test de la
    dedicatoria y que `test_el_grafo_tiene_aristas_que_mirar` en el de ciclos:
    afirmar tambien que **hay algo que mirar**.
    """
    assert EJEMPLOS.is_dir(), f"no existe {EJEMPLOS}"
    assert _briefs(), f"ningun brief-*.json en {EJEMPLOS}"


@pytest.mark.parametrize("ruta", _briefs(), ids=lambda r: r.name)
def test_el_ejemplo_valida_contra_el_esquema_de_verdad(ruta: Path) -> None:
    """No se comprueba «tiene los campos»: se **construye el modelo**.

    Los tres validadores de `BriefEntrada` -contenido adulto con menores, la
    edad contra la fecha de nacimiento, y ningun veto chocando con el nombre
    del destinatario- solo corren al construirlo. Un ejemplo que pasara un
    chequeo de forma y fallara uno de esos tres seria peor que el roto de
    antes, porque parece bueno.
    """
    BriefEntrada.model_validate(json.loads(ruta.read_text(encoding="utf-8")))
