"""La novela entera: diez capitulos integrados desde el brief. **`CA-1`.**

Es la fase en un test, y la trampa que la tarea avisa esta escrita aqui para que
nadie la vuelva a caer: **un test de diez capitulos que solo cuenta diez filas
pasa con una implementacion que los escriba en cualquier orden.** Lo que se
comprueba, entonces, no es el recuento sino las dos cosas que solo son ciertas
si la secuencia se respeto:

1. **El orden.** El trabajo del capitulo N nace despues de que el N-1 quedara
   `INTEGRADA`, y eso se lee en la base sin creerselo: los identificadores de
   `trabajo` crecen con el numero de capitulo.
2. **La cadena de contexto.** El paquete del capitulo N cita la `version_texto`
   del N-1 en su capa de continuidad y el `resumen_capitulo` del N-1 en la de
   memoria. Eso **no se puede falsificar escribiendo en otro orden**: el texto
   y el resumen del anterior tienen que existir antes.

Ninguna prueba llama al proveedor (CA-4): el cliente es `DobleDeterminista`.
"""

import json
from dataclasses import replace
from typing import Any

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.jobs.turnos import CerrojoDeEscena, PresupuestoConcurrente
from app.commons.llm.doble import DobleDeterminista
from app.features.calidad import (
    CATALOGO_DE_MANUSCRITO,
    CODIGO_DE_ELEMENTO_AUSENTE,
    Cobertura,
    ElementoAusente,
    ElementoCubierto,
    ManuscritoAValidar,
    PuntoDeEjecucion,
    cerrar_manuscrito,
)
from app.features.canon.agents import Extractor
from app.features.escena.agents import Planificador
from app.features.escritura.agents import Escritor
from app.features.escritura.ciclo import Agentes
from app.features.escritura.modelos import Ejecucion, Trabajo
from app.features.escritura.novela import (
    ciclo_de_la_novela,
    cobertura_de_la_novela,
    elementos_obligatorios_de,
    escribir_novela,
    hechos_usados,
    numero_de_capitulo,
)
from app.features.obra.modelos import Entrevista, HechoCanon

# ---------------------------------------------------------------------------
# El brief de ejemplo, y lo que el doble contesta a cada rol
# ---------------------------------------------------------------------------

BRIEF_DE_EJEMPLO: dict[str, Any] = {
    "nombre": "Marta",
    "edad": 34,
    "rasgos": ["terca", "curiosa"],
    "recuerdos_aportados": ["el verano en Cadiz"],
    "genero": "romance",
    "tono": "calido",
    "nivel_de_calor": 2,
    "elementos_obligatorios": ["el perro Luna", "la bufanda roja"],
}
"""El brief del que sale la novela. **Dos elementos obligatorios y a proposito:**
uno lo respalda un hecho del canon y el otro no, asi que `CA-15` se ve por los
dos lados en la misma corrida — el que aparece y el que se echa en falta."""

FRASE = "Nadia cerro el invernadero y miro la carta que estaba sobre la mesa."
PROSA_BUENA = "\n\n".join(" ".join([FRASE] * 23) for _ in range(4))
"""1.196 palabras: dentro del rango 1.000-1.500 de `definitions.md` §4.1."""

PROSA_CORTA = FRASE
"""Trece palabras: `EST-02`, y la puerta rechaza sin que haya veto de por medio."""

BIBLIA: dict[str, Any] = {
    "protagonista": "Nadia",
    "persona": "3ª limitada",
    "tiempo_verbal": "pasado",
    "nivel_de_calor": 2,
}

