"""La reanudacion tras la caida (T8). **RF-ORQ-06, RF-ORQ-07, R-2 y `CA-5`.**

`architecture.md` §3.7 lo dice en dos frases y este fichero las prueba:

> «Al arrancar, el orquestador busca trabajos en estado no terminal y los
> retoma desde su ultimo estado persistido.»

> «Un paso interrumpido se **repite entero**, nunca se reanuda a medias.»

Y §3.9 anade la propiedad que TLC comprueba sobre la maquina de la novela: **la
reanudacion no duplica ni pierde capitulos.**

**La caida se simula como lo que es: otra sesion sobre el mismo fichero.** Lo
que el proceso muerto no llego a confirmar no esta, y lo que confirmo si.
Releer por la misma sesion devolveria su mapa de identidad en memoria y el test
pasaria sin que nada se hubiera persistido — es el mismo cuidado que
`test_checkpoint.py` se toma con `ultimo_capitulo_completado`.

**R-2 no es negociable y se prueba en los seis estados no terminales**, uno por
parametro, con un test que ademas exige que la lista sea la de la maquina: si
manana entra un estado nuevo, el que falta se nota aqui y no en produccion.

Ninguna prueba llama al proveedor (CA-4): los tres roles son `DobleDeterminista`.
"""

import json
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.commons.jobs.turnos import CerrojoDeEscena, PresupuestoConcurrente
from app.commons.llm.doble import DobleDeterminista
from app.conftest import ObraConOutline
from app.features.canon.agents import Extractor
from app.features.canon.modelos import ResumenCapitulo
from app.features.escena.agents import Planificador
from app.features.escena.modelos import Escena
from app.features.escritura.agents import Escritor
from app.features.escritura.checkpoint import CapituloAnteriorSinIntegrar
from app.features.escritura.ciclo import Agentes, abrir_trabajo, ejecutar_ciclo
from app.features.escritura.maquina import (
    ESTADOS_TERMINALES,
    Estado,
    NovelaDetenida,
    Senal,
    avanzar,
)
from app.features.escritura.modelos import Trabajo, VersionTexto
from app.features.escritura.reanudacion import (
    ESTADOS_VIVOS,
    TrabajoTerminal,
    descartar,
    planificar_reanudacion,
    reanudar,
    trabajos_en_vuelo,
)
from app.features.obra.modelos import HechoCanon
from app.features.outline.schemas import BeatDeGenero

# ---------------------------------------------------------------------------
# Lo que devuelve el doble, por rol. Duplicado de `test_ciclo.py` a proposito:
# `CLAUDE.md` §5.1 regla 4 dice que se duplica primero y se sube al tercer uso
# real, y una fixture compartida tiene dueno por fichero (regla 4 del reparto).
# ---------------------------------------------------------------------------

FRASE = "Nadia cerro el invernadero y miro la carta que estaba sobre la mesa."
PROSA_BUENA = "\n\n".join(" ".join([FRASE] * 23) for _ in range(4))
"""1.196 palabras: dentro del rango 1.000-1.500 de `definitions.md` §4.1."""

BIBLIA: dict[str, Any] = {
    "protagonista": "Nadia",
    "persona": "3ª limitada",
    "tiempo_verbal": "pasado",
    "nivel_de_calor": 2,
}

FICHA_DICT: dict[str, Any] = {
    "tiempo_historia": "dia 1, manana",
    "elapsed_desde_anterior": None,
    "pov": "Nadia",
    "lugar": "El invernadero",
    "presentes": ["Nadia", "Teo"],
    "mencionados": ["la madre de Teo"],
    "objetivo_del_pov": "Que Teo confiese",
    "obstaculo": "Teo no habla de su madre",
    "resultado": "si-pero",
    "valor_entrada": "confianza",
    "valor_salida": "sospecha",
    "extension_objetivo": 1200,
    "densidad_de_dialogo_objetivo": 0.4,
    "distancia_psiquica": 3,
    "beat_de_genero": "Encuentro",
    "planta": ["la carta sin abrir"],
    "paga": [],
    "revela": [],
}

EXTRACCION = json.dumps(
    {
        "hechos": [{"entidad": "Teo", "atributo": "oficio", "valor": "relojero"}],
        "eventos": [
            {
                "descripcion": "Nadia cierra el invernadero",
                "tiempo_historia": "dia 1, manana",
                "testigos": ["Nadia"],
            }
        ],
        "resumen": "Nadia cierra el invernadero y encuentra una carta.",
        "hilos": [{"pregunta": "quien escribio la carta"}],
    }
)


