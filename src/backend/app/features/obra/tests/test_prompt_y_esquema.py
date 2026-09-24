"""El prompt del Entrevistador y `BriefEntrada` no pueden separarse.

**El bloqueo de la primera corrida real, fijado. 2026-09-24.**

`entrevistador.v1.md` pedia como obligatorios de la obra «genero, tono y
**extension**», y `BriefEntrada` no tiene `extension`. El modelo hacia
exactamente lo que se le pedia: sobre el brief de ejemplo -- que valida contra
el esquema -- devolvia `faltantes: ["extension"]`, y cerrar la entrevista daba
409. **La obra no se podia crear**, y el comprador se quedaba mirando un
formulario que le pedia algo que nadie iba a usar.

**Con dobles no se ve.** El doble devuelve lo que el test le pone, asi que el
prompt podia pedir cualquier cosa sin que nada se pusiera rojo. Solo aparece al
conectar el agente con el proveedor de verdad.

Estos tests no comprueban el texto del prompt -- eso se reescribe cada version --
sino la **correspondencia**: que no nombre un obligatorio que el esquema no
tiene, y que no se olvide de uno que si.
"""

import re

from app.features.obra.agents import PLANTILLA_V1
from app.features.obra.schemas import BriefEntrada, DestinatarioEntrada

# `nombre` y `edad` viven en `DestinatarioEntrada`, que el brief anida.
CAMPOS_DEL_DESTINATARIO = {
    nombre for nombre, campo in DestinatarioEntrada.model_fields.items() if campo.is_required()
}
CAMPOS_DE_LA_OBRA = {
    nombre for nombre, campo in BriefEntrada.model_fields.items() if campo.is_required()
} - {"destinatario"}

OBLIGATORIOS = CAMPOS_DEL_DESTINATARIO | CAMPOS_DE_LA_OBRA

# Donde termina lo obligatorio y empieza lo que el prompt prohibe pedir. Esa
# parte nombra campos **a proposito**, para vetarlos, y contarlos como
# obligatorios haria fallar el test por decir bien lo que hay que decir.
CORTES = ("**No pidas", "Son opcionales")


def _bloque_de_faltantes() -> str:
    """El trozo del prompt que enumera lo obligatorio, y solo ese."""
    partido = re.split(r"\*\*Qu[eé] falta:\*\*", PLANTILLA_V1)
    assert len(partido) == 2, "el prompt ya no tiene un bloque «Que falta»"

    bloque = re.split(r"\n- \*\*", partido[1])[0]
    for corte in CORTES:
        bloque = bloque.split(corte)[0]
    return bloque


def _campos_citados() -> set[str]:
    """Los identificadores entre comillas invertidas del bloque obligatorio."""
    return set(re.findall(r"`([a-z_]+)`", _bloque_de_faltantes()))


def test_el_prompt_no_pide_campos_que_el_esquema_no_tiene() -> None:
    """Un obligatorio inventado **detiene la creacion de la obra**."""
    inventados = _campos_citados() - OBLIGATORIOS - {"faltantes"}

    assert not inventados, (
        f"el prompt pide como obligatorio lo que `BriefEntrada` no tiene: "
        f"{sorted(inventados)}. Un dato de mas en `faltantes` da 409 al cerrar."
    )


def test_el_prompt_nombra_todos_los_obligatorios_del_esquema() -> None:
    """El fallo simetrico, que seria peor porque es silencioso.

    Un obligatorio que el prompt no nombra no llega a `faltantes`: el agente da
    la entrevista por completa, el esquema la rechaza despues y el comprador
    recibe un error que el Entrevistador podia haberle evitado.
    """
    olvidados = OBLIGATORIOS - _campos_citados()

    assert not olvidados, (
        f"el esquema exige campos que el prompt no nombra: {sorted(olvidados)}. "
        f"El agente dara por completa una entrevista que el esquema rechazara."
    )


def test_extension_no_vuelve_a_la_lista_de_obligatorios() -> None:
    """El caso concreto que costo la corrida, por su nombre.

    Se comprueba sobre los **campos citados** y no sobre el texto: el prompt
    menciona «extension» a proposito para prohibirla, y buscarla en la prosa
    daria falso positivo justo cuando el aviso esta bien escrito.
    """
    citados = {campo.replace("ó", "o") for campo in _campos_citados()}

    assert "extension" not in citados
