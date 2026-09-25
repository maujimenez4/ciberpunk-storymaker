"""El Escritor: el unico rol que escribe prosa, y el unico que no ve la base.

Lo que se comprueba aqui no es que la prosa sea buena -- eso lo juzga G1b, que
no existe todavia -- sino las tres cosas que hacen **atribuible** un defecto:

1. **Solo ve el paquete** (RF-ESC-01). Se comprueba por analisis del arbol de
   sintaxis *y* con la sesion cortada: si tocara la base, fallaria.
2. **El reintento lleva el defecto concreto con su cita** (RF-ESC-03). Nunca un
   reintento generico, que `CLAUDE.md` §15 prohibe con esas palabras.
3. **Las restricciones duras salen dos veces**, al principio y al final
   (`CLAUDE.md` §10).

Ninguna prueba llama al proveedor (CA-4): el cliente es `DobleDeterminista`.
"""

import ast
from pathlib import Path

import pytest

from app.commons.llm.doble import DobleDeterminista
from app.features.escena import RestriccionesDeDiscurso
from app.features.escritura.agents import (
    HASH_DE_PLANTILLA_V2,
    MARCA_DE_PLANTILLA,
    MARCA_DE_REPARACION,
    PLANTILLA_V2,
    PROMPT_ID,
    PROMPT_VERSION,
    Escritor,
    ProsaVacia,
    Reparacion,
    render_escritor,
)

RESTRICCIONES = RestriccionesDeDiscurso(
    persona="3ª limitada", tiempo_verbal="pasado", nivel_de_calor=2
)

PROSA = "Nadia cerro la puerta del invernadero y miro el suelo mojado."

DEFECTO = Reparacion(
    codigo="VOZ-03",
    cita="miro el suelo",
    desplazamiento_inicio=38,
    desplazamiento_fin=51,
)


def _escritor(prosa: str = PROSA, semilla: int = 0) -> Escritor:
    return Escritor(DobleDeterminista({MARCA_DE_PLANTILLA: prosa}), semilla=semilla)


# ---------------------------------------------------------------------------
# RF-ESC-01 · solo el paquete
# ---------------------------------------------------------------------------


async def test_el_escritor_escribe_con_la_sesion_cortada(paquete, sesion, motor):
    """RF-ESC-01, y es el test que el plan pide con esas palabras.

    Se le pasa el paquete y **se le corta la sesion**: se cierra la sesion y se
    desmonta el motor antes de llamar. Si el Escritor tocara la base, aqui
    reventaria. De esto sale que un defecto sea atribuible: si le falta un dato,
    el fallo es del ensamblado (`CLAUDE.md` §9.1).
    """
    await sesion.close()
    await motor.dispose()

    texto = await _escritor().escribir(paquete, RESTRICCIONES)

    assert texto == PROSA


PROHIBIDOS_PARA_EL_ESCRITOR = (
    "sqlalchemy",
    "aiosqlite",
    "app.commons.db",
    "app.features.escritura.modelos",
    "app.features.escritura.service",
)
"""Lo que el Escritor no puede nombrar, y por que cada uno.

Los tres primeros son la base de datos. Los dos ultimos son **de su propia
feature**, que es donde §5.1 no lo impediria: `modelos.py` son las tablas y
`service.py` es quien las escribe, y un Escritor que importara cualquiera de los
dos tendria como llegar a ellas sin cruzar ninguna frontera.

**Lo que este analisis no compra**, y se dice para que nadie lo dé por mas de lo
que es: `agents.py` importa `Paquete` de `contexto` y `Defecto` de `calidad`, y
esas features si conocen SQLAlchemy por dentro. Lo que se afirma es que el
Escritor **no nombra ningun almacen**; que no lo **use** lo sostiene el test de
la sesion cortada, y que no pueda tenerlo, el que no recibe sesion por firma.
"""


def _modulos_importados(fichero: Path) -> list[str]:
    arbol = ast.parse(fichero.read_text(encoding="utf-8"), str(fichero))
    modulos: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.append(nodo.module)
        elif isinstance(nodo, ast.Import):
            modulos.extend(alias.name for alias in nodo.names)
    return modulos