def _capitulos_del_outline() -> list[dict[str, Any]]:
    return [
        {
            "numero": n,
            "titulo": f"Capitulo {n}",
            "pov_dominante": "Nadia",
            "lugar": "El invernadero",
            "objetivo": "Que Teo confiese",
            "obstaculo": "Teo no habla de su madre",
            "valor_entrada": "confianza",
            "valor_salida": "sospecha",
            "gancho_de_apertura": "La puerta estaba abierta",
            "tipo_de_corte_final": "pregunta",
            "extension_objetivo": 1200,
            "beat_de_genero": beat.value,
        }
        for n, beat in enumerate(BeatDeGenero, start=1)
    ]


def _agentes() -> Agentes:
    doble = DobleDeterminista(
        {
            "# Arquitecto": json.dumps({"biblia": BIBLIA, "capitulos": _capitulos_del_outline()}),
            "PLANIFICADOR DE ESCENA": json.dumps(FICHA_DICT),
            "# Extractor · v1": EXTRACCION,
            "ESCRITOR · v2": PROSA_BUENA,
        }
    )
    return Agentes(
        planificador=Planificador(doble),
        escritor=Escritor(doble),
        extractor=Extractor(doble),
    )


class ContadorDePalabras:
    """El mismo de `conftest.py`: exacto, reproducible y sin red."""

    def contar(self, texto: str) -> int:
        return len(texto.split())


async def _ejecutar(sesion: AsyncSession, trabajo: Trabajo) -> Any:
    """El ciclo de un capitulo, que es lo que la reanudacion recibe inyectado.

    Va como funcion y no dentro de `reanudar` porque el que reanuda no tiene por
    que saber montar un ciclo: lo que decide es **que capitulo** y **con que
    trabajo**, y eso es lo que este fichero prueba.
    """
    assert trabajo.capitulo_id is not None
    return await ejecutar_ciclo(
        sesion,
        trabajo,
        capitulo_id=trabajo.capitulo_id,
        agentes=_agentes(),
        contador=ContadorDePalabras(),
        presupuesto=PresupuestoConcurrente(),
        cerrojo=CerrojoDeEscena(),
    )


@pytest.fixture
async def obra_lista(sesion: AsyncSession, obra_con_outline: ObraConOutline) -> ObraConOutline:
    """La obra planificada **con canon sobre quien sale en la ficha**, y confirmada.

    El `commit` no es ceremonia y es lo que distingue este fichero de los demas:
    lo que la sesion que se cae no confirmo **no existe** para la que reanuda, y
    las fixtures compartidas hacen `flush`. Sin el, la sesion de despues de la
    caida no veria ni la obra.
    """
    obra_con_outline.version_obra.biblia = {
        **obra_con_outline.version_obra.biblia,
        "persona": "3ª limitada",
        "tiempo_verbal": "pasado",
    }
    sesion.add(
        HechoCanon(
            obra_id=obra_con_outline.obra.id,
            entidad="Nadia",
            atributo="oficio",
            valor="botanica",
            origen="brief",
        )
    )
    await sesion.commit()
    return obra_con_outline


async def _integrar(sesion: AsyncSession, plan: ObraConOutline, numero: int) -> Any:
    """Escribe un capitulo entero de verdad, hasta `INTEGRADA`."""
    capitulo = next(c for c in plan.capitulos if c.numero == numero)
    trabajo = await abrir_trabajo(sesion, capitulo_id=capitulo.id)
    resultado = await _ejecutar(sesion, trabajo)
    await sesion.commit()
    return resultado


