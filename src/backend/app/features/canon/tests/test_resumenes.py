"""RF-MEM-04 por el lado que faltaba: **leer** el resumen, no solo escribirlo.

La Fase 2 dejo `escribir_resumen_de_capitulo` y la tabla `resumen_capitulo`, y
con eso la mitad del requisito: «resumen por capitulo, derivado del texto
aprobado, **que alimenta el contexto de los siguientes**». Lo segundo no lo
hacia nadie -- ninguna capa leia esa tabla --, y por eso diez capitulos eran
diez cuentos (R-7).

**Que se cuenta y que se lee no es lo mismo, y ahi esta el censo.** Lo que se
lee son los resumenes que existen; lo que se cuenta son los capitulos
anteriores **que ya tienen texto aprobado vigente**, es decir los que deberian
haber dejado uno. Cuando los dos numeros coinciden, la memoria esta al dia;
cuando el censo es mayor, un capitulo escrito no dejo resumen y eso es un fallo
del almacen (RF-CTX-06, R-3). Contar aqui los resumenes encontrados haria la
regla inalcanzable, que es la trampa que `capas.py` nombra.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.canon import (
    contar_capitulos_con_texto_aprobado,
    leer_resumenes_anteriores,
)
from app.features.canon.modelos import ResumenCapitulo
from app.features.canon.repository import escribir_resumen_de_capitulo
from app.features.escena.modelos import Escena
from app.features.escritura.modelos import VersionTexto


async def _escena_de(sesion: AsyncSession, base: ObraConOutline, numero: int) -> Escena:
    """La escena del capitulo `numero`, con `orden_discurso` = `numero` (P-C, 1:1).

    La del capitulo 1 ya la trae la fixture y la cardinalidad es 1:1: crear otra
    choca contra `uq_escena_capitulo`, que es la restriccion que sostiene P-C.
    """
    if numero == 1:
        return base.escena
    escena = Escena(
        capitulo_id=base.capitulos[numero - 1].id,
        version_obra_id=base.version_obra.id,
        orden_discurso=numero,
        tiempo_historia=f"dia {numero}",
        pov="Nadia",
        lugar="El invernadero",
        presentes=["Nadia", "Teo"],
        objetivo_del_pov="Que Teo confiese",
        obstaculo="Teo no habla",
        resultado="si-pero",
        valor_entrada="confianza",
        valor_salida="sospecha",
        extension_objetivo=1200,
        densidad_de_dialogo_objetivo=0.4,
        distancia_psiquica=3,
    )
    sesion.add(escena)
    await sesion.flush()
    return escena


async def _capitulo_escrito(
    sesion: AsyncSession,
    base: ObraConOutline,
    numero: int,
    *,
    texto: str = "el texto aprobado",
    vigente: bool = True,
) -> VersionTexto:
    """Un capitulo con su escena y su version de texto. Sin resumen todavia."""
    escena = await _escena_de(sesion, base, numero)
    version = VersionTexto(
        escena_id=escena.id, numero=1, texto=texto, vigente=vigente, run_id=f"run-{numero}"
    )
    sesion.add(version)
    await sesion.flush()
    return version


async def _resumen_de(
    sesion: AsyncSession,
    base: ObraConOutline,
    numero: int,
    *,
    version_texto_id: int | None,
    texto: str,
) -> ResumenCapitulo:
    resumen = ResumenCapitulo(
        capitulo_id=base.capitulos[numero - 1].id,
        version_texto_id=version_texto_id,
        texto=texto,
        hechos_establecidos=["Nadia.oficio=botanica"],
        hilos_abiertos=["Quien escribio la carta"],
    )
    sesion.add(resumen)
    await sesion.flush()
    return resumen


# ---------------------------------------------------------------------------
# 1. Se lee, y se lee derivado del texto aprobado
# ---------------------------------------------------------------------------


async def test_el_resumen_de_un_capitulo_anterior_se_lee_entero(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Lo que alimenta el contexto del siguiente: texto, hechos e hilos."""
    version = await _capitulo_escrito(sesion, obra_con_outline, 1)
    await _resumen_de(
        sesion, obra_con_outline, 1, version_texto_id=version.id, texto="Nadia cerro el invernadero"
    )

    resumenes = await leer_resumenes_anteriores(
        sesion, obra_id=obra_con_outline.obra.id, antes_de=2
    )

    assert [r.numero for r in resumenes] == [1]
    assert resumenes[0].texto == "Nadia cerro el invernadero"
    assert resumenes[0].hechos_establecidos == ("Nadia.oficio=botanica",)
    assert resumenes[0].hilos_abiertos == ("Quien escribio la carta",)
    assert resumenes[0].version_texto_id == version.id


