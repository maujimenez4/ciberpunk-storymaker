"""Casos de uso de la feature `obra`."""

from pydantic import ValidationError

from app.commons.domain import Reloj
from app.commons.llm import ClienteDeModelo, extraer_json
from app.features.obra.biblia import Biblia, SalidaDeAgenteInvalida, VersionDeBiblia
from app.features.obra.repository import RepositorioDeObras
from app.features.obra.schemas import Brief, ObraCreada


def crear_obra(
    brief: Brief, repositorio: RepositorioDeObras, reloj: Reloj
) -> ObraCreada:
    """CU-01, RF-OBR-01: arrancar una obra desde un brief.

    El reloj entra por parametro y no se llama a `datetime.now()` aqui: es lo
    que hace reproducible cualquier test sobre fechas (RI-13).
    """
    return repositorio.crear(brief, reloj.ahora())


def generar_biblia(
    obra_id: str,
    cliente: ClienteDeModelo,
    prompt: str,
    repositorio: RepositorioDeObras,
    reloj: Reloj,
) -> VersionDeBiblia:
    """RF-OBR-02: el Arquitecto produce la biblia y se guarda como version nueva.

    La salida se valida **antes** de tocar la base de datos. Si no valida, no se
    escribe nada: un paso fallido no deja media biblia guardada, que luego
    parece una biblia pobre en vez de un fallo (RF-ORQ-15).
    """
    respuesta = cliente.generar(prompt)
    try:
        biblia = Biblia.model_validate_json(extraer_json(respuesta.texto))
    except ValidationError as error:
        raise SalidaDeAgenteInvalida(
            f"la salida del Arquitecto no valida contra Biblia: {error}"
        ) from error
    return repositorio.crear_version_de_biblia(obra_id, biblia, reloj.ahora())
