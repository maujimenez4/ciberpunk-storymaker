"""El cliente de modelo real: el **Claude Agent SDK**, ya autenticado (P-08).

P-02 dijo *que* —Anthropic, por consumo de cuenta, **sin clave de API**— y
P-08 dijo *como*: se invoca el SDK del agente, que reutiliza la sesion ya
abierta contra la cuenta. No hay clave que leer de ninguna parte, y eso deja
RF-OBS-07 barato en vez de relajado.

Tres consecuencias, y ninguna es un detalle:

1. **El coste se deriva** (RF-OBS-03). Sin cargo por llamada no hay factura
   que leer, asi que la cifra sale de los tokens y de la tarifa escrita en
   `TARIFAS`. Es una cifra **imputada**: sirve para comparar plantillas y para
   el *tuning*, que es para lo que el encargo la pide. La respuesta del SDK
   trae un `total_cost_usd` propio y **se ignora a proposito**.
2. **La semilla no la admite el proveedor.** Se registra en `Consumo` porque
   `ejecucion` la guarda (RF-OBS-06), pero no hace reproducible la llamada.
   La reproducibilidad de `CLAUDE.md` §3, punto 6, la sostienen la plantilla
   versionada y los IDs recuperados, no la semilla.
3. **Nada de esto se ejerce en la suite.** CA-4 dice que las pruebas corren
   sin red y sin credenciales; `consulta` es el punto por donde el SDK se
   sustituye. La llamada de verdad es una corrida manual declarada en el plan.
"""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from app.commons.llm.cliente import ClienteModelo, Vectorizacion, vectorizar_texto

MODELO_ESCRITOR = "claude-haiku-4-5"
"""Escribe y edita, que es el volumen (P-02)."""

MODELO_JUEZ = "claude-opus-5"
"""Juzga —Critico y Continuista—. Separarlo del escritor es deliberado (P-02)."""


@dataclass(frozen=True)
class Tarifa:
    """Dolares por millon de tokens, **declarada aqui y no consultada**.

    Que este en el repositorio es la mitad de lo que hace auditable el coste:
    una cifra imputada sin tarifa a la vista no se puede rehacer.
    """

    entrada_por_millon: Decimal
    salida_por_millon: Decimal


TARIFAS: dict[str, Tarifa] = {
    MODELO_ESCRITOR: Tarifa(Decimal("1.00"), Decimal("5.00")),
    MODELO_JUEZ: Tarifa(Decimal("5.00"), Decimal("25.00")),
}
"""Tarifa publica de Anthropic por modelo. No cubre lectura ni escritura de
cache, que se facturan a otro precio: hoy no se usa cache de prompt, y cuando
se use hay que ampliar esto y no dar el numero por bueno."""


@dataclass(frozen=True)
class Consumo:
    """Lo que `ejecucion` guarda de una llamada (RF-OBS-06)."""

    modelo: str
    semilla: int
    tokens_entrada: int
    tokens_salida: int
    coste_usd: Decimal


class TarifaDesconocida(Exception):
    """No hay tarifa para ese modelo, y por eso no hay coste.

    Se falla en vez de imputar cero: un cero se guarda, se suma y se publica
    sin que nadie note que el modelo no estaba en la tabla.
    """

    def __init__(self, modelo: str) -> None:
        self.modelo = modelo
        super().__init__(f"No hay tarifa declarada para el modelo {modelo!r}")


class RespuestaVacia(Exception):
    """El proveedor respondio sin un solo bloque de texto.

    Devolver la cadena vacia seria guardar un capitulo en blanco con su
    `run_id` y su coste, y descubrirlo al maquetar el PDF.
    """


class LlamadaRechazada(Exception):
    """El SDK marco la respuesta con un error propio: autenticacion, cuota,
    limite de ritmo. Se propaga con su nombre en vez de devolver texto a
    medias, que es como un fallo de credenciales acaba pareciendo prosa mala.
    """

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(f"El proveedor rechazo la llamada: {motivo}")


Consulta = Callable[..., AsyncIterator[Any]]
"""La forma de `claude_agent_sdk.query`, inyectable para poder probar sin red."""


def coste_derivado(modelo: str, tokens_entrada: int, tokens_salida: int) -> Decimal:
    """RF-OBS-03: el coste sale de los tokens y de la tarifa, no de una factura."""
    tarifa = TARIFAS.get(modelo)
    if tarifa is None:
        raise TarifaDesconocida(modelo)
    bruto = (
        tokens_entrada * tarifa.entrada_por_millon + tokens_salida * tarifa.salida_por_millon
    ) / Decimal(1_000_000)
    return bruto.quantize(Decimal("0.00000001"))