async def test_el_resumen_que_no_cita_texto_vigente_no_alimenta_nada(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """RF-MEM-04: **derivado** del texto aprobado, no escrito aparte.

    Un resumen que no cita ninguna version de texto no se puede rehacer desde
    el manuscrito: es una segunda verdad sobre el capitulo, y la que gana es el
    texto. Uno que cita una version **descartada** describe prosa que ya no esta
    en el manuscrito, y meterlo en el contexto del capitulo siguiente es
    exactamente como se contradice una novela a si misma.
    """
    descartada = await _capitulo_escrito(sesion, obra_con_outline, 1, vigente=False)
    await _resumen_de(
        sesion, obra_con_outline, 1, version_texto_id=descartada.id, texto="lo que se descarto"
    )
    await _resumen_de(sesion, obra_con_outline, 2, version_texto_id=None, texto="escrito a mano")

    resumenes = await leer_resumenes_anteriores(
        sesion, obra_id=obra_con_outline.obra.id, antes_de=3
    )

    assert resumenes == []


async def test_los_resumenes_llegan_del_mas_reciente_al_mas_antiguo(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """El recorte de la capa de memoria quita **por el final** (`presupuesto.py`).

    Asi que el orden no es estetico: si el capitulo 1 fuera primero, el resumen
    que se perderia al recortar seria el del capitulo inmediatamente anterior,
    que es justo el que el siguiente necesita. `CLAUDE.md` §4.1 manda recortar
    «resultados de menor puntuacion», y en una cadena de capitulos lo de menor
    puntuacion es lo mas lejano.
    """
    for numero in (1, 2, 3):
        version = await _capitulo_escrito(sesion, obra_con_outline, numero)
        await _resumen_de(
            sesion,
            obra_con_outline,
            numero,
            version_texto_id=version.id,
            texto=f"resumen del {numero}",
        )

    resumenes = await leer_resumenes_anteriores(
        sesion, obra_id=obra_con_outline.obra.id, antes_de=4
    )

    assert [r.numero for r in resumenes] == [3, 2, 1]


async def test_el_capitulo_en_curso_no_se_resume_a_si_mismo(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """`antes_de` es estricto, y no es un detalle de indices.

    Un capitulo que se resumiera a si mismo tendria en su contexto el resumen
    de la prosa que todavia no ha escrito. Es el mismo error que el filtro
    estructural evito con la escena en curso, y alli lo destapo una mutacion.

    **Este test paso una vez por el motivo equivocado, y CA-6 lo destapo.**
    Preguntaba por `antes_de=1`, que devuelve `[]` sin llegar a la consulta:
    con el `<` cambiado a `<=` seguia en verde. Se pregunta por el capitulo 2,
    que es donde el corte se decide de verdad.
    """
    primera = await _capitulo_escrito(sesion, obra_con_outline, 1)
    await _resumen_de(sesion, obra_con_outline, 1, version_texto_id=primera.id, texto="del 1")
    segunda = await _capitulo_escrito(sesion, obra_con_outline, 2)
    await _resumen_de(sesion, obra_con_outline, 2, version_texto_id=segunda.id, texto="del 2")

    resumenes = await leer_resumenes_anteriores(
        sesion, obra_id=obra_con_outline.obra.id, antes_de=2
    )

    assert [r.numero for r in resumenes] == [1], "el 2 se esta escribiendo: no se resume solo"


# ---------------------------------------------------------------------------
# 2. El censo: los capitulos que **deberian** haber dejado resumen
# ---------------------------------------------------------------------------


async def test_el_censo_cuenta_los_capitulos_anteriores_con_texto_aprobado(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Dos escritos y uno descartado: el censo son dos, resuman o no.

    Es lo que hace comprobable «la capa llego vacia teniendo con que llenarse»:
    si el censo contara los resumenes encontrados, coincidiria siempre con lo
    entregado y RF-CTX-06 se cumpliria por consecuencia.
    """
    version = await _capitulo_escrito(sesion, obra_con_outline, 1)
    await _resumen_de(sesion, obra_con_outline, 1, version_texto_id=version.id, texto="del 1")
    await _capitulo_escrito(sesion, obra_con_outline, 2)
    await _capitulo_escrito(sesion, obra_con_outline, 3, vigente=False)

    censo = await contar_capitulos_con_texto_aprobado(
        sesion, obra_id=obra_con_outline.obra.id, antes_de=4
    )

    assert censo == 2


async def test_el_primer_capitulo_no_tiene_censo_y_no_es_averia(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """El caso mas normal que hay: nadie ha escrito nada todavia."""
    assert (
        await contar_capitulos_con_texto_aprobado(
            sesion, obra_id=obra_con_outline.obra.id, antes_de=1
        )
        == 0
    )


async def test_ni_los_resumenes_ni_el_censo_cruzan_de_obra(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Una novela no se alimenta de otra, por mucho que compartan fichero."""
    version = await _capitulo_escrito(sesion, obra_con_outline, 1)
    await _resumen_de(sesion, obra_con_outline, 1, version_texto_id=version.id, texto="del 1")

    otra = obra_con_outline.obra.id + 1000
    assert await leer_resumenes_anteriores(sesion, obra_id=otra, antes_de=9) == []
    assert await contar_capitulos_con_texto_aprobado(sesion, obra_id=otra, antes_de=9) == 0


@pytest.mark.parametrize("antes_de", [0, -1])
async def test_un_numero_de_capitulo_no_positivo_no_pregunta_a_la_base(
    sesion: AsyncSession, obra_con_outline: ObraConOutline, antes_de: int
) -> None:
    """No es defensa: es que `numero < 0` es una consulta que nadie deberia hacer."""
    assert (
        await leer_resumenes_anteriores(sesion, obra_id=obra_con_outline.obra.id, antes_de=antes_de)
        == []
    )


async def test_consolidar_dos_veces_el_mismo_capitulo_sobrescribe_el_resumen(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """P-7. `UNIQUE(capitulo_id)` mas `INSERT` siempre era `IntegrityError` al
    regenerar un capitulo ya integrado."""
    capitulo_id = obra_con_outline.capitulos[0].id
    entregada = await _capitulo_escrito(sesion, obra_con_outline, 1)
    await escribir_resumen_de_capitulo(
        sesion,
        capitulo_id=capitulo_id,
        version_texto_id=entregada.id,
        texto="la version que se entrego",
        hechos_establecidos=(),
        hilos_abiertos=(),
    )

    resumen = await escribir_resumen_de_capitulo(
        sesion,
        capitulo_id=capitulo_id,
        version_texto_id=None,
        texto="la version regenerada",
        hechos_establecidos=("perro.nombre=Nala",),
        hilos_abiertos=(),
    )

    assert resumen.texto == "la version regenerada"
    assert resumen.hechos_establecidos == ["perro.nombre=Nala"]
    cuantos = (
        await sesion.execute(
            text("SELECT COUNT(*) FROM resumen_capitulo WHERE capitulo_id = :c"),
            {"c": capitulo_id},
        )
    ).scalar_one()
    assert cuantos == 1
