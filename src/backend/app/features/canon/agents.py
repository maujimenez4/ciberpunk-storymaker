"""El Extractor: el agente que cierra el bucle y hace crecer la memoria.

Es el ultimo paso del ciclo de `CLAUDE.md` §9.2 y el unico que escribe memoria
de largo plazo. Lee **prosa ya aprobada** y devuelve hechos, eventos, resumen e
hilos; lo que hace con eso —y en que orden— es de `service.py`.

**Tiene dos entradas y dos plantillas**, y conviene decir por que antes de que
parezca un descuido. La escena produce hechos, ledger, resumen e hilos; el
`TextoAportado` produce **solo hechos**, porque no hay escena de la que salga
un evento y sus hechos existian antes del texto (axioma 14 de
`definitions.md` §11). Son dos formatos de salida y dos juegos de restricciones
duras, y `CLAUDE.md` §10 pide repetir las duras al principio y al final: una
sola plantilla con dos formatos alternativos las pondria en el centro, que es
donde mas informacion se pierde. Queda anotado en Desviaciones.

**Lo que entra va SIEMPRE marcado como dato** (`CLAUDE.md` §11, RNF-SEG-03).
No es una precaucion cosmetica: el Extractor es, con el Entrevistador, uno de
los dos roles cuya entrada no controla el sistema.
"""

import json
from hashlib import sha256
from pathlib import Path

from pydantic import ValidationError

from app.commons.llm.cliente import ClienteModelo
from app.commons.llm.json_de_modelo import json_de_modelo
from app.features.canon.schemas import Extraccion, ExtraccionDelBrief
from app.features.obra import HechoDelBrief

_PROMPTS = Path(__file__).parent / "prompts"

PLANTILLA_V1 = (_PROMPTS / "extractor.v1.md").read_text(encoding="utf-8")
PLANTILLA_BRIEF_V1 = (_PROMPTS / "extractor-brief.v1.md").read_text(encoding="utf-8")

PROMPT_ID = "extractor"
PROMPT_VERSION = "v1"
HASH_DE_PLANTILLA_V1 = sha256(PLANTILLA_V1.encode("utf-8")).hexdigest()
"""La plantilla **de la escena**, que es la que corre en el ciclo del capitulo
y la que lleva span (plan 8 T7, P-22.3). La del brief corre al cerrar la
entrevista, sin obra y sin sesion todavia (D-5), y por eso no tiene constante."""

MARCA_PROSA = "prosa"
MARCA_TEXTO_APORTADO = "texto_aportado"


class SalidaMalFormada(Exception):
    """Un agente que devuelve algo fuera de su esquema es un fallo (RF-ORQ-09).

    Se repite desde `features/obra/agents.py` en vez de subir a `commons/`:
    `CLAUDE.md` §5.1 regla 4 dice que se duplica primero y se sube al tercer
    uso real. Este es el segundo.
    """


def sin_etiquetas(texto: str, marca: str) -> str:
    """Quita la etiqueta hasta que quitarla ya no cambie nada.

    Una pasada sola no basta: al borrar el cierre de `</pro</prosa>sa>` se unen
    los dos trozos que lo rodeaban y la etiqueta se vuelve a formar. Se repite
    hasta punto fijo, y termina siempre porque cada vuelta que cambia algo
    acorta la cadena.
    """
    sano = texto
    while True:
        podado = sano.replace(f"</{marca}>", "").replace(f"<{marca}>", "")
        if podado == sano:
            return sano
        sano = podado


def _render(plantilla: str, hueco: str, marca: str, texto: str) -> str:
    if not texto.strip():
        return plantilla.replace(hueco, "")
    return plantilla.replace(hueco, f"<{marca}>\n{sin_etiquetas(texto, marca)}\n</{marca}>")


def render_extractor(plantilla: str, prosa: str) -> str:
    """La prosa entra SIEMPRE marcada como dato (`CLAUDE.md` §11).

    R-8 se apoya en dos propiedades de esta funcion: que la prosa no pueda
    cerrar su etiqueta, y que **lo que rodea a la etiqueta no dependa de la
    prosa**. La segunda es la que hace que un ataque no cambie el prompt, y por
    tanto que no cambie el paquete del capitulo siguiente.
    """
    return _render(plantilla, "{{PROSA}}", MARCA_PROSA, prosa)


def render_extractor_del_brief(plantilla: str, texto_aportado: str) -> str:
    """Lo mismo para el texto del comprador, con la marca que ya usa la entrevista.

    La marca se llama igual que en `features/obra/agents.py` a proposito: es el
    mismo artefacto —el `TextoAportado`— pasando por otro rol, y darle dos
    nombres seria el tipo de deriva de vocabulario que `CLAUDE.md` §2 prohibe.
    """
    return _render(plantilla, "{{TEXTO_APORTADO}}", MARCA_TEXTO_APORTADO, texto_aportado)


class Extractor:
    """El rol, con su cliente inyectado (`CLAUDE.md` §6).

    No toca la base de datos: devuelve formas validadas y quien las escribe es
    `service.py`. Esa separacion es la que hace atribuible un fallo — si falta
    un hecho, es del agente; si esta y no llego al canon, es del servicio.
    """

    def __init__(self, cliente: ClienteModelo, semilla: int = 0) -> None:
        self._cliente = cliente
        self._semilla = semilla

    async def extraer(self, prosa: str) -> Extraccion:
        """De una escena aprobada: hechos, eventos, resumen e hilos."""
        crudo = await self._cliente.completar(
            render_extractor(PLANTILLA_V1, prosa), semilla=self._semilla
        )
        return _validar(Extraccion, crudo)

    async def extraer_del_brief(self, texto_aportado: str) -> list[HechoDelBrief]:
        """Del `TextoAportado`: hechos con `origen: brief` y **sin escena**.

        Cierra el hueco que la Fase 1 dejo declarado. El canon ya sabia
        guardarlos (`registrar_hechos_del_brief`); lo que no existia era quien
        los produjera, asi que RF-ENT-06 estaba a medias y `CA-3` solo cubria
        el prompt.

        Un texto en blanco **no llama al modelo** (R-2): lo que no dice nada no
        se paga, y un `TextoAportado` vacio acabaria produciendo un hecho de
        canon vacio, que es subcadena de cualquier capitulo.

        Devuelve `HechoDelBrief`, que es de `features/obra` y ya tiene la forma
        del documento. No se declara aqui una clase gemela: dos formas del
        mismo concepto divergen.
        """
        if not texto_aportado.strip():
            return []
        crudo = await self._cliente.completar(
            render_extractor_del_brief(PLANTILLA_BRIEF_V1, texto_aportado), semilla=self._semilla
        )
        extraccion = _validar(ExtraccionDelBrief, crudo)
        return [
            HechoDelBrief(
                entidad=hecho.entidad,
                atributo=hecho.atributo,
                valor=hecho.valor,
                confianza=hecho.confianza,
            )
            for hecho in extraccion.hechos
        ]


def _validar[T: (Extraccion, ExtraccionDelBrief)](esquema: type[T], crudo: str) -> T:
    """JSON mal formado y esquema incumplido se cuentan igual: fallo del agente.

    Los dos significan lo mismo para quien llama —no hay extraccion utilizable—
    y distinguirlos obligaria a cada llamador a manejar dos excepciones para
    tomar la misma decision.
    """
    try:
        return esquema.model_validate(json_de_modelo(crudo))
    except (json.JSONDecodeError, ValidationError) as error:
        raise SalidaMalFormada(crudo[:200]) from error
