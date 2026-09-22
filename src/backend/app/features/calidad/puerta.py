"""Comprobación de forma y puerta G1a (RF-CAL-09 a RF-CAL-11, `architecture.md` §8.3).

**Por qué existe la comprobación de forma.** El Continuista es un modelo, así que
lo que afirma es una señal con varianza. Lo que hace *mecánica* a G1a es el
**contraste**, no la extracción (`verification.md` §6.2). Antes de que un defecto
llegue a la puerta se comprueba su forma, en código y sin volver a llamar al
modelo:

1. El `codigo` pertenece a la taxonomía cerrada de `definitions.md` §8.
2. La `cita` es subcadena exacta de la `VersionDeTexto` que señala, en el
   desplazamiento declarado (axioma 11).
3. Si el `codigo` es `CAN-01`, el `hecho_canon_id` existe en el grafo (axioma 12).

Lo que esto compra es concreto y conviene no ampliarlo: **desaparece la categoría
del defecto bien formado con la cita equivocada**, y un `CAN-01` deja de poder
apuntar a un hecho inventado. No dice nada sobre el defecto que el Continuista
**no vio**: el falso negativo sigue sin medirse.

Un defecto mal formado no bloquea, no consume reintento y **no se descarta en
silencio**: se registra, porque su tasa es hoy la única señal directa de que el
Continuista afirma cosas que no están en el texto (§9).
"""

from pydantic import BaseModel, ConfigDict

from app.features.calidad.defectos import CodigoDeDefecto, Defecto


class VeredictoDeG1a(BaseModel):
    """Lo que la puerta devuelve al orquestador."""

    model_config = ConfigDict(frozen=True)

    bloquean: list[Defecto]
    no_bloquean: list[Defecto]
    mal_formados: list[Defecto]

    @property
    def aprobada(self) -> bool:
        return not self.bloquean

    @property
    def tasa_de_mal_formados(self) -> float:
        """§9 y `verification.md` §6.3: la única señal que hoy mide al Continuista."""
        total = len(self.bloquean) + len(self.no_bloquean) + len(self.mal_formados)
        return len(self.mal_formados) / total if total else 0.0


def comprobar_forma(defecto: Defecto, texto: str, hechos_de_canon: set[str]) -> Defecto:
    """RF-CAL-11. Devuelve el defecto, marcado como mal formado si no pasa."""
    motivos: list[str] = []

    if defecto.codigo not in set(CodigoDeDefecto):  # pragma: no cover
        motivos.append("codigo fuera de la taxonomia")

    trozo = texto[defecto.desplazamiento_inicio : defecto.desplazamiento_fin]
    if trozo != defecto.cita:
        motivos.append(
            f"la cita no coincide con el texto en [{defecto.desplazamiento_inicio}:"
            f"{defecto.desplazamiento_fin}]: dice {trozo!r} y afirma {defecto.cita!r}"
        )

    if defecto.codigo is CodigoDeDefecto.CAN_01:
        if not defecto.hecho_canon_id:
            motivos.append("CAN-01 sin hecho_canon_id (axioma 12)")
        elif defecto.hecho_canon_id not in hechos_de_canon:
            motivos.append(
                f"CAN-01 apunta a un hecho que no existe: {defecto.hecho_canon_id}"
            )

    if not motivos:
        return defecto
    return defecto.model_copy(
        update={
            "bien_formado": False,
            "detalle": f"{defecto.detalle} | mal formado: {'; '.join(motivos)}".strip(
                " |"
            ),
        }
    )


def pasar_g1a(
    defectos: list[Defecto], texto: str, hechos_de_canon: set[str]
) -> VeredictoDeG1a:
    """RF-CAL-09: bloquean los mecánicos. **G1b no se implementa en la v1.**

    Los defectos de juicio —voz, prosa, ruptura por malentendido— se registran y
    dejan pasar, porque necesitan al Crítico con una rúbrica calibrada y eso es
    la fase 4. Fingir que la función dramática se comprueba mecánicamente sería
    peor que declararla pendiente.
    """
    comprobados = [comprobar_forma(d, texto, hechos_de_canon) for d in defectos]
    return VeredictoDeG1a(
        bloquean=[d for d in comprobados if d.bloquea_g1a()],
        no_bloquean=[d for d in comprobados if d.bien_formado and not d.bloquea_g1a()],
        mal_formados=[d for d in comprobados if not d.bien_formado],
    )
