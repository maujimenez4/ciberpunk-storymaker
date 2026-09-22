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
import subprocess
from dataclasses import dataclass

from app.commons.errors import FalloDeProveedor
from app.commons.llm.cliente import RespuestaDeModelo

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

    modelo: str = "haiku"
    sistema: str = SISTEMA_POR_DEFECTO
    plazo_s: int = 600

    def generar(self, prompt: str) -> RespuestaDeModelo:
        orden = [
            "claude",
            "-p",
            prompt,
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
                capture_output=True,
                text=True,
                timeout=self.plazo_s,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as error:
            raise FalloDeProveedor(intentos=1) from error

        if proceso.returncode != 0:
            raise FalloDeProveedor(intentos=1)

        try:
            datos = json.loads(proceso.stdout)
        except json.JSONDecodeError as error:
            raise FalloDeProveedor(intentos=1) from error

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
