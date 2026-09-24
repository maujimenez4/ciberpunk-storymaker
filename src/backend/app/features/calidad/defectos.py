"""La comprobacion de **forma** de un defecto, antes de la puerta.

RF-VAL-07 y `architecture.md` §8.3. El Continuista es un modelo, asi que lo que
afirma es una senal con varianza: lo que hace mecanica a G1a es el **contraste**,
no la extraccion. Por eso, antes de que un defecto llegue a la puerta, se
comprueba su forma **en codigo y sin volver a llamar al modelo**:

1. El `codigo` pertenece a la taxonomia de `definitions.md` §8.
2. La `cita` es subcadena exacta del texto **en el desplazamiento declarado**
   (regla de dominio 8, axioma 11).
3. Si el `codigo` es `CAN-01`, el `hecho_canon_id` existe en el grafo de canon
   (regla de dominio 9, axioma 12).
4. Si el `codigo` es `CON-03`, el `evento_id` esta en la proyeccion de
   `estado_en_t` **y su `sabe_desde` es anterior a este capitulo** (regla de
   dominio 2). Es P-4: hasta hoy `CON-03` era una opinion cuya forma se
   comprobaba y cuyo fondo no.

Un defecto que no pasa las cuatro esta **mal formado**: no bloquea, no consume
reintento y no llega al prompt de reparacion. **Tampoco se descarta en
silencio**: sale contado y con su motivo, porque la tasa de defectos mal
formados es hoy la unica senal directa de que quien los emite esta afirmando
cosas que no estan en el texto.

**Lo que esta comprobacion NO compra**, y conviene no ampliarlo al leerlo:
desaparece el defecto bien formado con la cita equivocada, y un `CAN-01` deja de
poder apuntar a un hecho inventado. No dice **nada** sobre el defecto que nadie
vio: el falso negativo sigue sin medirse y ninguna comprobacion de forma lo
alcanza.
"""

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from enum import StrEnum

from app.features.calidad.schemas import ConocimientoEnT, Defecto

CODIGOS_DE_LA_TAXONOMIA: frozenset[str] = frozenset(
    {
        "CAN-01",
        "CON-01",
        "CON-02",
        "CON-03",
        "VOZ-01",
        "VOZ-02",
        "VOZ-03",
        "PRO-01",
        "PRO-02",
        "EST-01",
        "EST-02",
        "GEN-01",
        "GEN-02",
        "SEG-01",
        "SEG-02",
        "PER-01",
        "PER-02",
        "PER-03",
        "CFG-01",
        "CFG-02",
        "REN-01",
    }
)
"""Copiada literal de la tabla de `definitions.md` §8. **Fuera de la taxonomia
no es un defecto**: es texto que alguien devolvio con forma de defecto."""

CODIGO_QUE_EXIGE_EVENTO = "CON-03"
"""«Un personaje sabe lo que no deberia» (`definitions.md` §8). Su contraste
es el ledger, y el `evento_id` es lo que lo hace comprobable."""

CODIGO_QUE_EXIGE_HECHO_DE_CANON = "CAN-01"
"""El unico con `hecho_canon_id` obligatorio (`definitions.md` §8, cardinalidad
0..1 con la nota «obligatorio si `codigo` es `CAN-01`»)."""


class MotivoMalFormado(StrEnum):
    """Por que un defecto no llega a la puerta. Se guarda **con** el defecto:
    «mal formado» a secas no deja corregir a quien lo emitio."""

    CODIGO_FUERA_DE_LA_TAXONOMIA = "codigo_fuera_de_la_taxonomia"
    CITA_FUERA_DE_SU_DESPLAZAMIENTO = "cita_fuera_de_su_desplazamiento"
    HECHO_DE_CANON_QUE_NO_EXISTE = "hecho_de_canon_que_no_existe"
    CONOCIMIENTO_NO_ANTERIOR = "conocimiento_no_anterior"


@dataclass(frozen=True, slots=True)
class DefectoMalFormado:
    """El defecto entero y su motivo. No se tira: se cuenta."""

    defecto: Defecto
    motivo: MotivoMalFormado


@dataclass(frozen=True, slots=True)
class DefectosClasificados:
    """Los dos montones, separados y ambos presentes.

    Que los mal formados vengan en el mismo resultado —y no se pierdan por el
    camino— es lo que hace que «se cuenta aparte» sea comprobable.
    """

    bien_formados: tuple[Defecto, ...]
    mal_formados: tuple[DefectoMalFormado, ...]