FICHA = json.dumps(
    {
        "tiempo_historia": "dia 1, manana",
        "elapsed_desde_anterior": None,
        "pov": "Nadia",
        "lugar": "El invernadero",
        "presentes": ["Nadia", "Teo"],
        "mencionados": ["Luna"],
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
)
"""Menciona a **Luna** y no al perro de la fixture de otros modulos: es lo que
hace que el hecho del brief entre en la capa de canon y quede registrado en
`hecho_usado_en`, que es de donde la cobertura lee."""

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

_ENTREVISTA_COMPLETA = json.dumps({"faltantes": [], "contradicciones": []})


def _capitulos_del_outline() -> list[dict[str, Any]]:
    from app.features.outline.schemas import BeatDeGenero

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


def _respuestas(prosa: str = PROSA_BUENA) -> dict[str, str]:
    """Lo que devuelve el doble, por marca del prompt. **El orden importa:** se
    elige la primera clave que sea subcadena del prompt."""
    return {
        "ENTREVISTADOR": _ENTREVISTA_COMPLETA,
        "# Arquitecto": json.dumps({"biblia": BIBLIA, "capitulos": _capitulos_del_outline()}),
        "PLANIFICADOR DE ESCENA": FICHA,
        "# Extractor · v1": EXTRACCION,
        "ESCRITOR · v1": prosa,
        # P-17: el Continuista **corre de verdad** desde que `Agentes` lo lleva.
        # Sin esta clave el doble lanza `RespuestaNoPreparada`, y eso es una
        # buena noticia: significa que el rol dejo de estar escrito y sin llamar.
        "# Continuista": '{"defectos": []}',
    }


class ContadorDePalabras:
    """El mismo de `conftest.py`: exacto, reproducible y sin red."""

    def contar(self, texto: str) -> int:
        return len(texto.split())


def _agentes(respuestas: dict[str, str]) -> Agentes:
    doble = DobleDeterminista(respuestas)
    return Agentes(
        planificador=Planificador(doble),
        escritor=Escritor(doble),
        extractor=Extractor(doble),
    )


async def _correr(sesion: AsyncSession, obra_id: int, *, prosa: str = PROSA_BUENA):
    """La novela entera con los dobles de los cuatro roles."""
    return await escribir_novela(
        sesion,
        obra_id=obra_id,
        ejecutar=ciclo_de_la_novela(
            sesion,
            agentes=_agentes(_respuestas(prosa)),
            contador=ContadorDePalabras(),
            presupuesto=PresupuestoConcurrente(),
            cerrojo=CerrojoDeEscena(),
        ),
    )


@pytest.fixture
async def obra_lista(sesion: AsyncSession, obra_con_outline):
    """La obra planificada, con la biblia que el ciclo relee y el hecho del brief.

    El hecho es **Luna**, que es a quien nombra la ficha: sin el, la capa de
    canon sale vacia con el grafo lleno y el ensamblado falla antes de llamar
    (RF-CTX-06). Y es el que cubre «el perro Luna» del brief.
    """
    obra_con_outline.version_obra.biblia = {
        **obra_con_outline.version_obra.biblia,
        "persona": "3ª limitada",
        "tiempo_verbal": "pasado",
    }
    obra_con_outline.hecho_canon.entidad = "Luna"
    obra_con_outline.hecho_canon.atributo = "especie"
    obra_con_outline.hecho_canon.valor = "perro"
    # La escena del primer capitulo viene de la fixture compartida y **no se
    # replanifica** —`ciclo.py` solo planifica si no hay ficha—, asi que a ella
    # hay que anadirle la mencion a mano. De la segunda en adelante la pone el
    # Planificador con `FICHA`.
    obra_con_outline.escena.mencionados = ["Luna"]
    # P-2: los elementos viven en `obra` desde T3. La entrevista se deja porque
    # es por donde llegan de verdad, pero **ya no es de donde se leen**: el test
    # de `features/obra` la borra y comprueba que la cobertura sigue contando.
    obra_con_outline.obra.elementos_obligatorios = list(BRIEF_DE_EJEMPLO["elementos_obligatorios"])
    sesion.add(
        Entrevista(
            respuestas={"elementos_obligatorios": BRIEF_DE_EJEMPLO["elementos_obligatorios"]},
            obra_id=obra_con_outline.obra.id,
        )
    )
    await sesion.flush()
    return obra_con_outline


# ---------------------------------------------------------------------------
# CA-1 · de la obra planificada salen diez capitulos integrados
# ---------------------------------------------------------------------------


async def test_de_una_obra_planificada_salen_diez_capitulos_integrados(sesion, obra_lista):
    """`CA-1`. Diez, todos `INTEGRADA`, y el checkpoint en el ultimo."""
    novela = await _correr(sesion, obra_lista.obra.id)

    assert novela.completa
    assert [c.numero for c in novela.integrados] == list(range(1, 11))
    assert novela.detenida_en is None
    assert novela.checkpoint.numero == 10

    integrados = (
        await sesion.execute(
            select(func.count())
            .select_from(Trabajo)
            .where(Trabajo.obra_id == obra_lista.obra.id, Trabajo.estado == "INTEGRADA")
        )
    ).scalar_one()
    assert integrados == 10


async def test_los_diez_se_escriben_en_orden_y_no_en_cualquiera(sesion, obra_lista):
    """CU-03. **Contar diez filas no distingue el orden; esto si.**

    El identificador de `trabajo` es monotono: si el capitulo 7 se hubiera
    escrito antes que el 4, su trabajo tendria el numero menor.
    """
    await _correr(sesion, obra_lista.obra.id)

    filas = (
        (
            await sesion.execute(
                text(
                    "SELECT c.numero AS numero FROM trabajo AS t "
                    "JOIN capitulo AS c ON c.id = t.capitulo_id "
                    "WHERE t.obra_id = :obra_id AND t.estado = 'INTEGRADA' "
                    "ORDER BY t.id"
                ),
                {"obra_id": obra_lista.obra.id},
            )
        )
        .scalars()
        .all()
    )
    assert list(filas) == list(range(1, 11))


async def test_cada_capitulo_lleva_el_anterior_en_su_paquete(sesion, obra_lista):
    """R-7 a escala: **la cadena de contexto, no el recuento.**

    El paquete del capitulo N cita la `version_texto` vigente del N-1 en la capa
    de continuidad y el `resumen_capitulo` del N-1 en la de memoria. Las dos
    piezas solo existen si el anterior se escribio antes, asi que esta asercion
    es la que ningun orden alternativo puede satisfacer.
    """
    await _correr(sesion, obra_lista.obra.id)

    por_capitulo = {c.numero: c.id for c in obra_lista.capitulos}
    for numero in range(2, 11):
        ids = await _ids_por_capa(sesion, por_capitulo[numero])
        anterior = por_capitulo[numero - 1]
        assert f"rc:{anterior}" in ids["memoria"], numero
        assert f"vt:{await _version_vigente(sesion, anterior)}" in ids["continuidad"], numero


async def test_una_novela_terminada_no_vuelve_a_escribir_ningun_capitulo(sesion, obra_lista):
    """La mitad «sin duplicar» de `CA-5`, vista desde el bucle: volver a pedir
    la novela entera sobre una obra completa no abre un solo trabajo mas."""
    await _correr(sesion, obra_lista.obra.id)
    antes = (await sesion.execute(select(func.count()).select_from(Trabajo))).scalar_one()

    segunda = await _correr(sesion, obra_lista.obra.id)

    assert segunda.completa
    assert segunda.integrados == ()
    despues = (await sesion.execute(select(func.count()).select_from(Trabajo))).scalar_one()
    assert despues == antes


async def test_un_capitulo_escalado_detiene_la_novela_y_no_escribe_el_siguiente(sesion, obra_lista):
    """R-6. **Se detiene y se informa**; no se salta al siguiente."""
    novela = await _correr(sesion, obra_lista.obra.id, prosa=PROSA_CORTA)

    assert not novela.completa
    assert novela.integrados == ()
    assert novela.detenida_en is not None
    assert novela.detenida_en.numero == 1
    assert novela.detenida_en.estado == "ESCALADA"
    assert "EST-02" in (novela.causa or "")

    escritos = (await sesion.execute(select(func.count()).select_from(Trabajo))).scalar_one()
    assert escritos == 1


# ---------------------------------------------------------------------------
# RI-06 · el estado de la novela se lee por trabajo, y **por capitulo**
# ---------------------------------------------------------------------------


async def test_numero_de_capitulo_traduce_el_identificador_al_numero_del_outline(
    sesion, obra_con_outline
):
    """RI-06 dice «legible **por capitulo**», y un identificador no lo es.

    **Con la primera obra esto no se puede comprobar:** sus capitulos tienen
    `id` 1..10 y `numero` 1..10, asi que devolver el identificador pasaria el
    test y `GET /trabajos/{id}` diria «capitulo 47» de una novela de diez. Es la
    misma trampa que T7 aviso para `usado_en`, y la mutacion la encontro viva
    aqui. Por eso se mide la **segunda** obra.
    """
    _, capitulos = await _otra_obra_con_capitulos(sesion)
    septimo = capitulos[6]
    assert septimo.capitulo_id != septimo.numero

    assert await numero_de_capitulo(sesion, capitulo_id=septimo.capitulo_id) == 7
    assert await numero_de_capitulo(sesion, capitulo_id=None) is None
    assert await numero_de_capitulo(sesion, capitulo_id=9999) is None


# ---------------------------------------------------------------------------
# CA-15 · la cobertura, de extremo a extremo
# ---------------------------------------------------------------------------


async def test_los_hechos_usados_llevan_el_numero_del_capitulo_y_no_su_identificador(
    sesion, obra_con_outline
):
    """El aviso de T7, y **se prueba con identificadores que no coinciden**.

    Con una sola obra los diez capitulos tienen `id` 1..10 y `numero` 1..10, asi
    que pasar identificadores en vez de numeros pasaria el test igual y el
    informe seria inservible sin que nada fallara. Por eso los capitulos que se
    miden son los de una **segunda** obra: sus identificadores empiezan donde
    acaban los de la primera y su numeracion vuelve a empezar por uno.
    """
    otra_id, capitulos = await _otra_obra_con_capitulos(sesion)
    tercero = capitulos[2]
    assert tercero.capitulo_id != tercero.numero

    hecho = HechoCanon(
        obra_id=otra_id, entidad="Luna", atributo="especie", valor="perro", origen="brief"
    )
    sesion.add(hecho)
    await sesion.flush()
    await sesion.execute(
        text("INSERT INTO hecho_usado_en (hecho_canon_id, capitulo_id) VALUES (:hecho, :capitulo)"),
        {"hecho": hecho.id, "capitulo": tercero.capitulo_id},
    )
    await sesion.flush()

    usados = await hechos_usados(sesion, obra_id=otra_id)

    luna = next(h for h in usados if h.entidad == "Luna")
    assert luna.usado_en == (3,)


async def test_un_hecho_que_ningun_capitulo_usa_llega_con_usado_en_vacio(sesion, obra_lista):
    """El hecho del brief entra al canon antes de la primera linea de prosa
    (RF-ENT-06). Si no llegara a la cobertura, su guarda no tendria nada contra
    lo que defenderse y la regla de `cobertura.py` seria inalcanzable."""
    usados = await hechos_usados(sesion, obra_id=obra_lista.obra.id)

    assert usados
    assert all(h.usado_en == () for h in usados)


async def test_la_cobertura_dice_cual_falta_sobre_la_novela_entera(sesion, obra_lista):
    """`CA-15` y R-5, de extremo a extremo y contra la tabla de hechos.

    «el perro Luna» lo respalda un hecho que entro en los diez paquetes; «la
    bufanda roja» no lo respalda ninguno, y lo que se exige es que se diga
    **cual** falta, no que falte algo.
    """
    await _correr(sesion, obra_lista.obra.id)

    cobertura = await cobertura_de_la_novela(sesion, obra_id=obra_lista.obra.id)

    assert not cobertura.completa
    assert [c.elemento for c in cobertura.cubiertos] == ["el perro Luna"]
    assert cobertura.cubiertos[0].capitulos == tuple(range(1, 11))
    assert [a.elemento for a in cobertura.ausentes] == ["la bufanda roja"]
    assert cobertura.ausentes[0].codigo == CODIGO_DE_ELEMENTO_AUSENTE


async def test_los_elementos_obligatorios_se_leen_de_la_columna_de_la_obra(sesion, obra_lista):
    """P-2. **El nombre cambio con el comportamiento**: hasta T3 esto se llamaba
    «se leen del brief de la obra» y era cierto — se sacaban del JSON en bruto de
    la entrevista. Ahora salen de `obra.elementos_obligatorios`.

    Y de una obra que no existe salen cero, que no es lo mismo que cubiertos."""
    assert await elementos_obligatorios_de(sesion, obra_id=obra_lista.obra.id) == (
        "el perro Luna",
        "la bufanda roja",
    )
    assert await elementos_obligatorios_de(sesion, obra_id=9999) == ()


# ---------------------------------------------------------------------------
# El validador de cobertura entra en un catalogo, y por tanto **corre**
# ---------------------------------------------------------------------------


def test_el_validador_de_cobertura_esta_en_un_catalogo_con_su_punto():
    """«Un validador que no esta en el catalogo no corre» (T7). Y el nombre es
    el de `verification.md` §8.1, que es lo que ata el documento al codigo."""
    nombres = [v.nombre for v in CATALOGO_DE_MANUSCRITO]

    assert nombres == ["cobertura_de_personalizacion"]
    for validador in CATALOGO_DE_MANUSCRITO:
        assert validador.punto is PuntoDeEjecucion.PUERTA_G4


def test_cerrar_el_manuscrito_ejecuta_el_catalogo_y_declara_a_quien_ejecuto():
    """Y lo declara, como hace `cruzar_g1a`: lo que no se puede nombrar no se
    puede contar (RF-VAL-01)."""
    from app.features.calidad import HechoUsado

    cierre = cerrar_manuscrito(
        ManuscritoAValidar(
            elementos_obligatorios=("el perro Luna",),
            hechos=(HechoUsado(entidad="Luna", atributo="especie", valor="perro", usado_en=(3,)),),
        )
    )

    assert cierre.validadores_ejecutados == ("cobertura_de_personalizacion",)
    assert cierre.cobertura.completa


def test_el_cierre_suma_lo_que_cubre_cada_validador_y_respeta_el_orden_del_brief():
    """Con un solo validador en el catalogo esto no se puede ver, y por eso se
    prueba con dos: la mutacion «devuelve la cobertura del ultimo» seria
    correcta hoy y falsa el dia que entre el segundo, sin que cayera un test.

    Y el orden de salida es el del **brief**, no el del catalogo: es el orden en
    que el comprador pidio los elementos, y el unico que le dice algo a quien
    lea el informe.
    """
    manuscrito = ManuscritoAValidar(
        elementos_obligatorios=("el perro Luna", "la bufanda roja"), hechos=()
    )
    uno = replace(
        CATALOGO_DE_MANUSCRITO[0],
        nombre="uno",
        comprobar=lambda _: Cobertura(
            cubiertos=(ElementoCubierto(elemento="la bufanda roja", capitulos=(2,)),),
            ausentes=(ElementoAusente(elemento="el perro Luna"),),
        ),
    )
    dos = replace(
        CATALOGO_DE_MANUSCRITO[0],
        nombre="dos",
        comprobar=lambda _: Cobertura(
            cubiertos=(ElementoCubierto(elemento="el perro Luna", capitulos=(5,)),),
            ausentes=(ElementoAusente(elemento="la bufanda roja"),),
        ),
    )

    cierre = cerrar_manuscrito(manuscrito, (uno, dos))

    assert cierre.validadores_ejecutados == ("uno", "dos")
    assert [c.elemento for c in cierre.cobertura.cubiertos] == [
        "el perro Luna",
        "la bufanda roja",
    ]
    assert cierre.cobertura.completa


async def test_la_cobertura_de_la_novela_pasa_por_el_catalogo(sesion, obra_lista):
    """La juntura de T7: la funcion estaba probada y **no la ejecutaba nadie**.

    Se comprueba con un catalogo espia y no mirando el resultado: dos caminos
    distintos —el catalogo o una llamada directa a `cobertura_de_obligatorios`—
    devuelven exactamente lo mismo, asi que el resultado no distingue cual se
    tomo. Lo que distingue es si el catalogo se recorrio.
    """
    vistos: list[ManuscritoAValidar] = []

    def espiar(manuscrito: ManuscritoAValidar):
        vistos.append(manuscrito)
        return CATALOGO_DE_MANUSCRITO[0].comprobar(manuscrito)

    espia = (replace(CATALOGO_DE_MANUSCRITO[0], nombre="espia", comprobar=espiar),)

    cobertura = await cobertura_de_la_novela(sesion, obra_id=obra_lista.obra.id, catalogo=espia)

    assert len(vistos) == 1
    assert vistos[0].elementos_obligatorios == ("el perro Luna", "la bufanda roja")
    assert [a.elemento for a in cobertura.ausentes] == ["el perro Luna", "la bufanda roja"]


# ---------------------------------------------------------------------------
# De punta a punta por HTTP: del brief a los diez capitulos
# ---------------------------------------------------------------------------


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    return _respuestas()


async def test_del_brief_de_ejemplo_sale_una_novela_de_diez_capitulos(cliente, sesion):
    """**`CA-1` entero por HTTP:** entrevista, outline y los diez capitulos.

    Es CU-01 → CU-02 → CU-03 diez veces, con `DobleDeterminista` y sin tocar la
    base por dentro salvo para el hecho de canon del brief, que hoy no tiene
    endpoint (RF-ENT-06 quedo sin cablear en la Fase 1).
    """
    entrevista = cliente.post("/entrevistas").json()
    cliente.post(
        f"/entrevistas/{entrevista['id']}/respuestas",
        json={"respuestas": BRIEF_DE_EJEMPLO},
    )
    cierre = cliente.post(f"/entrevistas/{entrevista['id']}/cerrar")
    assert cierre.status_code == 201
    obra_id = cierre.json()["obra_id"]

    assert cliente.post(f"/obras/{obra_id}/outline").status_code == 201
    sesion.add(
        HechoCanon(
            obra_id=obra_id, entidad="Luna", atributo="especie", valor="perro", origen="brief"
        )
    )
    await sesion.flush()

    lanzada = cliente.post(f"/obras/{obra_id}/novela")
    assert lanzada.status_code == 202
    assert lanzada.json()["desde_el_capitulo"] == 1

    trabajos = (
        (
            await sesion.execute(
                select(Trabajo).where(Trabajo.obra_id == obra_id).order_by(Trabajo.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(trabajos) == 10
    assert [t.estado for t in trabajos] == ["INTEGRADA"] * 10

    # RI-06, «legible por capitulo»: el trabajo dice de que capitulo es y que
    # numero tiene ese capitulo en el outline.
    estado = cliente.get(f"/trabajos/{trabajos[4].id}").json()
    assert estado["capitulo_id"] == trabajos[4].capitulo_id
    assert estado["numero_de_capitulo"] == 5


def test_el_endpoint_de_la_novela_esta_en_el_openapi(cliente):
    """RI-13: el OpenAPI es el contrato del que la spec 002 genera su cliente."""
    openapi = cliente.get("/openapi.json").json()

    assert "post" in openapi["paths"]["/obras/{obra_id}/novela"]
    # RI-06 «legible por capitulo» es contrato, no detalle: el cliente de la
    # spec 002 se genera de aqui, y sin estos dos campos en el modelo no podria
    # decir de que capitulo es el trabajo que muestra.
    trabajo = openapi["components"]["schemas"]["EstadoDelTrabajo"]["properties"]
    assert "capitulo_id" in trabajo
    assert "numero_de_capitulo" in trabajo


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


async def _ids_por_capa(sesion: AsyncSession, capitulo_id: int) -> dict[str, list[str]]:
    """Los identificadores que el Ensamblador guardo, por capa (RF-CTX-09)."""
    fila = (
        await sesion.execute(
            select(Ejecucion.ids_por_capa)
            .join(Trabajo, Trabajo.run_id == Ejecucion.run_id)
            .where(Trabajo.capitulo_id == capitulo_id)
        )
    ).scalar_one()
    return dict(fila) if isinstance(fila, dict) else dict(json.loads(fila))


async def _otra_obra_con_capitulos(sesion: AsyncSession):
    """Una segunda obra con sus diez capitulos, **que ya no numeran como su id**."""
    from app.features.escritura.novela import CapituloDeLaNovela

    obra_id = (
        await sesion.execute(
            text(
                # `elementos_obligatorios` va aqui desde T3: la columna es
                # obligatoria y no admite lista vacia (P-2). Este INSERT es SQL
                # crudo a proposito —prueba que el numero no sale del id— y por
                # eso no lo cubrio el arreglo del modelo.
                "INSERT INTO obra (titulo, genero, tono, nivel_de_calor, "
                "elementos_obligatorios) "
                "VALUES ('Otra', 'romance', 'calido', 1, '[\"un elemento\"]') RETURNING id"
            )
        )
    ).scalar_one()
    capitulos = []
    for n in range(1, 11):
        capitulo_id = (
            await sesion.execute(
                text(
                    "INSERT INTO capitulo (obra_id, numero, titulo, pov_dominante, lugar, "
                    "objetivo, obstaculo, giro_de_valor_previsto, gancho_de_apertura, "
                    "tipo_de_corte_final, extension_objetivo) "
                    "VALUES (:obra_id, :numero, 'x', 'x', 'x', 'x', 'x', 'x', 'x', "
                    "'pregunta', 1200) RETURNING id"
                ),
                {"obra_id": obra_id, "numero": n},
            )
        ).scalar_one()
        capitulos.append(
            CapituloDeLaNovela(capitulo_id=capitulo_id, numero=n, trabajo_id=0, estado="x")
        )
    await sesion.flush()
    return int(obra_id), capitulos


async def _version_vigente(sesion: AsyncSession, capitulo_id: int) -> int:
    """La `version_texto` marcada vigente del capitulo, que es la que la capa de
    continuidad local trae del anterior."""
    return int(
        (
            await sesion.execute(
                text(
                    "SELECT vt.id FROM version_texto AS vt "
                    "JOIN escena AS e ON e.id = vt.escena_id "
                    "WHERE e.capitulo_id = :capitulo_id AND vt.vigente = 1"
                ),
                {"capitulo_id": capitulo_id},
            )
        ).scalar_one()
    )
