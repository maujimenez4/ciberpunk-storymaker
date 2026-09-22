"""De los almacenes a las capas (`architecture.md` §4.8 y §4.6).

El Ensamblador **lee** de los almacenes y no escribe en ninguno (§3.5). Aquí vive
esa lectura, y la correspondencia capa ↔ almacén está en un solo sitio a
propósito: si estuviera repartida, una capa podría quedarse sin origen sin que
nada lo notara, y el síntoma sería una escena escrita a ciegas.

**Los almacenes entran como interfaz, no como import de otra feature.** No es
ceremonia: es lo que permite probar el ensamblador —el componente cuyo fallo es
silencioso— sin montar media base de datos, y lo que evita que `contexto` dependa
de `canon` y de `escena` a la vez.
"""

from typing import Protocol

from app.commons.llm import TOPE_DE_CANDIDATOS, OrdenadorSemantico
from app.features.contexto.capas import Capa, CapaEnsamblada, Pieza

# RF-CTX-08. Cuántas muestras ancla de prosa aprobada del mismo POV se inyectan:
# son la contención principal de la deriva estilística, y más de dos empiezan a
# competir con el canon por el presupuesto.
MUESTRAS_ANCLA = 2

# Prioridades de recorte dentro de la continuidad local (§2.1: «escena N-2 antes
# que N-1»). El número no significa nada por sí solo; lo que importa es el orden.
PRIORIDAD_N1 = 90
PRIORIDAD_N2 = 10


class Almacenes(Protocol):
    """Lo que el Ensamblador necesita leer, y nada más.

    Cada método corresponde a **una** capa de §4.8. Ese uno a uno es lo que hace
    comprobable que ninguna capa se quede sin origen.
    """

    def biblia_y_discurso(self, escena_id: str) -> list[str]: ...

    def outline_del_capitulo(self, escena_id: str) -> list[str]: ...

    def canon_relevante(self, escena_id: str) -> list[tuple[str, bool]]:
        """Devuelve `(texto, esta_presente)`. §2.1 recorta primero a los
        personajes **mencionados y no presentes**."""
        ...

    def estado_en_t(self, escena_id: str) -> list[tuple[str, bool]]:
        """Devuelve `(texto, es_reciente)`. §2.1 recorta primero los
        conocimientos antiguos ya usados."""
        ...

    def escena_anterior_integra(self, escena_id: str) -> str | None: ...

    def resumen_de_la_penultima(self, escena_id: str) -> str | None: ...

    def fragmentos_candidatos(self, escena_id: str, tope: int) -> dict[str, str]:
        """**Ya filtrados** por el filtro estructural (§4.6, paso 1)."""
        ...

    def muestras_ancla(self, escena_id: str, cuantas: int) -> list[str]: ...

    def instruccion(self, escena_id: str) -> list[str]: ...


def _piezas(textos: list[str], etiqueta: str) -> list[Pieza]:
    return [
        Pieza(texto=t, prioridad=i, etiqueta=f"{etiqueta}-{i}")
        for i, t in enumerate(textos)
    ]