class ClienteClaudeCode(ClienteModelo):
    """Una llamada, un texto. El modelo es parametro y por defecto es el Escritor.

    Construirlo no cuesta nada: no abre proceso, no lee credenciales y no
    importa vocabulario. Lo que arranca el CLI del proveedor es `completar`.
    """

    def __init__(self, modelo: str = MODELO_ESCRITOR, *, consulta: Consulta | None = None) -> None:
        self._modelo = modelo
        self._consulta: Consulta = consulta if consulta is not None else query
        self._ultimo_consumo: Consumo | None = None

    @property
    def modelo(self) -> str:
        return self._modelo

    @property
    def ultimo_consumo(self) -> Consumo | None:
        """Tokens y coste de la ultima llamada, para que `ejecucion` los guarde."""
        return self._ultimo_consumo

    def _opciones(self, modelo: str) -> ClaudeAgentOptions:
        """Un capitulo se escribe con el modelo y con nada mas.

        - `tools` y `allowed_tools` vacios: el Escritor **solo ve el paquete**
          (RF-ESC-01). Una herramienta de lectura le daria acceso a la base de
          datos, y con el se perderia la atribucion de los defectos.
        - `setting_sources=None`: no se cargan ajustes del usuario ni del
          repositorio. Sin esto, el `CLAUDE.md` de este proyecto entraria en el
          prompt de la novela.
        - `verbatim_prompts=True`: el prompt se entrega tal cual, sin expandir
          `@ruta` ni despachar barras. El texto que aporta el comprador es
          contenido no confiable (`CLAUDE.md` §11) y viaja dentro del prompt.
        - `max_turns=1`: una llamada es una llamada. Sin tope, un turno extra
          gasta cuota fuera de todo presupuesto contado.
        """
        return ClaudeAgentOptions(
            model=modelo,
            tools=[],
            allowed_tools=[],
            setting_sources=None,
            verbatim_prompts=True,
            max_turns=1,
        )

    async def completar(self, prompt: str, semilla: int, modelo: str | None = None) -> str:
        """`modelo` decide **esta** llamada; sin el, el que declaro el cliente.

        Es P-02 hecho pedible: el Continuista y el Critico piden `MODELO_JUEZ`
        y el Escritor se queda con `MODELO_ESCRITOR`. Y lo que se guarda en
        `Consumo` -- tarifa incluida -- es el modelo que de verdad se uso: Opus
        cuesta cinco veces mas que Haiku, asi que imputar el coste al del
        constructor mientras se llama a otro produce una cifra falsa que
        RF-OBS-03 usa despues para comparar plantillas.
        """
        elegido = modelo if modelo is not None else self._modelo
        partes: list[str] = []
        uso: dict[str, Any] = {}

        async for mensaje in self._consulta(prompt=prompt, options=self._opciones(elegido)):
            if isinstance(mensaje, AssistantMessage):
                if mensaje.error is not None:
                    raise LlamadaRechazada(str(mensaje.error))
                partes.extend(b.text for b in mensaje.content if isinstance(b, TextBlock))
            elif isinstance(mensaje, ResultMessage):
                if mensaje.is_error:
                    raise LlamadaRechazada(mensaje.subtype)
                uso = mensaje.usage or {}

        tokens_entrada = int(uso.get("input_tokens", 0))
        tokens_salida = int(uso.get("output_tokens", 0))
        self._ultimo_consumo = Consumo(
            modelo=elegido,
            semilla=semilla,
            tokens_entrada=tokens_entrada,
            tokens_salida=tokens_salida,
            coste_usd=coste_derivado(elegido, tokens_entrada, tokens_salida),
        )

        if not partes:
            raise RespuestaVacia(f"El modelo {elegido} no devolvio ningun bloque de texto")
        return "".join(partes)

    def vectorizar(self, texto: str) -> Vectorizacion:
        """El vector del indice, **calculado aqui y no pedido al proveedor**.

        Anthropic no publica un extremo de *embeddings*, y P-02 fija el modelo
        por consumo de cuenta **sin clave de API**: un segundo proveedor seria
        una credencial mas y una dependencia que nadie ha aprobado. Pedirselo
        al modelo en prosa seria peor —cuota por fragmento, y una cifra
        distinta en cada llamada para algo que se guarda y se compara—.

        Asi que esto **no gasta cuota y no abre el SDK**, y esa es la razon de
        que no sea `async`. Lo que da es una senal lexica: ver
        `vectorizar_texto` para lo que eso alcanza y lo que no.
        """
        return vectorizar_texto(texto)
