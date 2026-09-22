"""P-46, P-47 y P-57: de los almacenes a las capas.

RF-CTX-07, RF-CTX-08 y `architecture.md` §4.2, §4.6, §4.8.
"""

from app.features.contexto import (
    MUESTRAS_ANCLA,
    ORIGEN,
    Capa,
    recolectar,
)


class AlmacenesDeMentira:
    """Cada método devuelve algo reconocible, para poder afirmar **de dónde**
    salió cada capa y no solo que tenga contenido."""

    def __init__(self, candidatos: dict[str, str] | None = None) -> None:
        self.candidatos = (
            candidatos
            if candidatos is not None
            else {
                "f1": "el taller bajo la lluvia",
                "f2": "las monedas del cajon",
            }
        )
        self.tope_pedido: int | None = None

    def biblia_y_discurso(self, escena_id: str) -> list[str]:
        return ["de la biblia"]

    def outline_del_capitulo(self, escena_id: str) -> list[str]:
        return ["beat cercano", "beat lejano"]

    def canon_relevante(self, escena_id: str) -> list[tuple[str, bool]]:
        return [("Ada tiene los ojos verdes", True), ("Noe vive lejos", False)]

    def estado_en_t(self, escena_id: str) -> list[tuple[str, bool]]:
        return [("Ada sabe lo del muro", True), ("Noe supo algo hace mucho", False)]

    def escena_anterior_integra(self, escena_id: str) -> str | None:
        return "TEXTO INTEGRO DE LA ESCENA N-1"

    def resumen_de_la_penultima(self, escena_id: str) -> str | None:
        return "resumen de la N-2"

    def fragmentos_candidatos(self, escena_id: str, tope: int) -> dict[str, str]:
        self.tope_pedido = tope
        return dict(self.candidatos)

    def muestras_ancla(self, escena_id: str, cuantas: int) -> list[str]:
        return [f"ancla {i}" for i in range(cuantas)]

    def instruccion(self, escena_id: str) -> list[str]:
        return ["la ficha de escena"]


class OrdenadorEspia:
    """Registra qué candidatos vio. Es lo que permite comprobar el **orden** de
    la recuperación híbrida, que es lo que RF-CTX-07 exige de verdad."""

    def __init__(self) -> None:
        self.vio: dict[str, str] = {}

    def ordenar(self, consulta: str, candidatos: dict[str, str], k: int) -> list[str]:
        self.vio = dict(candidatos)
        return list(candidatos)[::-1]


# --- P-46: cada capa sale del almacén que le corresponde ---------------------


def test_todas_las_capas_con_origen_declarado_se_llenan() -> None:
    """§4.8. Si alguna se quedara sin origen, el ensamblado seguiría y el
    Escritor escribiría a ciegas esa parte."""
    capas = recolectar("es1", AlmacenesDeMentira(), OrdenadorEspia(), "consulta")

    assert set(capas) == set(ORIGEN)
    for capa in ORIGEN:
        assert not capas[capa].esta_vacia, f"{capa.value} llego vacia"


def test_cada_capa_trae_lo_de_su_almacen() -> None:
    capas = recolectar("es1", AlmacenesDeMentira(), OrdenadorEspia(), "consulta")

    assert "de la biblia" in capas[Capa.CONSTITUCIONAL].texto
    assert "beat cercano" in capas[Capa.ESTRUCTURAL].texto
    assert "ojos verdes" in capas[Capa.CANON_RELEVANTE].texto
    assert "sabe lo del muro" in capas[Capa.ESTADO_EN_T].texto
    assert "la ficha de escena" in capas[Capa.INSTRUCCION].texto


def test_el_canon_cede_antes_a_los_mencionados_que_a_los_presentes() -> None:
    """§2.1: «personajes mencionados, no presentes»."""
    capas = recolectar("es1", AlmacenesDeMentira(), OrdenadorEspia(), "consulta")

    descartada = capas[Capa.CANON_RELEVANTE].descartar_menos_importante()

    assert descartada is not None
    assert "mencionado" in descartada.etiqueta


def test_el_estado_cede_antes_lo_antiguo_que_lo_reciente() -> None:
    """§2.1: «conocimientos antiguos ya usados»."""
    capas = recolectar("es1", AlmacenesDeMentira(), OrdenadorEspia(), "consulta")

    descartada = capas[Capa.ESTADO_EN_T].descartar_menos_importante()

    assert descartada is not None
    assert "antiguo" in descartada.etiqueta


