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


class CapituloPublicado(BaseModel):
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


class FichaDeLectura(BaseModel):
    """La ficha entera de una tirada: quien es quien, y donde sale.

    Es la **respuesta** de `/lectura/{token}/ficha`, no una fila: `EntradaDeFicha`
    es una entrada suelta y el frontend necesita el tipo del cuerpo completo
    para derivar su cliente.
    """

    model_config = ConfigDict(frozen=True)

    entradas: list[EntradaDeFicha] = Field(default_factory=list)


class DefectoDelCuadro(BaseModel):
    """Un defecto tal y como quedo al publicar, para que la Fase 5 pueda
    clasificarlo despues en preexistente o introducido."""

    model_config = ConfigDict(frozen=True)

    codigo: str
    capitulo: int | None = None
    cita: str = ""


class VersionPublicada(BaseModel):
    """La tirada, **sin** `id` ni `obra_id`.

    El `identificador_publico` no sale aqui: quien lee ya lo tiene, porque es
    por donde entro. Devolverlo otra vez solo lo pondria en un sitio mas -- un
    registro, una captura, un historial del navegador compartido.
    """

    model_config = ConfigDict(frozen=True)

    ordinal: int
    publicada_en: datetime
    dedicatoria: str | None = None
    capitulos: list[CapituloPublicado] = Field(default_factory=list)


class DedicatoriaEntrada(BaseModel):
    """Lo que el comprador escribe para el destinatario (RD-05, R-6).

    Es **entrada**, no salida, y es la unica de este modulo: la dedicatoria
    sale por `VersionPublicadaSalida.dedicatoria`, con la portada, porque ese
    es su unico uso.

    `texto` admite `None` a proposito. R-6 la declara opcional -- un regalo sin
    dedicatoria sigue siendo un regalo --, y quien cierra la entrevista no tiene
    por que distinguir entre «no la escribio» y «la dejo en blanco»: las dos
    cosas significan lo mismo y se normalizan aqui, no en cada llamador.
    """

    model_config = ConfigDict(frozen=True)

    texto: str | None = None

    def limpia(self) -> str | None:
        """El texto sin espacios de borde, o `None` si no queda nada.

        Los tres vacios -- `None`, `""` y `"   "` -- se tratan igual. Guardar una
        fila con tres espacios obligaria a la portada a distinguirla de una
        dedicatoria de verdad, y ese `if` acabaria escrito en dos sitios.
        """
        limpio = (self.texto or "").strip()
        return limpio or None
