"""El generador del fichero Lean, desde la vista `cronologia`.

Lo que se prueba aqui es **lo que sale**, no que Lean lo acepte: compilar es de
T5, y un test que llamara a `lake build` tardaria segundos y ataria esta suite a
que Lean este instalado. Lo que si se prueba, y es lo que rompe de verdad, es
que el texto emitido sea Lean **valido**: una comilla sin escapar en un nombre
del brief no la ve nadie hasta que la compilacion falla, y para entonces el
mensaje habla de una linea de un fichero que nadie escribio a mano.
"""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.canon.modelos import Evento
from app.features.manuscrito.lean import generar_lean
from app.features.obra.modelos import Obra


async def _evento(
    sesion: AsyncSession,
    obra_id: int,
    *,
    participantes: list[str],
    lugar: str = "la cocina",
    tiempo: str = "dia 1, manana",
) -> Evento:
    evento = Evento(
        obra_id=obra_id,
        descripcion="pasa algo",
        tiempo_historia=tiempo,
        lugar=lugar,
        participantes=participantes,
    )
    sesion.add(evento)
    await sesion.flush()
    return evento


async def test_una_obra_sin_eventos_produce_una_lista_vacia_y_no_falla(
    sesion: AsyncSession, obra: Obra
) -> None:
    """R-3, primera mitad. Distinguir «vacio» de «coherente» es de T5.

    Aqui lo unico que se exige es que no reviente y que emita una lista, porque
    una obra sin cronologia es un estado legitimo -- antes de escribir nada --
    y no un error del generador.
    """
    lean = await generar_lean(sesion, obra.id)
    assert "def eventos : List Evento := []" in lean


async def test_cada_participante_produce_su_propia_fila(sesion: AsyncSession, obra: Obra) -> None:
    """`sinUbicuidad` compara **pares** de filas, y una fila tiene un personaje.

    Un evento con tres participantes son tres filas con el mismo momento y el
    mismo lugar. Emitirlo como una fila con una lista dentro dejaria el
    invariante sin poder compararlas.
    """
    await _evento(sesion, obra.id, participantes=["Marta", "Luna", "Teo"])
    lean = await generar_lean(sesion, obra.id)

    assert lean.count("⟨") == 3


@pytest.mark.parametrize("cuantos", [1, 20])
async def test_produce_lean_valido_con_uno_o_con_veinte_participantes(
    sesion: AsyncSession, obra: Obra, cuantos: int
) -> None:
    """R-4: `participantes` es JSON libre y **nada acota su tamano**."""
    await _evento(sesion, obra.id, participantes=[f"P{i}" for i in range(cuantos)])
    lean = await generar_lean(sesion, obra.id)

    assert lean.count("⟨") == cuantos
    assert lean.count("[") == lean.count("]")


async def test_los_nombres_se_mapean_a_indices_y_no_viajan_en_los_eventos(
    sesion: AsyncSession, obra: Obra
) -> None:
    """La decision del plan: en Lean las pruebas se cierran con `decide`, que
    evalua por fuerza bruta, y comparar cadenas sale mucho mas caro que
    comparar enteros. Los nombres van una vez en su tabla."""
    await _evento(sesion, obra.id, participantes=["Marta"], lugar="la cocina")
    lean = await generar_lean(sesion, obra.id)

    cuerpo = lean.split("def eventos")[1]
    assert "Marta" not in cuerpo
    assert "la cocina" not in cuerpo
    assert '"Marta"' in lean
    assert '"la cocina"' in lean


async def test_el_mismo_nombre_recibe_el_mismo_indice_en_dos_eventos(
    sesion: AsyncSession, obra: Obra
) -> None:
    """Si «Marta» cambiara de indice entre eventos, `sinUbicuidad` no la
    reconoceria como la misma persona y el invariante no detectaria nada."""
    await _evento(sesion, obra.id, participantes=["Marta"], lugar="la cocina")
    await _evento(sesion, obra.id, participantes=["Marta"], lugar="el patio")
    lean = await generar_lean(sesion, obra.id)

    assert lean.count('"Marta"') == 1


async def test_escapa_las_comillas_las_barras_y_conserva_los_acentos(
    sesion: AsyncSession, obra: Obra
) -> None:
    """Los nombres vienen del brief: «O'Shea», «Begoña» y una comilla doble en
    el nombre de un bar son entradas legitimas, no casos raros.

    La apostrofe **no** se escapa -- en Lean no delimita cadenas -- y los
    acentos tampoco: Lean 4 lee UTF-8. Lo que rompe es la comilla doble y la
    barra invertida, y son las dos que se comprueban.
    """
    await _evento(
        sesion,
        obra.id,
        participantes=["O'Shea", "Begoña"],
        lugar='el "bar" de C:\\Norte',
    )
    lean = await generar_lean(sesion, obra.id)

    assert r"\"bar\"" in lean
    assert r"C:\\Norte" in lean
    assert "O'Shea" in lean
    assert "Begoña" in lean


async def test_el_fichero_generado_es_el_mismo_dos_veces(sesion: AsyncSession, obra: Obra) -> None:
    """`CLAUDE.md` §3 punto 6: cualquier ejecucion debe poder reproducirse.

    Un generador que ordenara por un conjunto daria ficheros distintos con los
    mismos datos, y entonces «la prueba paso ayer» no diria nada de hoy.
    """
    await _evento(sesion, obra.id, participantes=["Marta", "Luna"])
    await _evento(sesion, obra.id, participantes=["Teo"], lugar="el patio")

    assert await generar_lean(sesion, obra.id) == await generar_lean(sesion, obra.id)


