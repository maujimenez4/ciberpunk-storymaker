"""El ciclo de una escena: reparación dirigida, escalado y reentrada.

RF-ORQ-02, RF-ORQ-07, RF-ORQ-08, RF-ORQ-15 a RF-ORQ-18; `architecture.md` §3.1 y
§8.3.

**Topología en estrella** (§3.1, punto 1). El orquestador invoca a un agente,
recibe su salida, la persiste y decide el siguiente. Ningún agente llama a otro:
una cadena de agentes que se invocan entre sí hace imposible saber quién
introdujo un defecto, y este fichero es el único sitio donde se decide el orden.

**La reparación lleva el defecto concreto con su cita** (RF-ORQ-08). Un reintento
genérico —«mejóralo»— degrada el texto casi siempre, porque el modelo no sabe
qué arreglar y reescribe lo que ya estaba bien.

**Máximo dos reparaciones** (RF-ORQ-07). Después, humano. El tercer intento
raramente arregla lo que dos no arreglaron, y cada uno cuesta una llamada.
"""

from pydantic import BaseModel, ConfigDict

from app.commons.domain import Reloj
from app.commons.jobs import (
    MAXIMO_DE_REPARACIONES,
    Estado,
    RepositorioDeTrabajos,
    Trabajo,
)


class DefectoParaReparar(BaseModel):
    """Lo que viaja al prompt de reparación. Con cita, siempre."""

    model_config = ConfigDict(frozen=True)

    defecto_id: str
    codigo: str
    cita: str
    detalle: str


class ReintentoGenericoProhibido(ValueError):
    """RF-ORQ-08: ninguna ruta reintenta sin defecto adjunto."""


def preparar_reparacion(
    trabajo: Trabajo,
    defectos: list[DefectoParaReparar],
    repositorio: RepositorioDeTrabajos,
    reloj: Reloj,
) -> Trabajo:
    """`VALIDANDO` → `REPARANDO` → `ESCRIBIENDO`, o `ESCALADA` al agotarse.

    El contador sube **aquí** y no al reescribir: lo que se cuenta son las
    reparaciones dirigidas, y contarlas en el otro extremo dejaría un intento sin
    registrar si el proceso cae entre ambos.
    """
    if not defectos:
        raise ReintentoGenericoProhibido(
            "se pidio reparar sin ningun defecto adjunto. Un reintento generico "
            "-«mejoralo»- degrada el texto casi siempre (RF-ORQ-08)"
        )
    if any(not d.cita.strip() for d in defectos):
        raise ReintentoGenericoProhibido(
            "un defecto sin cita no es reparable: el prompt necesita el pasaje, "
            "no una descripcion (RF-CAL-08)"
        )

    en_reparacion = repositorio.transitar(
        trabajo.trabajo_id,
        Estado.REPARANDO,
        reloj,
        causa_fallo="DefectoBloqueante",
        incrementa_intento=True,
    )
    if en_reparacion.intento > MAXIMO_DE_REPARACIONES:  # pragma: no cover
        return repositorio.transitar(trabajo.trabajo_id, Estado.ESCALADA, reloj)
    if en_reparacion.intento == MAXIMO_DE_REPARACIONES:
        return repositorio.transitar(trabajo.trabajo_id, Estado.ESCALADA, reloj)
    return repositorio.transitar(trabajo.trabajo_id, Estado.ESCRIBIENDO, reloj)


def prompt_de_reparacion(prompt_base: str, defectos: list[DefectoParaReparar]) -> str:
    """El defecto concreto y su cita, nunca «mejóralo» (RF-ORQ-08).

    El paquete se reconstruye entero aparte (RF-CTX-12); esto solo añade qué hay
    que arreglar.
    """
    lineas = [
        f"- [{d.codigo}] {d.detalle}\n  Pasaje citado: «{d.cita}»" for d in defectos
    ]
    return (
        f"{prompt_base}\n\n## Defectos que hay que reparar\n"
        + "\n".join(lineas)
        + "\n\nCorrige **solo** esos pasajes. No reescribas lo que no se cita."
    )


def reentrar_tras_edicion_humana(
    trabajo: Trabajo, repositorio: RepositorioDeTrabajos, reloj: Reloj
) -> Trabajo:
    """RF-ORQ-17 y D-08: vuelve a `VALIDANDO`, no a `EXTRAYENDO`.

    Si una edición humana introdujera un CON-01 y entráramos por `EXTRAYENDO`,
    ese error se escribiría en canon, y deshacerlo cuesta un hecho sustitutorio
    más la invalidación de *snapshots*. Revalidar es barato; deshacer no.

    La revalidación **no consume** el contador de RF-ORQ-07: los dos intentos son
    de reparación por el modelo, y aquí ha escrito una persona.
    """
    return repositorio.transitar(trabajo.trabajo_id, Estado.VALIDANDO, reloj)


def aceptar_pese_al_defecto(
    trabajo: Trabajo,
    defecto_id: str,
    quien: str,
    repositorio: RepositorioDeTrabajos,
    reloj: Reloj,
) -> Trabajo:
    """RF-ORQ-18: el autor acepta y queda registrado qué defecto anuló.

    Existe porque un validador puede equivocarse. Sin esta salida, la
    postcondición de CU-04 —nunca indefinidamente en `ESCALADA`— no se puede
    prometer. El registro es la condición: sin él no se avanza.
    """
    if not defecto_id or not quien:
        raise ValueError(
            "aceptar pese a un defecto exige registrar cual y quien lo anulo "
            "(RF-ORQ-18)"
        )
    repositorio.registrar_anulacion(trabajo.trabajo_id, defecto_id, quien, reloj)
    return repositorio.transitar(trabajo.trabajo_id, Estado.EXTRAYENDO, reloj)
