"""Cliente de modelo sobre el CLI de Claude Code (D-02, RI-13, RF-ORQ-16).

Es el proveedor real que `ClienteNoConfigurado` reservaba. Llama al CLI `claude`
en modo no interactivo, que usa la credencial de la cuenta: no hay clave de API
en este entorno, y esa fue la razón de toda la revisión D-02.

**Los agentes corren sin herramientas** (RF-ORQ-16). Se pasa la lista completa a
`--disallowed-tools`, así que el agente no puede leer ficheros, escribir, ni
salir a la red. La invariante deja de depender de que el prompt lo pida y pasa a
depender del proceso que lo lanza, que es lo que `verification.md` §3 llama
supresión de alcance en vez de *sandbox*.

**Se sustituye el prompt de sistema del CLI.** Sin `--system-prompt`, cada
llamada arrastra el contexto entero de Claude Code —unos 52.000 tokens— y se
factura como creación de caché: medido, 0,52 USD por llamada trivial. Con prompt
propio y sin herramientas baja a 0,057. En un capítulo de cincuenta llamadas eso
es la diferencia entre 26 USD y 3.

**Lo que el CLI añade no cuenta contra el presupuesto de §2.1.** Ese presupuesto
acota *nuestro* paquete; el contexto propio del proveedor es suyo y va aparte.
Conviene saberlo al leer una factura y no confundirlo con un desbordamiento.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass

from app.commons.llm.cliente import RespuestaDeModelo


class ErrorTransitorioDeProveedor(RuntimeError):
    """El CLI fallo en **esta** llamada: 5xx, limite de tasa, salida ilegible.

    No es `FalloDeProveedor`, y la distincion es la que hace alcanzable
    RNF-FIA-02. `con_reintentos` reintenta esto con espera creciente y solo
    despues de tres intentos lo convierte en `FalloDeProveedor`; si el cliente
    lanzara `FalloDeProveedor` de entrada, el reintento lo trataria como ya
    agotado y no reintentaria nunca. Eso es exactamente lo que paso en la
    primera corrida real: el requisito estaba implementado y era inalcanzable.

    Lleva la salida de error del CLI, porque sin ella un fallo de proveedor es
    indistinguible de una cuota agotada o de un prompt demasiado largo.
    """


# RF-ORQ-16: ninguna de estas llega al agente narrativo.
HERRAMIENTAS_PROHIBIDAS = (
    "Bash",
    "Read",
    "Write",
    "Edit",
    "NotebookEdit",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "Task",
    "TodoWrite",
    "SlashCommand",
)

SISTEMA_POR_DEFECTO = (
    "Eres un generador de texto dentro de un sistema de escritura de novela. "
    "Recibes un encargo completo y devuelves exactamente lo que se te pide, sin "
    "preambulo, sin explicaciones y sin preguntas. No tienes herramientas ni "
    "acceso a ficheros: todo lo que necesitas esta en el mensaje."
)


@dataclass(frozen=True)
class ClienteDeClaudeCode:
    """Una llamada, un proceso. Sin estado entre llamadas (§4: los agentes no
    tienen memoria; la memoria son los almacenes)."""

    # Sin valor por defecto (P-106, RI-21). Con uno, quien olvida pasarlo se
    # lleva un modelo en silencio y la factura o la calidad cambian sin que
    # nadie lo haya decidido. El ajuste `modelo` lo inyecta P-111.
    modelo: str
    sistema: str = SISTEMA_POR_DEFECTO
    plazo_s: int = 600

    @staticmethod
    def _ejecutable() -> list[str]:
        """Resuelve el CLI. En Windows es un `.cmd` de npm, y CreateProcess no
        sabe ejecutarlo: hay que pasarlo por `cmd /c`. Sin esto, `subprocess`
        falla con «no se encuentra el archivo» aunque el comando exista en el
        PATH y funcione desde la terminal."""
        ruta = shutil.which("claude")
        if ruta is None:
            raise ErrorTransitorioDeProveedor("no se encuentra el CLI `claude`")
        if ruta.lower().endswith((".cmd", ".bat")):
            return ["cmd", "/c", ruta]
        return [ruta]

    def generar(self, prompt: str) -> RespuestaDeModelo:
        # El prompt va por **entrada estandar**, no como argumento. Un paquete
        # de contexto puede acercarse a 100.000 tokens y la linea de comandos de
        # Windows se corta en 8.191 caracteres; ademas `cmd /c` reinterpreta
        # comillas y saltos de linea, que en prosa aparecen constantemente.
        orden = [
            *self._ejecutable(),
            "-p",
            "--model",
            self.modelo,
            "--system-prompt",
            self.sistema,
            "--output-format",
            "json",
            "--disallowed-tools",
            *HERRAMIENTAS_PROHIBIDAS,
        ]
        try:
            proceso = subprocess.run(
                orden,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.plazo_s,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as error:
            raise ErrorTransitorioDeProveedor("el CLI agoto el plazo") from error

        if proceso.returncode != 0:
            raise ErrorTransitorioDeProveedor(
                f"el CLI devolvio {proceso.returncode}: "
                f"{(proceso.stderr or proceso.stdout or '').strip()[:400]}"
            )

        try:
            datos = json.loads(proceso.stdout)
        except json.JSONDecodeError as error:
            raise ErrorTransitorioDeProveedor(
                f"salida ilegible: {proceso.stdout.strip()[:400]}"
            ) from error

        uso = datos.get("usage", {})
        return RespuestaDeModelo(
            texto=str(datos.get("result", "")),
            # La entrada real incluye lo que el CLI cachea; se suma para que
            # `ejecucion` registre lo que de verdad se pago (RI-14).
            tokens_entrada=(
                int(uso.get("input_tokens", 0))
                + int(uso.get("cache_creation_input_tokens", 0))
                + int(uso.get("cache_read_input_tokens", 0))
            ),
            tokens_salida=int(uso.get("output_tokens", 0)),
            modelo=self.modelo,
            parametros={
                "coste_usd": datos.get("total_cost_usd"),
                "session_id": datos.get("session_id"),
                "stop_reason": datos.get("stop_reason"),
            },
        )