def recolectar(
    escena_id: str,
    almacenes: Almacenes,
    ordenador: OrdenadorSemantico,
    consulta: str,
    tope_candidatos: int = TOPE_DE_CANDIDATOS,
) -> dict[Capa, CapaEnsamblada]:
    """Construye las siete capas con contenido, cada una de su almacén (§4.8)."""
    capas: dict[Capa, CapaEnsamblada] = {}

    capas[Capa.CONSTITUCIONAL] = CapaEnsamblada(
        capa=Capa.CONSTITUCIONAL,
        piezas=_piezas(almacenes.biblia_y_discurso(escena_id), "biblia"),
    )
    capas[Capa.ESTRUCTURAL] = CapaEnsamblada(
        capa=Capa.ESTRUCTURAL,
        # §2.1: cede primero el detalle de beats lejanos. El outline llega en
        # orden de cercanía, así que la prioridad crece con la posición.
        piezas=_piezas(almacenes.outline_del_capitulo(escena_id), "beat"),
    )
    capas[Capa.CANON_RELEVANTE] = CapaEnsamblada(
        capa=Capa.CANON_RELEVANTE,
        piezas=[
            # §2.1: ceden primero los personajes **mencionados y no presentes**.
            Pieza(
                texto=texto,
                prioridad=50 + i if presente else i,
                etiqueta=f"canon-{'presente' if presente else 'mencionado'}-{i}",
            )
            for i, (texto, presente) in enumerate(almacenes.canon_relevante(escena_id))
        ],
    )
    capas[Capa.ESTADO_EN_T] = CapaEnsamblada(
        capa=Capa.ESTADO_EN_T,
        piezas=[
            # §2.1: ceden primero los conocimientos antiguos ya usados.
            Pieza(
                texto=texto,
                prioridad=50 + i if reciente else i,
                etiqueta=f"estado-{'reciente' if reciente else 'antiguo'}-{i}",
            )
            for i, (texto, reciente) in enumerate(almacenes.estado_en_t(escena_id))
        ],
    )

    # §4.2: la N-1 **íntegra** y la N-2 **resumida**. No es ahorro: la escena
    # inmediatamente anterior es la que el Escritor necesita palabra por palabra
    # para encadenar; de la anterior a esa basta con qué pasó.
    continuidad: list[Pieza] = []
    penultima = almacenes.resumen_de_la_penultima(escena_id)
    if penultima:
        continuidad.append(Pieza(penultima, PRIORIDAD_N2, "escena N-2 resumida"))
    anterior = almacenes.escena_anterior_integra(escena_id)
    if anterior:
        continuidad.append(Pieza(anterior, PRIORIDAD_N1, "escena N-1 integra"))
    capas[Capa.CONTINUIDAD_LOCAL] = CapaEnsamblada(
        capa=Capa.CONTINUIDAD_LOCAL, piezas=continuidad
    )

    capas[Capa.MEMORIA_RECUPERADA] = CapaEnsamblada(
        capa=Capa.MEMORIA_RECUPERADA,
        piezas=_recuperar(escena_id, almacenes, ordenador, consulta, tope_candidatos),
    )
    capas[Capa.INSTRUCCION] = CapaEnsamblada(
        capa=Capa.INSTRUCCION,
        piezas=_piezas(almacenes.instruccion(escena_id), "instruccion"),
    )
    return capas


def _recuperar(
    escena_id: str,
    almacenes: Almacenes,
    ordenador: OrdenadorSemantico,
    consulta: str,
    tope: int,
) -> list[Pieza]:
    """RF-CTX-07 y §4.6, **en este orden**.

    1. Filtro estructural. Lo hace el almacén, y es el que hace el trabajo
       pesado: el ordenador nunca ve el manuscrito entero.
    2. Ordenación semántica sobre lo ya filtrado.
    3. Fusión con recencia.

    El orden no es negociable. Ordenar por parecido sin filtrar antes trae
    escenas parecidas, no pertinentes: una escena de hace veinte capítulos con un
    beso se parece mucho a la actual y no tiene nada que ver con ella.
    """
    candidatos = almacenes.fragmentos_candidatos(escena_id, tope)  # 1
    if not candidatos:
        return []

    ordenados = ordenador.ordenar(consulta, candidatos, k=len(candidatos))  # 2

    # 3. §2.1 recorta primero «resultados de menor puntuación», así que la
    # prioridad decrece con la posición que les dio el ordenador. La recencia
    # entra como desempate: a igual pertinencia, lo reciente pesa más.
    piezas = [
        Pieza(
            texto=candidatos[identificador],
            prioridad=len(ordenados) - posicion,
            etiqueta=f"recuperado-{posicion}",
        )
        for posicion, identificador in enumerate(ordenados)
    ]

    # RF-CTX-08: muestras ancla de prosa aprobada del mismo POV. Van con
    # prioridad alta porque son la contención principal de la deriva de voz: si
    # se recortan, el capítulo 20 deja de sonar como el 3.
    piezas.extend(
        Pieza(texto=muestra, prioridad=1_000 + i, etiqueta=f"ancla-{i}")
        for i, muestra in enumerate(almacenes.muestras_ancla(escena_id, MUESTRAS_ANCLA))
    )
    return piezas