def test_el_modulo_del_escritor_no_nombra_ningun_almacen():
    """RF-ESC-01 por **analisis**, que es como la spec lo verifica.

    El test anterior demuestra que no toca la base en esa llamada; este
    demuestra que no tiene con que nombrarla. Sin el, bastaria con que el camino
    feliz no consultara nada para que la restriccion pareciera cumplida.
    """
    fichero = Path(__file__).resolve().parents[1] / "agents.py"

    prohibidos = [
        m for m in _modulos_importados(fichero) if m.startswith(PROHIBIDOS_PARA_EL_ESCRITOR)
    ]
    assert not prohibidos, f"El Escritor no puede nombrar un almacen: {prohibidos}"


def test_el_analisis_anterior_sabe_reconocer_una_infraccion(tmp_path):
    """Contraste: sin esto, un modulo sin imports lo dejaria verde por vacio."""
    impostor = tmp_path / "agents.py"
    impostor.write_text(
        "from sqlalchemy.ext.asyncio import AsyncSession\n"
        "from app.features.escritura.modelos import VersionTexto\n",
        encoding="utf-8",
    )

    prohibidos = [
        m for m in _modulos_importados(impostor) if m.startswith(PROHIBIDOS_PARA_EL_ESCRITOR)
    ]
    assert len(prohibidos) == 2


# ---------------------------------------------------------------------------
# `CLAUDE.md` §10 · la plantilla
# ---------------------------------------------------------------------------


def test_la_plantilla_repite_las_restricciones_duras_al_principio_y_al_final():
    """`CLAUDE.md` §10: el centro del prompt es donde mas informacion se pierde.

    Se cuenta sobre el prompt **renderizado** y no sobre la plantilla: lo que el
    modelo lee son los valores, y un marcador repetido que se sustituyera una
    sola vez dejaria la restriccion dicha una vez.
    """
    prompt = render_escritor(PLANTILLA_V2, "el paquete", RESTRICCIONES)
    mitad = len(prompt) // 2

    duras = (
        "**Persona:** 3ª limitada",
        "**Tiempo verbal:** pasado",
        "**Nivel de calor:** 2",
    )
    for duro in duras:
        assert duro in prompt[:mitad], f"{duro!r} no aparece en la primera mitad"
        assert duro in prompt[mitad:], f"{duro!r} no aparece en la segunda mitad"


def test_la_plantilla_declara_rol_formato_de_salida_y_que_no_hacer():
    """`CLAUDE.md` §10, los cuatro apartados obligatorios de todo prompt."""
    for apartado in ("Rol", "Restricciones duras", "Formato de salida", "Qué NO debes hacer"):
        assert apartado in PLANTILLA_V2


def test_la_plantilla_se_identifica_con_su_version_y_su_hash():
    """Regla de dominio 7: `ejecucion` ata la fila al fichero por el hash."""
    assert PROMPT_ID == "escritor"
    assert PROMPT_VERSION == "v2"
    assert len(HASH_DE_PLANTILLA_V2) == 64
    assert HASH_DE_PLANTILLA_V2 != "0" * 64


def test_el_paquete_entra_entero_en_el_prompt():
    """El Escritor no ve nada mas, asi que lo que no entre aqui no existe."""
    prompt = render_escritor(PLANTILLA_V2, "## canon relevante\n\nNadia es botanica", RESTRICCIONES)
    assert "Nadia es botanica" in prompt


# ---------------------------------------------------------------------------
# RF-ESC-03 · el reintento dirigido
# ---------------------------------------------------------------------------


def test_el_primer_prompt_no_lleva_seccion_de_reparacion():
    """El contraste del test siguiente: sin el, «lleva el defecto» pasaria
    igual con una plantilla que hablara de reparacion siempre."""
    prompt = render_escritor(PLANTILLA_V2, "el paquete", RESTRICCIONES)
    assert MARCA_DE_REPARACION not in prompt