async def test_no_se_mezclan_los_eventos_de_otra_obra(sesion: AsyncSession, obra: Obra) -> None:
    """Una base, muchas obras (P-07). Publicar una y colar la cronologia de
    otra es el fallo que nadie ve hasta que Lean prueba algo de un desconocido."""
    otra = Obra(
        titulo="Otra",
        genero="romance",
        tono="calido",
        nivel_de_calor=1,
        elementos_obligatorios=["lo que pidio el comprador de la otra obra"],
    )
    sesion.add(otra)
    await sesion.flush()

    await _evento(sesion, obra.id, participantes=["Marta"])
    await _evento(sesion, otra.id, participantes=["Ajeno"])
    lean = await generar_lean(sesion, obra.id)

    assert '"Marta"' in lean
    assert "Ajeno" not in lean


async def test_los_participantes_mal_formados_no_rompen_el_fichero(
    sesion: AsyncSession, obra: Obra
) -> None:
    """`participantes` es JSON libre: nada impide que llegue vacio.

    Un evento sin participantes no produce filas -- no hay nadie de quien decir
    donde estaba -- y **no** produce una fila con un hueco, que es lo que
    dejaria el fichero sin compilar.
    """
    await _evento(sesion, obra.id, participantes=[])
    await _evento(sesion, obra.id, participantes=["Marta"])
    lean = await generar_lean(sesion, obra.id)

    assert lean.count("⟨") == 1


async def test_el_momento_declara_que_no_es_tiempo_de_historia(
    sesion: AsyncSession, obra: Obra
) -> None:
    """**El aviso que impide que T5 pruebe algo falso.**

    `tiempo_historia` es `String(120)` -- «dia 1, manana» -- y no hay en el
    esquema ninguna magnitud ordenable de tiempo de historia. El indice que
    emite el generador ordena por aparicion, que es **orden de discurso**: en un
    salto atras, el discurso avanza y el tiempo de historia retrocede.

    Asi que un `ordenTemporal` sobre este campo no comprueba el invariante 1 de
    §5c: comprueba que el discurso avanza, que es cierto por construccion. El
    fichero lo dice en su cabecera para que nadie lo descubra despues de haber
    escrito la prueba.
    """
    await _evento(sesion, obra.id, participantes=["Marta"], tiempo="dia 1, manana")
    lean = await generar_lean(sesion, obra.id)

    assert "orden de aparicion" in lean
    assert "no es tiempo de historia" in lean


async def test_los_momentos_conservan_su_texto_original(sesion: AsyncSession, obra: Obra) -> None:
    """El indice se compara y el texto se lee: quien audite el fichero tiene que
    poder volver del numero al «dia 1, manana» sin abrir la base."""
    await _evento(sesion, obra.id, participantes=["Marta"], tiempo="dia 3, noche")
    lean = await generar_lean(sesion, obra.id)

    assert '"dia 3, noche"' in lean


async def test_un_participantes_que_no_es_una_lista_no_da_una_fila_por_caracter(
    sesion: AsyncSession, obra: Obra
) -> None:
    """La defensa real de `_participantes_de`, y no la que yo creia.

    La vista devuelve la columna JSON **siempre como texto**, porque la consulta
    es SQL crudo y no pasa por el tipo del ORM: eso ya lo ejercen todos los
    demas tests. Lo que si puede llegar es un valor que, una vez interpretado,
    **no sea una lista** -- aqui una cadena doblemente codificada --. Iterarlo
    emitiria una fila por caracter: compila, y es basura que nadie mirara
    porque el fichero es generado.

    Cero filas y no una excepcion: un evento cuyo `participantes` no se entiende
    no dice de nadie donde estaba, igual que uno vacio.
    """
    await sesion.execute(
        Evento.__table__.insert().values(
            obra_id=obra.id,
            descripcion="pasa algo",
            tiempo_historia="dia 1, manana",
            lugar="la cocina",
            participantes=json.dumps(["Marta", "Luna"]),
            testigos=[],
            causa=[],
            consecuencia=[],
            excluye=[],
        )
    )
    lean = await generar_lean(sesion, obra.id)

    assert lean.count("⟨") == 0
    assert "def eventos : List Evento := []" in lean


def _momentos_de_los_eventos(lean: str) -> list[str]:
    cuerpo = lean.split("def eventos : List Evento :=", 1)[1].split("def exclusiones", 1)[0]
    return [fila.split(",")[0].strip("⟨ ") for fila in cuerpo.split("\n") if "⟨" in fila]


async def test_un_momento_vago_no_es_un_instante_compartido(
    sesion: AsyncSession, obra: Obra
) -> None:
    """Corrida real, obra 3: el Extractor anoto «madrugada» en cinco capitulos
    y Lean vio a la protagonista en nueve sitios a la vez; ni la puerta pudo
    publicar. Un texto sin cifra no identifica un instante: cada evento es el
    suyo, y `sinUbicuidad` no los empareja."""
    await _evento(sesion, obra.id, participantes=["Marta"], tiempo="madrugada", lugar="la cocina")
    await _evento(sesion, obra.id, participantes=["Marta"], tiempo="madrugada", lugar="la playa")

    primero, segundo = _momentos_de_los_eventos(await generar_lean(sesion, obra.id))
    assert primero != segundo


async def test_un_momento_con_cifra_si_es_un_instante_compartido(
    sesion: AsyncSession, obra: Obra
) -> None:
    """La otra mitad: «la noche de San Juan de 1996» (B3) sigue siendo un
    instante, y dos sitios en ella siguen emparejandose."""
    for lugar in ("la hoguera", "el faro"):
        await _evento(
            sesion, obra.id, participantes=["Marta"], tiempo="San Juan de 1996", lugar=lugar
        )

    primero, segundo = _momentos_de_los_eventos(await generar_lean(sesion, obra.id))
    assert primero == segundo