async def _ficha(sesion: AsyncSession, plan: ObraConOutline, numero: int) -> Escena:
    """La ficha de escena que el Planificador habria dejado antes de la caida.

    Existe desde `PLANIFICANDO`, y esta confirmada porque la transicion a
    `ENSAMBLANDO` hace `commit` (`maquina.avanzar`). Se escribe a mano y no
    llamando al Planificador porque lo que aqui importa no es como nace la
    ficha, sino que **la caida la deja detras**.

    Si ya hay una —el capitulo 1 la trae de la fixture compartida— se reusa:
    `Escena` tiene una sola fila por capitulo (P-C), y es tambien lo que hace el
    ciclo al reanudar, que **no replanifica** una escena que ya existe.
    """
    capitulo = next(c for c in plan.capitulos if c.numero == numero)
    existente = (
        await sesion.execute(select(Escena).where(Escena.capitulo_id == capitulo.id))
    ).scalar_one_or_none()
    if existente is not None:
        return existente
    escena = Escena(
        capitulo_id=capitulo.id,
        version_obra_id=plan.version_obra.id,
        orden_discurso=capitulo.numero,
        tiempo_historia=FICHA_DICT["tiempo_historia"],
        pov=FICHA_DICT["pov"],
        lugar=FICHA_DICT["lugar"],
        presentes=list(FICHA_DICT["presentes"]),
        objetivo_del_pov=FICHA_DICT["objetivo_del_pov"],
        obstaculo=FICHA_DICT["obstaculo"],
        resultado=FICHA_DICT["resultado"],
        valor_entrada=FICHA_DICT["valor_entrada"],
        valor_salida=FICHA_DICT["valor_salida"],
        extension_objetivo=FICHA_DICT["extension_objetivo"],
        densidad_de_dialogo_objetivo=FICHA_DICT["densidad_de_dialogo_objetivo"],
        distancia_psiquica=FICHA_DICT["distancia_psiquica"],
    )
    sesion.add(escena)
    await sesion.flush()
    return escena


_CAMINO: dict[Estado, tuple[Senal, ...]] = {
    Estado.PLANIFICANDO: (),
    Estado.ENSAMBLANDO: (Senal.PASO_COMPLETADO,),
    Estado.ESCRIBIENDO: (Senal.PASO_COMPLETADO, Senal.PASO_COMPLETADO),
    Estado.VALIDANDO: (Senal.PASO_COMPLETADO,) * 3,
    Estado.REPARANDO: (Senal.PASO_COMPLETADO,) * 3 + (Senal.DEFECTO_BLOQUEANTE,),
    Estado.EXTRAYENDO: (Senal.PASO_COMPLETADO,) * 3 + (Senal.APROBADA,),
}
"""Como llega un trabajo a cada estado no terminal, por el camino de §3.3.

Se recorre con `avanzar`, que es la unica forma de mover la maquina, y cada
paso **confirma**: lo que la caida deja detras es exactamente lo que el
orquestador habria persistido hasta ahi.
"""


async def _caida_en(
    sesion: AsyncSession, plan: ObraConOutline, numero: int, estado: Estado
) -> Trabajo:
    """Un capitulo a medias, en el estado pedido, con los restos de su paso.

    Los restos importan tanto como el estado: a partir de `VALIDANDO` la corrida
    ya guardo prosa —`escribir_capitulo` la persiste antes de que la puerta
    opine— y esa fila es la que una reanudacion descuidada convierte en un
    capitulo duplicado.
    """
    capitulo = next(c for c in plan.capitulos if c.numero == numero)
    trabajo = await abrir_trabajo(sesion, capitulo_id=capitulo.id)
    camino = _CAMINO[estado]
    if camino:
        escena = await _ficha(sesion, plan, numero)
        trabajo.escena_id = escena.id
        for senal in camino:
            await avanzar(sesion, trabajo, senal)
        if len(camino) >= 3:
            sesion.add(
                VersionTexto(
                    escena_id=escena.id,
                    numero=1,
                    texto=PROSA_BUENA,
                    vigente=True,
                    run_id=trabajo.run_id,
                )
            )
    await sesion.commit()
    assert trabajo.estado == estado.value
    return trabajo


async def _cuenta(sesion: AsyncSession, tabla: Any, columna: Any, valor: Any) -> int:
    return int(
        (
            await sesion.execute(select(func.count()).select_from(tabla).where(columna == valor))
        ).scalar_one()
    )


# ---------------------------------------------------------------------------
# §3.7 · al arrancar se buscan los trabajos en estado no terminal
# ---------------------------------------------------------------------------