def test_el_reintento_lleva_el_defecto_concreto_con_su_cita():
    """RF-ESC-03. **Nunca un reintento generico** (`CLAUDE.md` §15)."""
    prompt = render_escritor(
        PLANTILLA_V2,
        "el paquete",
        RESTRICCIONES,
        texto_anterior=PROSA,
        reparaciones=(DEFECTO,),
    )

    assert MARCA_DE_REPARACION in prompt
    assert "VOZ-03" in prompt
    assert "miro el suelo" in prompt
    assert "38" in prompt and "51" in prompt
    assert PROSA in prompt


def test_el_reintento_por_veto_nombra_el_termino_concreto():
    """RF-GUA-03: «con el termino concreto», no «hay una palabra prohibida».

    La Fase 1 dejo `contiene_veto` devolviendo el termino y no un booleano
    justo para esto, y si el termino no llega al prompt aquel trabajo no sirve
    de nada.
    """
    prompt = render_escritor(
        PLANTILLA_V2,
        "el paquete",
        RESTRICCIONES,
        texto_anterior="Habia sangre en el suelo.",
        reparaciones=(
            Reparacion(
                codigo="SEG-02",
                cita="sangre",
                desplazamiento_inicio=6,
                desplazamiento_fin=12,
                termino_vetado="sangre",
            ),
        ),
    )

    assert "SEG-02" in prompt
    assert "sangre" in prompt


def test_una_reparacion_sin_defectos_no_existe():
    """La mitad de RF-ESC-03 que no se ve: no hay forma de pedir «mejoralo».

    Renderizar con texto anterior y **sin** defectos no produce seccion de
    reparacion. Un reintento generico no es una opcion que este apagada: es una
    que no se puede construir.
    """
    prompt = render_escritor(PLANTILLA_V2, "el paquete", RESTRICCIONES, texto_anterior=PROSA)
    assert MARCA_DE_REPARACION not in prompt


async def test_el_escritor_pasa_la_reparacion_al_prompt(paquete):
    """Del agente y no solo del render: lo que se envia lleva el defecto."""
    doble = DobleDeterminista({MARCA_DE_PLANTILLA: PROSA})
    await Escritor(doble).escribir(
        paquete, RESTRICCIONES, texto_anterior=PROSA, reparaciones=(DEFECTO,)
    )

    prompt, _ = doble.llamadas[-1]
    assert "VOZ-03" in prompt
    assert "miro el suelo" in prompt


# ---------------------------------------------------------------------------
# Lo que el agente no se cree
# ---------------------------------------------------------------------------


async def test_una_prosa_vacia_no_es_una_escena(paquete):
    """Devolver la cadena vacia guardaria un capitulo en blanco con su `run_id`
    y su coste, y se descubriria al maquetar el PDF."""
    with pytest.raises(ProsaVacia):
        await _escritor(prosa="   \n  ").escribir(paquete, RESTRICCIONES)


REPARADA = "Nadia cerro la puerta y estaba mirando la carta."


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    """Lo que el doble de la fixture `escritor` devuelve, **en este orden**.

    La reparacion va primera a proposito: el doble elige por subcadena y en
    orden de insercion, y el prompt del reintento contiene las dos marcas.
    """
    return {MARCA_DE_REPARACION: REPARADA, MARCA_DE_PLANTILLA: PROSA}


async def test_la_fixture_escritor_escribe_sin_sesion(escritor, paquete):
    """La fixture de T8 no recibe sesion, y esta es la comprobacion de que le
    basta con el paquete."""
    assert await escritor.escribir(paquete, RESTRICCIONES) == PROSA


async def test_la_fixture_escritor_distingue_el_reintento(escritor, paquete):
    """Y el reintento se ve desde fuera: otro prompt, otra respuesta."""
    reparada = await escritor.escribir(
        paquete, RESTRICCIONES, texto_anterior=PROSA, reparaciones=(DEFECTO,)
    )
    assert reparada == REPARADA


async def test_la_semilla_viaja_a_la_llamada(paquete):
    """Regla de dominio 7: `ejecucion` la guarda, asi que tiene que existir."""
    doble = DobleDeterminista({MARCA_DE_PLANTILLA: PROSA})
    await Escritor(doble, semilla=7).escribir(paquete, RESTRICCIONES)

    assert doble.llamadas[-1][1] == 7
