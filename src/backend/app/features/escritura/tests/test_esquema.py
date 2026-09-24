"""El esquema de `escritura`: texto inmutable, ejecuciones auditables y trabajos."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.features.escritura.modelos import Ejecucion, Trabajo, VersionTexto


async def test_editar_el_texto_de_una_version_esta_prohibido(sesion, obra_con_outline):
    """RF-ESC-02, y **en el esquema**: el disparador es una pared, no un cartel."""
    version = _version(obra_con_outline, numero=1, vigente=True)
    sesion.add(version)
    await sesion.flush()

    version.texto = "Otra cosa"
    with pytest.raises(IntegrityError, match="inmutable"):
        await sesion.flush()


async def test_editar_crea_otra_version_y_marca_la_vigente(sesion, obra_con_outline):
    """RF-ESC-02: la forma legitima de editar. La anterior se conserva."""
    primera = _version(obra_con_outline, numero=1, vigente=True)
    sesion.add(primera)
    await sesion.flush()

    primera.vigente = False
    sesion.add(_version(obra_con_outline, numero=2, vigente=True, texto="La segunda."))
    await sesion.flush()

    versiones = (await sesion.execute(select(VersionTexto).order_by(VersionTexto.numero))).scalars()
    assert [(v.numero, v.vigente) for v in versiones] == [(1, False), (2, True)]


async def test_solo_una_version_vigente_por_escena(sesion, obra_con_outline):
    """Dos vigentes es no tener ninguna: nadie sabria cual es el manuscrito."""
    sesion.add_all(
        [
            _version(obra_con_outline, numero=1, vigente=True),
            _version(obra_con_outline, numero=2, vigente=True),
        ]
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_la_ejecucion_guarda_lo_que_hace_auditable_una_llamada(sesion, obra_con_outline):
    """RF-OBS-06 y regla de dominio 7, campo a campo.

    Los **dos** recuentos de tokens son P-A: el previsto lo da el contador
    local antes de llamar, y el real lo devuelve el proveedor despues. Guardar
    solo uno deja la deriva del contador local como riesgo declarado en vez de
    como cifra medible.
    """
    sesion.add(
        Ejecucion(
            run_id="run-1",
            obra_id=obra_con_outline.obra.id,
            escena_id=obra_con_outline.escena.id,
            version_obra_id=obra_con_outline.version_obra.id,
            prompt_id="escritor",
            prompt_version="v3",
            prompt_hash="a" * 64,
            modelo="haiku",
            semilla=7,
            parametros={"temperatura": 0.8},
            tokens_por_capa={"constitucional": 900, "instruccion": 400},
            tokens_previstos=1300,
            tokens_reales=1288,
            coste=0.0031,
            ids_recuperados=[11, 12],
            ids_canon=[3],
            veredicto="aprobada",
        )
    )
    await sesion.flush()

    guardada = (await sesion.execute(select(Ejecucion))).scalars().one()
    assert guardada.prompt_hash == "a" * 64
    assert guardada.tokens_por_capa == {"constitucional": 900, "instruccion": 400}
    assert (guardada.tokens_previstos, guardada.tokens_reales) == (1300, 1288)
    assert (guardada.ids_recuperados, guardada.ids_canon) == ([11, 12], [3])
    assert (guardada.modelo, guardada.semilla, guardada.coste) == ("haiku", 7, 0.0031)


async def test_una_ejecucion_sin_recuento_previo_no_entra(sesion, obra_con_outline):
    """RF-CTX-02: nunca se llama sin haber contado, asi que siempre hay previsto."""
    sesion.add(
        Ejecucion(
            run_id="run-2",
            obra_id=obra_con_outline.obra.id,
            prompt_id="escritor",
            prompt_version="v3",
            prompt_hash="b" * 64,
            modelo="haiku",
            semilla=7,
            tokens_previstos=-1,
        )
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_trabajo_no_pasa_de_dos_intentos(sesion, obra_con_outline):
    """`CLAUDE.md` §9.1: maximo dos reparaciones dirigidas; despues, escalado."""
    sesion.add(_trabajo(obra_con_outline, intento=3))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_tipo_de_trabajo_que_no_existe_no_entra(sesion, obra_con_outline):
    """`architecture.md` §3.2 declara los tres tipos, y el conjunto es cerrado."""
    sesion.add(_trabajo(obra_con_outline, tipo="inventado"))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_estado_de_trabajo_que_no_existe_no_entra(sesion, obra_con_outline):
    """`architecture.md` §3.3: diez estados, y ninguno mas."""
    sesion.add(_trabajo(obra_con_outline, estado="CASI"))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_trabajo_recorre_sus_estados_y_conserva_el_run_id(sesion, obra_con_outline):
    """El `run_id` correlaciona las ejecuciones del trabajo: es su idempotencia."""
    trabajo = _trabajo(obra_con_outline)
    sesion.add(trabajo)
    await sesion.flush()

    trabajo.estado = "ESCRIBIENDO"
    await sesion.flush()

    guardado = (await sesion.execute(select(Trabajo))).scalars().one()
    assert (guardado.estado, guardado.run_id) == ("ESCRIBIENDO", "run-1")


def _version(
    obra_con_outline, numero: int, vigente: bool, texto: str = "La primera."
) -> VersionTexto:
    return VersionTexto(
        escena_id=obra_con_outline.escena.id,
        numero=numero,
        texto=texto,
        vigente=vigente,
        run_id="run-1",
    )


def _trabajo(obra_con_outline, **cambios) -> Trabajo:
    campos = {
        "obra_id": obra_con_outline.obra.id,
        "escena_id": obra_con_outline.escena.id,
        "tipo": "escribir_escena",
        "estado": "PLANIFICANDO",
        "intento": 0,
        "run_id": "run-1",
    }
    campos.update(cambios)
    return Trabajo(**campos)
