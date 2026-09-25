"""El Escritor (`CLAUDE.md` §9): del paquete, la prosa. Y no ve nada mas.

Es el unico rol de la cadena que **escribe prosa**, y el unico del que
`architecture.md` §3.5 dice, con esas palabras, que su lectura es «solo el
paquete recibido». Este fichero es donde esa frase se vuelve mecanismo:

- **No importa la base de datos.** Ni `sqlalchemy`, ni `commons/db/`, ni
  ninguna feature que persista. No es disciplina: hay un test que lee el arbol
  de sintaxis de este modulo y falla si aparece alguno.
- **No recibe sesion.** `escribir` toma un `Paquete` y las restricciones que
  viajan con la ficha, y nada mas. Un test le corta la sesion y desmonta el
  motor antes de llamarlo.

**De aqui sale que un defecto sea atribuible** (`CLAUDE.md` §9.1). Si al
Escritor le falta un dato, el fallo es del ensamblado; si tuviera forma de ir a
buscarlo, un hecho que contradice el canon podria venir de cualquier sitio y la
auditoria acusaria a quien escribio de ignorar algo que nunca vio.

**La reparacion nunca es generica.** `CLAUDE.md` §15 prohibe con esas palabras
los reintentos del tipo «mejoralo»: un reintento lleva el defecto concreto con
la cita del pasaje, y la unica forma de construir la seccion de reparacion es
darle defectos. Con la lista vacia, la seccion no existe -- no es una opcion
apagada, es una que no se puede pedir.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from app.commons.llm.cliente import ClienteModelo
from app.features.calidad import Defecto
from app.features.contexto import Paquete
from app.features.escena import RestriccionesDeDiscurso

PLANTILLA_V2 = (Path(__file__).parent / "prompts" / "escritor.v2.md").read_text(encoding="utf-8")

PROMPT_ID = "escritor"
PROMPT_VERSION = "v2"
HASH_DE_PLANTILLA_V2 = sha256(PLANTILLA_V2.encode("utf-8")).hexdigest()
"""Lo que ata la fila de `ejecucion` al fichero sin duplicarlo en cada llamada
(regla de dominio 7). La plantilla **no se edita en sitio**: una version nueva
es `escritor.v2.md` con su propio hash (`CLAUDE.md` §10)."""

MARCA_DE_PLANTILLA = "ESCRITOR"
"""El titulo de la plantilla. Los dobles de test eligen respuesta por subcadena
del prompt, y una constante evita que el test se apoye en una frase que la v2
puede reescribir."""

MARCA_DE_REPARACION = "Reparación dirigida"
"""El encabezado de la seccion que solo existe en un reintento. Es tambien lo
que permite a un doble distinguir la primera llamada de la segunda sin mirar el
contenido de la prosa."""


class ProsaVacia(Exception):
    """El modelo devolvio algo que no es una escena.

    Guardar la cadena vacia seria dejar un capitulo en blanco con su `run_id` y
    su coste, y descubrirlo al maquetar el PDF. Es el mismo criterio que
    `RespuestaVacia` aplica en el cliente real, un escalon mas arriba.
    """


@dataclass(frozen=True, slots=True)
class Reparacion:
    """Un defecto concreto que vuelve al Escritor, **con su cita** (RF-ESC-03).

    Es la forma de `Defecto` que el prompt necesita, no otra clase de defecto:
    `de_defecto` la construye desde el modelo de `calidad`, que es quien los
    emite. `termino_vetado` es el unico campo que `Defecto` no tiene y RF-GUA-03
    exige -- «con el termino concreto» --, porque la cita dice **como aparece en
    el texto** («sangres») y el veto dice **que se prohibio** («sangre»), y las
    dos cosas hacen falta para que el Escritor sepa que no puede volver a usar
    ninguna variante.
    """

    codigo: str
    cita: str
    desplazamiento_inicio: int
    desplazamiento_fin: int
    termino_vetado: str | None = None

    @classmethod
    def de_defecto(cls, defecto: Defecto, *, termino_vetado: str | None = None) -> "Reparacion":
        return cls(
            codigo=defecto.codigo,
            cita=defecto.cita,
            desplazamiento_inicio=defecto.desplazamiento_inicio,
            desplazamiento_fin=defecto.desplazamiento_fin,
            termino_vetado=termino_vetado,
        )

    def como_linea(self) -> str:
        """Una linea por defecto: codigo, pasaje y donde empieza y acaba.

        El desplazamiento va escrito y no solo la cita porque una cita que
        aparece dos veces en el capitulo senala un pasaje, no dos: es la misma
        razon por la que la comprobacion de forma lo exige (regla de dominio 8).

        **EST-02 (extension) es la excepcion:** su pasaje es el capitulo entero,
        y citarlo lo repetia dos veces en el prompt junto a la orden de «dejar
        intacto todo lo demas», que es lo contrario de lo que hace falta. En la
        primera corrida real el reintento paso de 812 a 141 palabras.
        """
        if self.codigo == "EST-02":
            palabras = len(self.cita.split())
            return (
                f"- **EST-02** · **extensión fuera de rango**: el capítulo tiene **{palabras} "
                "palabras** y debe tener **entre 1.000 y 1.500** (unas 1.200). "
                + (
                    f"Te faltan unas {1200 - palabras}: amplía la escena dramatizando más "
                    "—diálogo, gesto, lugar, lo que el punto de vista piensa y no dice— sin "
                    "cambiar lo que ocurre ni añadir hechos nuevos."
                    if palabras < 1000
                    else "Recórtala sin perder lo que ocurre."
                )
            )
        linea = (
            f"- **{self.codigo}** · caracteres {self.desplazamiento_inicio}"
            f"–{self.desplazamiento_fin} · pasaje: «{self.cita}»"
        )
        if self.termino_vetado is not None:
            linea += (
                f" · **palabra vetada: «{self.termino_vetado}»**. No puede aparecer, "
                "ni ella ni ninguna variante suya."
            )
        return linea


def _bloque_de_reparacion(texto_anterior: str | None, reparaciones: Sequence[Reparacion]) -> str:
    """La seccion que solo existe cuando hay defectos concretos que citar.

    Sin defectos devuelve la cadena vacia **aunque llegue el texto anterior**, y
    eso es RF-ESC-03 por construccion: no hay ninguna combinacion de argumentos
    que produzca un «reescribelo mejor».

    El capitulo entero viaja aqui ademas de en la cita, y es un coste conocido:
    hay defectos cuyo pasaje **es** el capitulo —la extension, o la persona
    ausente de toda la narracion— y sin el texto delante no hay nada que
    corregir, solo algo que volver a escribir desde cero.
    """
    if not reparaciones:
        return ""

    lineas = "\n".join(reparacion.como_linea() for reparacion in reparaciones)
    anterior = "" if texto_anterior is None else texto_anterior
    return (
        f"## {MARCA_DE_REPARACION}\n\n"
        "Ya escribiste esta escena y **no pasó la puerta de calidad**. No la escribes otra vez "
        "desde cero: corriges **exactamente** lo que se señala abajo y dejas intacto todo lo "
        "demás. Cada punto lleva su pasaje entre comillas, tal y como está en tu texto.\n\n"
        f"{lineas}\n\n"
        "Lo que escribiste, íntegro:\n\n"
        "<version_anterior>\n"
        f"{anterior}\n"
        "</version_anterior>\n"
    )


def render_escritor(
    plantilla: str,
    paquete_texto: str,
    restricciones: RestriccionesDeDiscurso,
    *,
    texto_anterior: str | None = None,
    reparaciones: Sequence[Reparacion] = (),
) -> str:
    """Rellena la plantilla. Las restricciones duras salen dos veces.

    Al principio y al final, y lo decide **la plantilla**, no esta funcion: el
    centro del prompt es donde mas informacion se pierde (`CLAUDE.md` §10). Lo
    que aqui se garantiza es que la sustitucion sea global, porque un marcador
    repetido sustituido una sola vez dejaria la restriccion dicha una vez.
    """
    sustituciones: Mapping[str, str] = {
        "{{PERSONA}}": restricciones.persona,
        "{{TIEMPO_VERBAL}}": restricciones.tiempo_verbal,
        "{{NIVEL_DE_CALOR}}": str(restricciones.nivel_de_calor),
        "{{PAQUETE}}": paquete_texto,
        "{{REPARACION}}": _bloque_de_reparacion(texto_anterior, reparaciones),
    }
    prompt = plantilla
    for marcador, valor in sustituciones.items():
        prompt = prompt.replace(marcador, valor)
    return prompt


class Escritor:
    """El rol. Una llamada, una escena, y ni una lectura de la base.

    Recibe el `Paquete` ya ensamblado y las `RestriccionesDeDiscurso` que
    **viajan con la ficha** (`features/escena/schemas.py`): no se vuelven a leer
    de la base, que es lo que hace atribuible un defecto de persona o de tiempo
    verbal al prompt que lo produjo y no al estado de hoy.
    """

    def __init__(self, cliente: ClienteModelo, semilla: int = 0) -> None:
        self._cliente = cliente
        self._semilla = semilla

    @property
    def cliente(self) -> ClienteModelo:
        """Para que quien orqueste le pregunte por el consumo de la ultima
        llamada. El agente no lo persiste: no conoce la base."""
        return self._cliente

    async def escribir(
        self,
        paquete: Paquete,
        restricciones: RestriccionesDeDiscurso,
        *,
        texto_anterior: str | None = None,
        reparaciones: Sequence[Reparacion] = (),
    ) -> str:
        """La prosa de la escena, o `ProsaVacia`. Nada mas sale de aqui.

        No valida la persona ni el tiempo verbal del texto: eso lo comprueba
        `calidad` sobre lo devuelto (regla de dominio 10), y quien escribe no
        debe juzgarse a si mismo (`CLAUDE.md` §9.1).
        """
        prompt = render_escritor(
            PLANTILLA_V2,
            paquete.texto,
            restricciones,
            texto_anterior=texto_anterior,
            reparaciones=reparaciones,
        )
        prosa = await self._cliente.completar(prompt, semilla=self._semilla)
        if not prosa.strip():
            raise ProsaVacia("El Escritor devolvio una escena sin una sola palabra")
        return prosa
