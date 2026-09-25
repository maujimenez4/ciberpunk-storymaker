"""La peticion de cambio de punta a punta (plan-5 T7): CA-25, RF-PET-01..07, R-3..R-7.

Ni el ciclo ni la revalidacion llaman al modelo (CA-4): son dobles. Lo demas es
real -- la correccion del canon, la regeneracion, la clasificacion contra el
cuadro guardado, la publicacion con Lean y la retirada de la prosa.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.commons.jobs.turnos import CerrojoDeEscena
from app.conftest import ObraConOutline
from app.features.calidad import Defecto
from app.features.canon import Extraccion, HechoYaSustituido
from app.features.escritura import (
    Escritura,
    ResultadoDelCiclo,
    atender_peticion,
    registrar_peticion,
)
from app.features.escritura.modelos import Trabajo, VersionTexto
from app.features.manuscrito import (
    cuadro_guardado,
    leer_peticion,
    publicar,
    version_vigente,
)
from app.features.manuscrito.modelos import PeticionDeCambio
from app.features.manuscrito.tests.test_publicar import _integrar

PREEXISTENTE = Defecto(
    codigo="VOZ-02",
    version_texto_id="3",
    cita="dijo ella",
    desplazamiento_inicio=0,
    desplazamiento_fin=9,
)


@dataclass
class NovelaPublicada:
    obra_id: int
    hecho_del_perro_id: int
    hecho_sin_uso_id: int
    version_id: int


async def _usar(sesion: AsyncSession, obra: ObraConOutline, hecho_id: int, *numeros: int) -> None:
    for numero in numeros:
        await sesion.execute(
            text("INSERT INTO hecho_usado_en (hecho_canon_id, capitulo_id) VALUES (:h, :c)"),
            {"h": hecho_id, "c": obra.capitulos[numero - 1].id},
        )


@pytest.fixture
async def novela_publicada(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> NovelaPublicada:
    """Diez capitulos integrados, el perro usado en el 3 y el 7, y una tirada vigente
    con un defecto en su cuadro (el preexistente de CA-25)."""
    await _integrar(sesion, obra_con_outline)
    await _usar(sesion, obra_con_outline, obra_con_outline.hecho_canon.id, 3, 7)
    sin_uso = (
        await sesion.execute(
            text(
                "INSERT INTO hecho_canon (obra_id, entidad, atributo, valor, confianza, origen) "
                "VALUES (:o, 'casa', 'lugar', 'el monte', 1.0, 'brief') RETURNING id"
            ),
            {"o": obra_con_outline.obra.id},
        )
    ).scalar_one()
    version = await publicar(
        sesion, obra_con_outline.obra.id, defectos_vigentes=[(2, PREEXISTENTE)]
    )
    await sesion.commit()
    return NovelaPublicada(
        obra_id=obra_con_outline.obra.id,
        hecho_del_perro_id=obra_con_outline.hecho_canon.id,
        hecho_sin_uso_id=int(sin_uso),
        version_id=version.id,
    )


def _ciclo_que_escribe(sesion: AsyncSession, *, aprobado: bool = True) -> Any:
    """Un ciclo sin modelo: escribe una version nueva y deja el trabajo cerrado."""

    async def ejecutar(trabajo: Trabajo, *, consolidar: bool) -> ResultadoDelCiclo:
        assert consolidar is False, "la regeneracion no consolida (decision previa)"
        escena_id = int(
            (
                await sesion.execute(
                    text("SELECT id FROM escena WHERE capitulo_id = :c"),
                    {"c": trabajo.capitulo_id},
                )
            ).scalar_one()
        )
        trabajo.escena_id = escena_id
        numero = int(
            (
                await sesion.execute(
                    text("SELECT MAX(numero) FROM version_texto WHERE escena_id = :e"),
                    {"e": escena_id},
                )
            ).scalar_one()
        )
        await sesion.execute(
            text("UPDATE version_texto SET vigente = 0 WHERE escena_id = :e AND vigente = 1"),
            {"e": escena_id},
        )
        nueva = VersionTexto(
            escena_id=escena_id,
            numero=numero + 1,
            texto="El perro se llamaba Nala.",
            vigente=True,
            run_id=trabajo.run_id,
        )
        sesion.add(nueva)
        trabajo.estado = "INTEGRADA" if aprobado else "ESCALADA"
        await sesion.flush()
        return ResultadoDelCiclo(
            trabajo_id=trabajo.id,
            estado=trabajo.estado,
            run_id=trabajo.run_id,
            escritura=Escritura(
                aprobado=aprobado,
                version_texto_id=nueva.id,
                texto=nueva.texto,
                intentos=(),
            ),
            extraccion=Extraccion(resumen="Nala entra en la historia."),
        )

    return ejecutar


def _revalida(*pares: tuple[int, Defecto]) -> Any:
    async def revalidar(
        sesion: AsyncSession, *, obra_id: int, numeros: Sequence[int]
    ) -> list[tuple[int, Defecto]]:
        return [(c, d) for c, d in pares if c in numeros]

    return revalidar


def _can_01(hecho_id: int) -> Defecto:
    return Defecto(
        codigo="CAN-01",
        version_texto_id="99",
        cita="el perro Luna",
        desplazamiento_inicio=0,
        desplazamiento_fin=13,
        hecho_canon_id=str(hecho_id),
    )


async def _censo(sesion: AsyncSession, obra_id: int) -> tuple[int, int, int]:
    async def cuantas(sql: str) -> int:
        return int((await sesion.execute(text(sql), {"o": obra_id})).scalar_one())

    return (
        await cuantas("SELECT COUNT(*) FROM evento WHERE obra_id = :o"),
        await cuantas("SELECT COUNT(*) FROM hecho_canon WHERE obra_id = :o"),
        await cuantas(
            "SELECT COUNT(*) FROM version_texto AS v JOIN escena AS e ON e.id = v.escena_id "
            "JOIN capitulo AS c ON c.id = e.capitulo_id WHERE c.obra_id = :o"
        ),
    )


async def _pedir(sesion: AsyncSession, novela: NovelaPublicada, hecho_id: int | None = None) -> int:
    peticion = await registrar_peticion(
        sesion,
        obra_id=novela.obra_id,
        hecho_canon_id=hecho_id or novela.hecho_del_perro_id,
        texto_pedido="el perro se llama Nala, no Luna",
    )
    await sesion.commit()
    return peticion.id


async def test_un_defecto_preexistente_no_impide_publicar(
    sesion: AsyncSession, novela_publicada: NovelaPublicada
) -> None:
    """CA-25, primera mitad (RF-PET-06). Y RF-IND-02: solo el 3 y el 7 salen cambiados."""
    peticion_id = await _pedir(sesion, novela_publicada)

    resultado = await atender_peticion(
        sesion,
        peticion_id=peticion_id,
        ejecutar=_ciclo_que_escribe(sesion),
        cerrojo=CerrojoDeEscena(),
        revalidar=_revalida((2, PREEXISTENTE)),
    )

    assert resultado.estado == "atendida", resultado.resultado
    assert resultado.version_producida_id is not None
    assert len(resultado.preexistentes) == 1 and resultado.introducidos == ()
    vigente = await version_vigente(sesion, obra_id=novela_publicada.obra_id)
    assert vigente is not None and vigente.id == resultado.version_producida_id
    cambiados = (
        (
            await sesion.execute(
                text(
                    "SELECT numero FROM capitulo_publicado WHERE version_id = :v AND cambiado = 1 "
                    "ORDER BY numero"
                ),
                {"v": vigente.id},
            )
        )
        .scalars()
        .all()
    )
    assert cambiados == [3, 7]
    assert await cuadro_guardado(sesion, version_publicada_id=vigente.id) == [(2, PREEXISTENTE)]


async def test_un_defecto_introducido_impide_publicar_y_no_deja_rastro(
    sesion: AsyncSession, novela_publicada: NovelaPublicada
) -> None:
    """CA-25, segunda mitad (RF-PET-06 y RF-PET-07) y R-6 de extremo a extremo."""
    eventos, hechos, textos = await _censo(sesion, novela_publicada.obra_id)
    peticion_id = await _pedir(sesion, novela_publicada)

    resultado = await atender_peticion(
        sesion,
        peticion_id=peticion_id,
        ejecutar=_ciclo_que_escribe(sesion),
        cerrojo=CerrojoDeEscena(),
        revalidar=_revalida((2, PREEXISTENTE), (7, _can_01(novela_publicada.hecho_del_perro_id))),
    )

    assert resultado.estado == "descartada"
    assert resultado.version_producida_id is None
    assert len(resultado.introducidos) == 1
    vigente = await version_vigente(sesion, obra_id=novela_publicada.obra_id)
    assert vigente is not None and vigente.id == novela_publicada.version_id
    guardada = await leer_peticion(sesion, peticion_id)
    assert guardada.estado == "descartada" and guardada.resultado
    assert "CAN-01" in guardada.resultado
    # El canon crece en uno: la correccion que el lector pidio (RF-PET-02). Ni
    # un evento ni una version de texto mas: la prosa descartada se retiro.
    assert await _censo(sesion, novela_publicada.obra_id) == (eventos, hechos + 1, textos)


async def test_un_capitulo_que_no_pasa_su_puerta_no_se_publica(
    sesion: AsyncSession, novela_publicada: NovelaPublicada
) -> None:
    """Regla de dominio 14 por el camino nuevo: se descarta y `publicar` no corre."""
    peticion_id = await _pedir(sesion, novela_publicada)

    resultado = await atender_peticion(
        sesion,
        peticion_id=peticion_id,
        ejecutar=_ciclo_que_escribe(sesion, aprobado=False),
        cerrojo=CerrojoDeEscena(),
        revalidar=_revalida(),
    )

    assert resultado.estado == "descartada"
    assert "puerta" in resultado.resultado
    vigente = await version_vigente(sesion, obra_id=novela_publicada.obra_id)
    assert vigente is not None and vigente.id == novela_publicada.version_id


async def test_un_hecho_sin_uso_corrige_el_canon_y_no_publica(
    sesion: AsyncSession, novela_publicada: NovelaPublicada
) -> None:
    """R-3. Atendida, sin version nueva."""
    peticion_id = await _pedir(sesion, novela_publicada, novela_publicada.hecho_sin_uso_id)

    resultado = await atender_peticion(
        sesion,
        peticion_id=peticion_id,
        ejecutar=_ciclo_que_escribe(sesion),
        cerrojo=CerrojoDeEscena(),
        revalidar=_revalida(),
    )

    assert resultado.estado == "atendida"
    assert resultado.version_producida_id is None
    assert resultado.hecho_nuevo_id is not None


async def test_no_se_pide_sobre_un_hecho_ya_sustituido(
    sesion: AsyncSession, novela_publicada: NovelaPublicada
) -> None:
    """R-5, al registrar: el 409 sale en la respuesta y no en el trabajo de fondo."""
    peticion_id = await _pedir(sesion, novela_publicada, novela_publicada.hecho_sin_uso_id)
    await atender_peticion(
        sesion,
        peticion_id=peticion_id,
        ejecutar=_ciclo_que_escribe(sesion),
        cerrojo=CerrojoDeEscena(),
        revalidar=_revalida(),
    )

    with pytest.raises(HechoYaSustituido):
        await _pedir(sesion, novela_publicada, novela_publicada.hecho_sin_uso_id)


async def test_la_segunda_peticion_espera_a_la_primera(
    sesion: AsyncSession, novela_publicada: NovelaPublicada
) -> None:
    """R-4. Con el cerrojo de la obra tomado, la peticion no empieza."""
    cerrojo = CerrojoDeEscena()
    peticion_id = await _pedir(sesion, novela_publicada, novela_publicada.hecho_sin_uso_id)

    async with cerrojo.por_obra(novela_publicada.obra_id):
        tarea = asyncio.create_task(
            atender_peticion(
                sesion,
                peticion_id=peticion_id,
                ejecutar=_ciclo_que_escribe(sesion),
                cerrojo=cerrojo,
                revalidar=_revalida(),
            )
        )
        await asyncio.sleep(0.2)
        assert not tarea.done()
        assert (await sesion.get(PeticionDeCambio, peticion_id)).estado == "registrada"  # type: ignore[union-attr]
    resultado = await tarea
    assert resultado.estado == "atendida"


async def test_la_peticion_queda_regenerando_antes_de_la_primera_llamada(
    sesion: AsyncSession, motor: AsyncEngine, novela_publicada: NovelaPublicada
) -> None:
    """R-7 y RNF-REN-01: confirmado, y visible desde otra conexion."""
    visto: list[str] = []
    peticion_id = await _pedir(sesion, novela_publicada)
    escribe = _ciclo_que_escribe(sesion)

    async def mira(trabajo: Trabajo, *, consolidar: bool) -> ResultadoDelCiclo:
        async with AsyncSession(motor) as otra:
            fila = await otra.get(PeticionDeCambio, peticion_id)
            assert fila is not None
            visto.append(fila.estado)
        return await escribe(trabajo, consolidar=consolidar)  # type: ignore[no-any-return]

    await atender_peticion(
        sesion,
        peticion_id=peticion_id,
        ejecutar=mira,
        cerrojo=CerrojoDeEscena(),
        revalidar=_revalida(),
    )

    assert visto and set(visto) == {"regenerando"}


async def test_republicar_no_duplica_capitulos_regenerados(
    sesion: AsyncSession, novela_publicada: NovelaPublicada
) -> None:
    """Un capitulo con dos trabajos (el original y la regeneracion) se publica una vez."""
    peticion_id = await _pedir(sesion, novela_publicada)
    resultado = await atender_peticion(
        sesion,
        peticion_id=peticion_id,
        ejecutar=_ciclo_que_escribe(sesion),
        cerrojo=CerrojoDeEscena(),
        revalidar=_revalida(),
    )
    filas = (
        await sesion.execute(
            text("SELECT COUNT(*) FROM capitulo_publicado WHERE version_id = :v"),
            {"v": resultado.version_producida_id},
        )
    ).scalar_one()
    assert filas == 10