@dataclass(frozen=True, slots=True)
class ContrasteDeConocimiento:
    """La proyeccion de `estado_en_t` y **el punto del discurso desde el que se
    mira**, juntos.

    Van en la misma estructura porque por separado no dicen nada: «lo sabe desde
    la siete» solo es un defecto si el capitulo que se juzga es anterior a la
    siete, y un `orden_discurso` suelto no tiene contra que compararse. Es la
    misma decision que tomo `CapituloAContrastar` con el grafo, y por el mismo
    motivo: que no se pueda llamar al contraste a medias por descuido.
    """

    conocimiento: tuple[ConocimientoEnT, ...]
    orden_discurso: int

    def respalda(self, evento_id: str | None) -> bool:
        """`True` si el ledger sostiene un `CON-03` sobre ese evento.

        Lo sostiene cuando el evento **esta en la proyeccion** y su `sabe_desde`
        es **anterior** a este capitulo: solo entonces hay algo ya establecido en
        la obra que el capitulo pueda estar usando antes de tiempo.

        Las tres formas de no sostenerlo, y ninguna es un descarte en silencio:

        - **No esta en la proyeccion.** Lo que no esta en la lista no existe para
          el Continuista, igual que un `hecho_canon_id` inventado.
        - **Su `sabe_desde` es nulo.** El ledger no situa ese evento en el
          discurso, y de lo que no esta situado no se puede decir que sea
          anterior.
        - **Su `sabe_desde` no es anterior.** El conocimiento llega despues del
          capitulo que se juzga: todavia no hay nada establecido con lo que
          chocar, y el defecto —si lo hay— es de la escena que llega luego.

        `evento_id` nulo tampoco lo sostiene: un `CON-03` sin evento no senala
        nada, exactamente como un `CAN-01` sin hecho.
        """
        if evento_id is None:
            return False
        return any(
            fila.evento_id == evento_id
            and fila.sabe_desde is not None
            and fila.sabe_desde < self.orden_discurso
            for fila in self.conocimiento
        )


def comprobar_forma(
    defecto: Defecto,
    texto: str,
    hechos_de_canon: Collection[str],
    contraste: ContrasteDeConocimiento | None = None,
) -> MotivoMalFormado | None:
    """`None` si el defecto esta bien formado; el motivo si no.

    `texto` es el de la `VersionDeTexto` que el defecto senala. `hechos_de_canon`
    son los identificadores que **existen** en el grafo: una proyeccion, no la
    tabla (ver la cabecera de `schemas.py`).

    **`contraste` nulo no significa «no hay conocimiento»: significa que esta
    llamada no lo contrasta**, y por eso un `CON-03` la atraviesa con lo que
    decidiera quien si lo tenia. La diferencia importa: si nulo valiera por
    proyeccion vacia, `cruzar_g1a` —que no recibe la vista— convertiria en mal
    formado **todo** `CON-03` que el Continuista ya hubiera respaldado, y el
    contraste de P-4 se perderia justo despues de hacerse.

    Es una asimetria con `CAN-01`, que la puerta si vuelve a comprobar porque
    recibe los hechos, y va escrita para que se vea: mientras `cruzar_g1a` no
    tenga la proyeccion, quien contrasta el conocimiento es el Continuista y
    nadie mas (Desviaciones, T8).
    """
    if defecto.codigo not in CODIGOS_DE_LA_TAXONOMIA:
        return MotivoMalFormado.CODIGO_FUERA_DE_LA_TAXONOMIA

    # Subcadena exacta **en su desplazamiento**, no en cualquier sitio: una cita
    # que aparece dos veces en el capitulo senala un pasaje, no dos.
    inicio, fin = defecto.desplazamiento_inicio, defecto.desplazamiento_fin
    if inicio < 0 or fin > len(texto) or texto[inicio:fin] != defecto.cita:
        return MotivoMalFormado.CITA_FUERA_DE_SU_DESPLAZAMIENTO

    if defecto.codigo == CODIGO_QUE_EXIGE_HECHO_DE_CANON and (
        defecto.hecho_canon_id is None or defecto.hecho_canon_id not in hechos_de_canon
    ):
        return MotivoMalFormado.HECHO_DE_CANON_QUE_NO_EXISTE

    # Regla de dominio 2, y el fondo de `CON-03` que P-4 dice que falta: no se
    # cree que un personaje sepa lo que no deberia hasta que el ledger situe ese
    # conocimiento antes del capitulo que se juzga.
    if (
        defecto.codigo == CODIGO_QUE_EXIGE_EVENTO
        and contraste is not None
        and not contraste.respalda(defecto.evento_id)
    ):
        return MotivoMalFormado.CONOCIMIENTO_NO_ANTERIOR

    return None


def clasificar(
    defectos: Iterable[Defecto],
    texto: str,
    hechos_de_canon: Collection[str],
    contraste: ContrasteDeConocimiento | None = None,
) -> DefectosClasificados:
    """Separa los dos montones conservando el orden de llegada."""
    bien_formados: list[Defecto] = []
    mal_formados: list[DefectoMalFormado] = []
    for defecto in defectos:
        motivo = comprobar_forma(defecto, texto, hechos_de_canon, contraste)
        if motivo is None:
            bien_formados.append(defecto)
        else:
            mal_formados.append(DefectoMalFormado(defecto=defecto, motivo=motivo))
    return DefectosClasificados(tuple(bien_formados), tuple(mal_formados))