async def test_en_vuelo_estan_los_no_terminales_y_solo_ellos(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """Los diez estados de §3.3, y salen seis. **De los terminales no se vuelve.**

    Si `ESTADOS_VIVOS` incluyera un terminal, la reanudacion retomaria un
    capitulo ya integrado — la mitad «sin duplicar» de `CA-5`— o reviviria un
    escalado que espera a una persona.
    """
    for estado in Estado:
        sesion.add(
            Trabajo(
                obra_id=obra_lista.obra.id,
                escena_id=None,
                capitulo_id=obra_lista.capitulos[0].id,
                tipo="escribir_escena",
                estado=estado.value,
                intento=0,
                run_id=f"run-{estado.value}",
            )
        )
    await sesion.flush()

    vivos = await trabajos_en_vuelo(sesion, obra_id=obra_lista.obra.id)

    assert {t.estado for t in vivos} == {e.value for e in ESTADOS_VIVOS}
    assert ESTADOS_VIVOS == frozenset(Estado) - ESTADOS_TERMINALES
    assert len(ESTADOS_VIVOS) == 6


async def test_sin_obra_se_buscan_los_de_todas_y_con_obra_solo_los_suyas(
    sesion: AsyncSession, obra_lista: ObraConOutline, motor: AsyncEngine
):
    """§3.7 dice «busca trabajos» y §3.8 dice «por obra». Las dos son ciertas.

    Al arrancar, el proceso no sabe todavia de que obras hay que ocuparse, asi
    que la busqueda sin obra existe; a partir de ahi, cada obra se reanuda sola
    y que una se detenga no para a las demas.
    """
    otra = await _otra_obra(sesion)
    sesion.add_all(
        [
            Trabajo(
                obra_id=obra_lista.obra.id,
                escena_id=None,
                capitulo_id=obra_lista.capitulos[0].id,
                tipo="escribir_escena",
                estado=Estado.ESCRIBIENDO.value,
                intento=0,
                run_id="run-a",
            ),
            Trabajo(
                obra_id=otra,
                escena_id=None,
                capitulo_id=None,
                tipo="escribir_escena",
                estado=Estado.VALIDANDO.value,
                intento=0,
                run_id="run-b",
            ),
        ]
    )
    await sesion.flush()

    assert len(await trabajos_en_vuelo(sesion)) == 2
    assert [t.run_id for t in await trabajos_en_vuelo(sesion, obra_id=obra_lista.obra.id)] == [
        "run-a"
    ]


async def _otra_obra(sesion: AsyncSession) -> int:
    from app.features.obra.modelos import Obra

    obra = Obra(
        titulo="La otra",
        genero="romance",
        tono="calido",
        nivel_de_calor=1,
        elementos_obligatorios=["un elemento que el comprador pidio"],
    )
    sesion.add(obra)
    await sesion.flush()
    return obra.id


# ---------------------------------------------------------------------------
# RF-ORQ-06 · desde donde se reanuda
# ---------------------------------------------------------------------------


async def test_la_reanudacion_empieza_por_el_siguiente_al_ultimo_completado(
    sesion: AsyncSession, obra_lista: ObraConOutline, motor: AsyncEngine
):
    """RF-ORQ-06, leido **despues de la caida** y no por la sesion que escribio."""
    await _integrar(sesion, obra_lista, 1)

    async with AsyncSession(motor, expire_on_commit=False) as despues:
        plan = await planificar_reanudacion(despues, obra_id=obra_lista.obra.id)

    assert plan.checkpoint.numero == 1
    assert plan.pendiente is not None
    assert plan.pendiente.numero == 2
    assert plan.terminada is False


async def test_una_obra_sin_nada_integrado_reanuda_por_el_primero(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """Y no se inventa un capitulo cero: empezar por el principio es correcto."""
    plan = await planificar_reanudacion(sesion, obra_id=obra_lista.obra.id)

    assert plan.checkpoint.hay_avance is False
    assert plan.pendiente is not None
    assert plan.pendiente.numero == 1


async def test_la_novela_entera_escrita_no_tiene_nada_que_reanudar(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """`terminada` y no una excepcion: haber acabado no es un error."""
    for capitulo in obra_lista.capitulos:
        sesion.add(
            Trabajo(
                obra_id=obra_lista.obra.id,
                escena_id=None,
                capitulo_id=capitulo.id,
                tipo="escribir_escena",
                estado=Estado.INTEGRADA.value,
                intento=0,
                run_id=f"run-{capitulo.numero}",
            )
        )
    await sesion.flush()

    plan = await planificar_reanudacion(sesion, obra_id=obra_lista.obra.id)

    assert plan.terminada is True
    assert plan.pendiente is None
    assert plan.checkpoint.numero == 10


async def test_la_reanudacion_hereda_las_reparaciones_gastadas_del_capitulo(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """El aviso de T5: **relanzar no devuelve los reintentos.**

    El contador se deriva del maximo de `intento` entre los trabajos del
    capitulo, asi que la caida no lo pone a cero. Si lo pusiera, bastaria con
    matar el proceso para tener dos reparaciones nuevas y el limite de RF-ORQ-04
    dejaria de ser un limite.
    """
    trabajo = await _caida_en(sesion, obra_lista, 1, Estado.REPARANDO)
    trabajo.intento = 2
    await sesion.commit()

    plan = await planificar_reanudacion(sesion, obra_id=obra_lista.obra.id)

    assert plan.pendiente is not None
    assert plan.pendiente.numero == 1
    assert plan.intento == 2


# ---------------------------------------------------------------------------
# Lo que se hace con el trabajo que la caida dejo vivo
# ---------------------------------------------------------------------------


async def test_el_trabajo_interrumpido_queda_fallido_y_deja_de_estar_en_vuelo(
    sesion: AsyncSession, obra_lista: ObraConOutline, motor: AsyncEngine
):
    """§3.6: la caida es un **error tecnico**, y §3.3 lo relanza como trabajo nuevo.

    Dejarlo en `ESCRIBIENDO` para siempre seria una mentira legible por
    `GET /trabajos/{id}` (RI-06): nadie esta escribiendo ese capitulo.
    """
    trabajo = await _caida_en(sesion, obra_lista, 1, Estado.ESCRIBIENDO)

    async with AsyncSession(motor, expire_on_commit=False) as despues:
        muerto = await despues.get(Trabajo, trabajo.id)
        assert muerto is not None
        await descartar(despues, muerto)

    async with AsyncSession(motor, expire_on_commit=False) as otra:
        recuperado = await otra.get(Trabajo, trabajo.id)
        assert recuperado is not None
        assert recuperado.estado == Estado.FALLIDA.value
        assert recuperado.causa_fallo == "caida del proceso en ESCRIBIENDO"
        assert await trabajos_en_vuelo(otra, obra_id=obra_lista.obra.id) == []


async def test_al_descartar_se_retira_la_prosa_que_la_corrida_muerta_dejo(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """R-7 sobre el manuscrito: la prosa que no paso la puerta **no se queda**.

    Y la que se queda es una duplicada: el capitulo se reescribe entero, asi que
    su escena acabaria con dos versiones del mismo texto y una de ellas
    `vigente` — que es lo que el capitulo siguiente leeria como continuidad
    local.
    """
    trabajo = await _caida_en(sesion, obra_lista, 1, Estado.VALIDANDO)
    assert trabajo.escena_id is not None
    assert await _cuenta(sesion, VersionTexto, VersionTexto.run_id, trabajo.run_id) == 1

    await descartar(sesion, trabajo)

    assert await _cuenta(sesion, VersionTexto, VersionTexto.escena_id, trabajo.escena_id) == 0


async def test_no_se_descarta_un_trabajo_que_ya_termino(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """Un `INTEGRADA` descartado seria un capitulo perdido, que es la otra mitad
    de `CA-5`. Se lanza en vez de no hacer nada: quien lo pide se ha equivocado
    de trabajo y callarselo lo deja creyendo que limpio algo."""
    trabajo = Trabajo(
        obra_id=obra_lista.obra.id,
        escena_id=None,
        capitulo_id=obra_lista.capitulos[0].id,
        tipo="escribir_escena",
        estado=Estado.INTEGRADA.value,
        intento=0,
        run_id="run-hecho",
    )
    sesion.add(trabajo)
    await sesion.flush()

    with pytest.raises(TrabajoTerminal):
        await descartar(sesion, trabajo)


# ---------------------------------------------------------------------------
# R-2 · se mata el proceso en CADA estado no terminal
# ---------------------------------------------------------------------------


def test_r2_se_prueba_en_todos_los_estados_no_terminales():
    """El guardia de R-2: **la lista de parametros es la de la maquina.**

    «Probarlo solo en `ESCRIBIENDO` deja los demas sin probar» es el aviso del
    plan, y un parametro que se olvide no se nota leyendo el fichero. Si manana
    entra un estado no terminal nuevo, este test cae antes que produccion.
    """
    assert set(_CAMINO) == set(ESTADOS_VIVOS)


@pytest.mark.parametrize("estado", sorted(ESTADOS_VIVOS, key=lambda e: e.value))
async def test_tras_la_caida_se_reanuda_sin_duplicar_ni_perder(
    sesion: AsyncSession, obra_lista: ObraConOutline, motor: AsyncEngine, estado: Estado
):
    """**R-2 y `CA-5` enteros, estado a estado.**

    Se integra el capitulo 1 de verdad, se mata el proceso con el 2 en el estado
    del parametro y se reanuda por otra sesion. Lo que se exige despues es lo
    que la spec llama «ni duplicar ni perder»: cada capitulo con **una** escena,
    **un** resumen y **una** version vigente, y el avance en el 2.
    """
    await _integrar(sesion, obra_lista, 1)
    muerto = await _caida_en(sesion, obra_lista, 2, estado)
    capitulo = obra_lista.capitulos[1]

    async with AsyncSession(motor, expire_on_commit=False) as despues:
        retomada = await reanudar(
            despues, obra_id=obra_lista.obra.id, ejecutar=lambda t: _ejecutar(despues, t)
        )
        await despues.commit()

    assert retomada.capitulo_id == capitulo.id
    assert retomada.numero == 2
    assert retomada.trabajo_id != muerto.id
    assert muerto.id in retomada.descartados

    async with AsyncSession(motor, expire_on_commit=False) as otra:
        for numero, cap in [(1, obra_lista.capitulos[0]), (2, capitulo)]:
            assert await _cuenta(otra, Escena, Escena.capitulo_id, cap.id) == 1, numero
            assert await _cuenta(otra, ResumenCapitulo, ResumenCapitulo.capitulo_id, cap.id) == 1, (
                numero
            )
            integrados = await otra.execute(
                select(func.count())
                .select_from(Trabajo)
                .where(Trabajo.capitulo_id == cap.id, Trabajo.estado == Estado.INTEGRADA.value)
            )
            assert integrados.scalar_one() == 1, numero

        escena = (
            await otra.execute(select(Escena).where(Escena.capitulo_id == capitulo.id))
        ).scalar_one()
        vigentes = await otra.execute(
            select(func.count())
            .select_from(VersionTexto)
            .where(VersionTexto.escena_id == escena.id, VersionTexto.vigente.is_(True))
        )
        assert vigentes.scalar_one() == 1

        plan = await planificar_reanudacion(otra, obra_id=obra_lista.obra.id)
        assert plan.checkpoint.numero == 2
        assert await trabajos_en_vuelo(otra, obra_id=obra_lista.obra.id) == []


async def test_la_novela_sigue_hasta_el_final_tras_la_caida(
    sesion: AsyncSession, obra_lista: ObraConOutline, motor: AsyncEngine
):
    """RF-ORQ-07 sobre varios capitulos seguidos: **ninguno dos veces, ninguno menos.**

    Un solo capitulo no ejercita la propiedad: lo que R-2 promete es que la
    novela **sigue**, y el fallo tipico —reanudar siempre por el mismo capitulo,
    o saltarse el interrumpido— solo se ve con el bucle puesto.
    """
    await _integrar(sesion, obra_lista, 1)
    await _caida_en(sesion, obra_lista, 2, Estado.ESCRIBIENDO)

    async with AsyncSession(motor, expire_on_commit=False) as despues:
        for _ in range(3):
            retomada = await reanudar(
                despues, obra_id=obra_lista.obra.id, ejecutar=lambda t: _ejecutar(despues, t)
            )
            await despues.commit()
            if retomada.numero == 4:
                break

    async with AsyncSession(motor, expire_on_commit=False) as otra:
        for cap in obra_lista.capitulos[:4]:
            assert await _cuenta(otra, ResumenCapitulo, ResumenCapitulo.capitulo_id, cap.id) == 1
        plan = await planificar_reanudacion(otra, obra_id=obra_lista.obra.id)
        assert plan.checkpoint.numero == 4
        assert plan.pendiente is not None
        assert plan.pendiente.numero == 5


async def test_reanudar_no_vuelve_a_resumir_un_capitulo_ya_integrado(
    sesion: AsyncSession, obra_lista: ObraConOutline, motor: AsyncEngine
):
    """El aviso de T6: `resumen_capitulo` tiene `UNIQUE(capitulo_id)`.

    Consolidar dos veces el mismo capitulo saltaria con `IntegrityError`, y el
    guardia de T3 no cubre esa tabla. **Lo que lo impide es de donde arranca la
    reanudacion**: el primer capitulo *no integrado*, nunca uno hecho. Aqui se
    mata el proceso con el 1 ya integrado y el 2 en `EXTRAYENDO` —el paso que
    escribe el resumen— y se exige que el 1 siga teniendo uno solo.
    """
    await _integrar(sesion, obra_lista, 1)
    await _caida_en(sesion, obra_lista, 2, Estado.EXTRAYENDO)
    primero = obra_lista.capitulos[0]

    async with AsyncSession(motor, expire_on_commit=False) as despues:
        retomada = await reanudar(
            despues, obra_id=obra_lista.obra.id, ejecutar=lambda t: _ejecutar(despues, t)
        )
        await despues.commit()

    assert retomada.numero == 2

    async with AsyncSession(motor, expire_on_commit=False) as otra:
        assert await _cuenta(otra, ResumenCapitulo, ResumenCapitulo.capitulo_id, primero.id) == 1
        assert (
            await _cuenta(
                otra, ResumenCapitulo, ResumenCapitulo.capitulo_id, obra_lista.capitulos[1].id
            )
            == 1
        )


async def test_un_capitulo_escalado_detiene_la_reanudacion(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """R-6 sobre la reanudacion: **no se sigue escribiendo encima de un escalado.**

    Reanudar no es una via alternativa para saltarse el freno. Si lo fuera,
    bastaria con reiniciar el proceso para que la novela pasara por encima de un
    capitulo que espera decision humana.
    """
    sesion.add(
        Trabajo(
            obra_id=obra_lista.obra.id,
            escena_id=None,
            capitulo_id=obra_lista.capitulos[0].id,
            tipo="escribir_escena",
            estado=Estado.ESCALADA.value,
            intento=2,
            run_id="run-escalado",
        )
    )
    await sesion.flush()

    with pytest.raises(NovelaDetenida):
        await reanudar(sesion, obra_id=obra_lista.obra.id, ejecutar=lambda t: _ejecutar(sesion, t))


async def test_la_reanudacion_no_se_salta_un_hueco_anterior(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """CU-03: los diez capitulos **no se paralelizan**, ni siquiera reanudando.

    Se integra el 2 sin el 1 —lo que dejaria una corrida mal ordenada— y se
    exige que la reanudacion se niegue a seguir por el 3. Sin esta llamada, el
    hueco se escribiria tres capitulos despues, cuando ya no se sabe de donde
    viene.
    """
    trabajo = Trabajo(
        obra_id=obra_lista.obra.id,
        escena_id=None,
        capitulo_id=obra_lista.capitulos[1].id,
        tipo="escribir_escena",
        estado=Estado.INTEGRADA.value,
        intento=0,
        run_id="run-2",
    )
    sesion.add(trabajo)
    await sesion.flush()

    plan = await planificar_reanudacion(sesion, obra_id=obra_lista.obra.id)
    assert plan.pendiente is not None
    assert plan.pendiente.numero == 1
    assert plan.checkpoint.numero == 2

    # Y si alguien fuerza el capitulo posterior al hueco, `empezar_capitulo` lo
    # frena: es la comprobacion que la reanudacion no puede saltarse.
    from app.features.escritura.checkpoint import empezar_capitulo

    with pytest.raises(CapituloAnteriorSinIntegrar):
        await empezar_capitulo(
            sesion, obra_id=obra_lista.obra.id, capitulo_id=obra_lista.capitulos[2].id
        )


# ---------------------------------------------------------------------------
# Lo que la mutacion de CA-6 dejo al descubierto: cuatro reglas sin test
# ---------------------------------------------------------------------------


class _EjecutorEspia:
    """Un `ejecutar` que no escribe nada y apunta como llego el trabajo.

    Es lo que hace comprobable el estado **con el que nace** el trabajo
    relanzado: el ciclo real sobrescribe `intento` con las reparaciones que
    gasto esta vuelta, asi que despues de ejecutarlo ya no se puede preguntar.
    """

    def __init__(self) -> None:
        self.llamadas: list[tuple[int, int, str]] = []

    async def __call__(self, trabajo: Trabajo) -> str:
        self.llamadas.append((trabajo.id, trabajo.intento, trabajo.run_id))
        return "ejecutado"


async def test_el_trabajo_relanzado_nace_con_las_reparaciones_del_capitulo(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """El aviso de T5, ya no en el plan sino en la fila. **Relanzar no regala vueltas.**

    El plan hereda el contador y el trabajo tambien tiene que nacer con el: si
    naciera a cero, la maquina saldria de `REPARANDO` hacia `ESCRIBIENDO` en vez
    de escalar, y matar el proceso seria la forma de conseguir dos reparaciones
    mas por capitulo.
    """
    muerto = await _caida_en(sesion, obra_lista, 1, Estado.REPARANDO)
    muerto.intento = 2
    await sesion.commit()
    espia = _EjecutorEspia()

    retomada = await reanudar(sesion, obra_id=obra_lista.obra.id, ejecutar=espia)

    assert retomada.intento == 2
    assert [intento for _, intento, _ in espia.llamadas] == [2]


async def test_al_descartar_vuelve_a_ser_vigente_la_version_anterior(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """Una escena sin ninguna version vigente es una escena sin manuscrito.

    La corrida que murio apago la vigente al guardar la suya
    (`escribir_capitulo`). Si al retirar la suya no se enciende la anterior, el
    capitulo desaparece del manuscrito sin que nadie lo borrara — y eso es
    **perder**, la otra mitad de `CA-5`.
    """
    escena = await _ficha(sesion, obra_lista, 1)
    trabajo = await abrir_trabajo(sesion, capitulo_id=obra_lista.capitulos[0].id)
    await avanzar(sesion, trabajo, Senal.PASO_COMPLETADO)
    sesion.add_all(
        [
            VersionTexto(
                escena_id=escena.id,
                numero=1,
                texto=PROSA_BUENA,
                vigente=False,
                run_id="run-aprobado",
            ),
            VersionTexto(
                escena_id=escena.id,
                numero=2,
                texto=PROSA_BUENA,
                vigente=True,
                run_id=trabajo.run_id,
            ),
        ]
    )
    await sesion.commit()

    await descartar(sesion, trabajo)

    vigentes = (
        (
            await sesion.execute(
                select(VersionTexto.run_id).where(
                    VersionTexto.escena_id == escena.id, VersionTexto.vigente.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )
    assert list(vigentes) == ["run-aprobado"]


async def test_una_novela_detenida_no_toca_lo_que_quedo_en_vuelo(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """R-6 **antes** de la primera escritura, y por eso la puerta va donde va.

    Reanudar una obra detenida informa y no hace. Si se descartara primero y se
    preguntara despues, el reinicio dejaria cerrados como `FALLIDA` los trabajos
    de una obra cuya continuacion todavia no ha decidido nadie — y la decision
    sobre un capitulo escalado es de una persona (§3.3).
    """
    sesion.add_all(
        [
            Trabajo(
                obra_id=obra_lista.obra.id,
                escena_id=None,
                capitulo_id=obra_lista.capitulos[0].id,
                tipo="escribir_escena",
                estado=Estado.ESCALADA.value,
                intento=2,
                run_id="run-escalado",
            ),
            Trabajo(
                obra_id=obra_lista.obra.id,
                escena_id=None,
                capitulo_id=obra_lista.capitulos[1].id,
                tipo="escribir_escena",
                estado=Estado.ESCRIBIENDO.value,
                intento=0,
                run_id="run-vivo",
            ),
        ]
    )
    await sesion.flush()
    espia = _EjecutorEspia()

    with pytest.raises(NovelaDetenida):
        await reanudar(sesion, obra_id=obra_lista.obra.id, ejecutar=espia)

    assert espia.llamadas == []
    assert [t.run_id for t in await trabajos_en_vuelo(sesion, obra_id=obra_lista.obra.id)] == [
        "run-vivo"
    ]


async def test_reanudar_con_la_novela_escrita_no_abre_ningun_trabajo(
    sesion: AsyncSession, obra_lista: ObraConOutline
):
    """Arrancar sobre una novela terminada es el caso normal de un reinicio.

    No se lanza y **no se escribe**: abrir un trabajo mas seria empezar un
    capitulo once que el outline no tiene, y llamar al ciclo costaria una
    llamada al modelo por nada.
    """
    for capitulo in obra_lista.capitulos:
        sesion.add(
            Trabajo(
                obra_id=obra_lista.obra.id,
                escena_id=None,
                capitulo_id=capitulo.id,
                tipo="escribir_escena",
                estado=Estado.INTEGRADA.value,
                intento=0,
                run_id=f"run-{capitulo.numero}",
            )
        )
    await sesion.flush()
    espia = _EjecutorEspia()

    retomada = await reanudar(sesion, obra_id=obra_lista.obra.id, ejecutar=espia)

    assert retomada.terminada is True
    assert retomada.trabajo_id is None
    assert retomada.descartados == ()
    assert espia.llamadas == []
    assert (
        await sesion.execute(
            select(func.count()).select_from(Trabajo).where(Trabajo.obra_id == obra_lista.obra.id)
        )
    ).scalar_one() == 10