# --- P-47: la N-1 íntegra y la N-2 resumida ---------------------------------


def test_la_continuidad_local_lleva_la_n1_integra_y_la_n2_resumida() -> None:
    """§4.2. No es ahorro: la escena inmediatamente anterior es la que el
    Escritor necesita palabra por palabra para encadenar; de la anterior a esa
    basta con qué pasó."""
    capas = recolectar("es1", AlmacenesDeMentira(), OrdenadorEspia(), "consulta")
    texto = capas[Capa.CONTINUIDAD_LOCAL].texto

    assert "TEXTO INTEGRO DE LA ESCENA N-1" in texto
    assert "resumen de la N-2" in texto


def test_la_continuidad_cede_la_n2_antes_que_la_n1() -> None:
    """§2.1: «escena N-2 antes que N-1». Recortar al revés dejaría al Escritor
    sin la escena que más falta le hace."""
    capas = recolectar("es1", AlmacenesDeMentira(), OrdenadorEspia(), "consulta")

    descartada = capas[Capa.CONTINUIDAD_LOCAL].descartar_menos_importante()

    assert descartada is not None
    assert descartada.etiqueta == "escena N-2 resumida"


# --- P-57: la recuperación híbrida, en su orden ------------------------------


def test_el_ordenador_solo_ve_lo_que_el_filtro_estructural_dejo_pasar() -> None:
    """RF-CTX-07, y es **lo** que el requisito exige de verdad.

    El filtro estructural va primero y hace el trabajo pesado. Si el ordenador
    viera el manuscrito entero, el orden de §4.6 sería decorativo y volveríamos
    a traer escenas parecidas en vez de pertinentes.
    """
    almacenes = AlmacenesDeMentira(candidatos={"f1": "uno", "f2": "dos"})
    espia = OrdenadorEspia()

    recolectar("es1", almacenes, espia, "consulta")

    assert espia.vio == {"f1": "uno", "f2": "dos"}


def test_el_filtro_estructural_recibe_el_tope_de_candidatos() -> None:
    """RNF-REN-04: sin techo, el coste del ensamblado crecería con la obra."""
    almacenes = AlmacenesDeMentira()

    recolectar("es1", almacenes, OrdenadorEspia(), "consulta", tope_candidatos=7)

    assert almacenes.tope_pedido == 7


def test_lo_peor_puntuado_por_el_ordenador_es_lo_primero_que_cede() -> None:
    """§2.1: «resultados de menor puntuación»."""
    almacenes = AlmacenesDeMentira(candidatos={"f1": "primero", "f2": "segundo"})
    capas = recolectar("es1", almacenes, OrdenadorEspia(), "consulta")

    descartada = capas[Capa.MEMORIA_RECUPERADA].descartar_menos_importante()

    assert descartada is not None
    # El espia invierte el orden, asi que el ultimo que devuelve es "f1".
    assert descartada.texto == "primero"


def test_las_muestras_ancla_sobreviven_al_recorte() -> None:
    """RF-CTX-08. Son la contención principal de la deriva de voz: si se
    recortan, el capítulo 20 deja de sonar como el 3."""
    capas = recolectar("es1", AlmacenesDeMentira(), OrdenadorEspia(), "consulta")
    memoria = capas[Capa.MEMORIA_RECUPERADA]

    while len(memoria.piezas) > MUESTRAS_ANCLA:
        memoria.descartar_menos_importante()

    assert all("ancla" in p.etiqueta for p in memoria.piezas)


def test_sin_candidatos_la_capa_recuperada_queda_vacia_y_lo_dice() -> None:
    """Y el ensamblador la rechazara (RF-CTX-14): una capa vacia es fallo del
    almacen que la surte, no algo que se deje pasar."""

    class SinNada(AlmacenesDeMentira):
        def muestras_ancla(self, escena_id: str, cuantas: int) -> list[str]:
            return []

    capas = recolectar("es1", SinNada(candidatos={}), OrdenadorEspia(), "consulta")

    assert capas[Capa.MEMORIA_RECUPERADA].esta_vacia
