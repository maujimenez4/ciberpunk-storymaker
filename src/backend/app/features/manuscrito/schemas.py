"""Modelos de salida de la publicacion. Nunca se expone el modelo de la base.

`CLAUDE.md` §6 lo pide y aqui hay un motivo extra: la fila de
`VersionPublicada` lleva `id` y `obra_id`, que son internos, y el
`identificador_publico`, que es **la credencial** que protege la lectura.
Devolver la fila entera repartiria los tres.

Lo que la lectura necesita entra por el token (T9 lo usa como llave de ruta) y
lo que sale son estos modelos, sin identificadores internos.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CapituloDelIndice(BaseModel):
    """Una entrada del indice de la 002 (`RF-IND-01`, `RF-IND-02`).

    `cambiado` viene del backend calculado y no se recalcula en el navegador: el
    navegador solo tiene delante la tirada que esta leyendo, y `cambiado`
    compara con la anterior.
    """

    model_config = ConfigDict(frozen=True)

    numero: int
    titulo: str | None = None
    cambiado: bool = False


class EntradaDeFicha(BaseModel):
    """Quien es quien, con los capitulos en que aparece (`RF-PUB-05`)."""

    model_config = ConfigDict(frozen=True)

    nombre: str
    tipo: str
    descripcion: str = ""
    capitulos: list[int] = Field(default_factory=list)


class DefectoDelCuadro(BaseModel):
    """Un defecto tal y como quedo al publicar, para que la Fase 5 pueda
    clasificarlo despues en preexistente o introducido."""

    model_config = ConfigDict(frozen=True)

    codigo: str
    capitulo: int | None = None
    cita: str = ""


class VersionPublicadaSalida(BaseModel):
    """La tirada, **sin** `id` ni `obra_id`.

    El `identificador_publico` no sale aqui: quien lee ya lo tiene, porque es
    por donde entro. Devolverlo otra vez solo lo pondria en un sitio mas -- un
    registro, una captura, un historial del navegador compartido.
    """

    model_config = ConfigDict(frozen=True)

    ordinal: int
    publicada_en: datetime
    dedicatoria: str | None = None
    capitulos: list[CapituloDelIndice] = Field(default_factory=list)
