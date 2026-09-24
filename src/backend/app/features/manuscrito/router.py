"""La superficie de lectura. `RI-08`, `RI-11`, y el contrato con la spec 002.

**Se entra por el token y solo por el token.** La 002 lo fija: «ninguna ruta
lleva el identificador de la obra en claro; el `token` es lo unico que protege
la lectura». Por eso estas rutas no aceptan `obra_id` ni ordinal, y el
identificador publico **no viaja en el cuerpo**: si viajara, protegeria lo que
se devuelve en vez de lo que se pide, que es justo al reves.

Las rutas de publicacion -- las del Autor -- siguen yendo por `obra_id`. Estas
no.

**Un token que no vale da 404 sin decir por que.** Distinguir «esa obra no
existe» de «ese token no es valido» filtraria la existencia de obras ajenas,
que es lo unico que el token protege. Es tambien el caso mas probable de
todos: el enlace se comparte por mensajeria y se corta.

**Los modelos se importan por su modulo, no por su simbolo.** `modelos` y
`schemas` tienen tres nombres iguales -- `VersionPublicada`, `CapituloPublicado`
y `FichaDeLectura` -- y aqui hacen falta los dos lados: `modelos.X` es la fila y
`X` a secas es lo que sale por la API. Escribirlo asi obliga a decir cual es
cual en cada linea.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.sesion import obtener_sesion
from app.features.manuscrito import modelos
from app.features.manuscrito.repository import (
    capitulos_de,
    dedicatoria_de,
    ficha_de,
    texto_publicado,
    titulo_de_obra,
    version_por_token,
    versiones_de,
)
from app.features.manuscrito.schemas import (
    CapituloPublicado,
    EntradaDeFicha,
    FichaDeLectura,
    VersionPublicada,
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]

router = APIRouter(prefix="/lectura", tags=["lectura"])

# El mismo texto para los dos casos, y es deliberado: ver la cabecera.
NO_ENCONTRADO = "No hay nada en este enlace."


async def _version_o_404(sesion: AsyncSession, token: str) -> modelos.VersionPublicada:
    """La tirada del enlace, o un 404 que no dice cual de los dos fallo."""
    version = await version_por_token(sesion, token)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return version


@router.get("/{token}")
async def portada(token: str, sesion: Sesion) -> VersionPublicada:
    """La portada: dedicatoria, indice y nada de prosa.

    **Los diez capitulos no vienen embebidos.** Serian unas doce mil palabras
    cargadas al abrir la pagina donde no se lee ni una; la lectura es capitulo
    a capitulo y la peticion tambien.

    La dedicatoria se sirve aqui, y es su unico uso: la creo T2 y hasta ahora
    no la leia nadie.
    """
    version = await _version_o_404(sesion, token)
    dedicatoria = await dedicatoria_de(sesion, version.obra_id)

    return VersionPublicada(
        titulo=await titulo_de_obra(sesion, version.obra_id),
        ordinal=version.ordinal,
        publicada_en=version.publicada_en,
        dedicatoria=dedicatoria.texto if dedicatoria else None,
        capitulos=[
            CapituloPublicado(
                numero=capitulo.numero,
                titulo=capitulo.titulo,
                cambiado=capitulo.cambiado,
            )
            for capitulo in await capitulos_de(sesion, version.id)
        ],
    )


@router.get("/{token}/capitulos/{numero}")
async def capitulo(token: str, numero: int, sesion: Sesion) -> dict[str, object]:
    """La prosa de un capitulo, **la que se fijo al publicar**.

    No la vigente: `capitulo_publicado` apunta a un `version_texto_id` concreto
    (`RF-PUB-01`), y resolver la version de hoy haria que un enlace ya
    repartido cambiara de contenido sin que nadie lo tocara.
    """
    version = await _version_o_404(sesion, token)

    texto = await texto_publicado(sesion, version.id, numero)
    if texto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)

    return {"numero": numero, "texto": texto}


@router.get("/{token}/ficha")
async def ficha(token: str, sesion: Sesion) -> FichaDeLectura:
    """Quien es quien, y en que capitulos aparece (`RF-PUB-05`).

    Una tirada sin ficha devuelve la ficha vacia y no un 404: el enlace es
    valido y la portada se lee igual. Un 404 aqui diria que el regalo no
    existe, que es otra cosa.
    """
    version = await _version_o_404(sesion, token)

    guardada = await ficha_de(sesion, version.id)
    if guardada is None:
        return FichaDeLectura()

    return FichaDeLectura(
        entradas=[EntradaDeFicha.model_validate(entrada) for entrada in guardada.entradas]
    )


@router.get("/{token}/versiones")
async def versiones(token: str, sesion: Sesion) -> list[VersionPublicada]:
    """Las tiradas de esta obra, de la mas reciente a la primera.

    Sin prosa y sin capitulos: es el historial para volver a una ya leida, y
    cada una se abre por su propio enlace.
    """
    version = await _version_o_404(sesion, token)

    return [
        VersionPublicada(ordinal=otra.ordinal, publicada_en=otra.publicada_en)
        for otra in await versiones_de(sesion, version.obra_id)
    ]


@router.get("/{token}/pdf")
async def pdf(token: str, sesion: Sesion) -> dict[str, object]:
    """El regalo en un fichero, para imprimir o guardar.

    **Fuera del alcance de T9 por decision del 2026-09-24.** El enfoque
    -- imprimir desde el Chromium de Playwright, sin dependencia nueva -- esta
    pendiente de aprobacion, y escribirlo antes seria escribir contra una
    decision que puede cambiar. Sale como tarea propia cuando se apruebe.
    """
    await _version_o_404(sesion, token)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="La descarga en PDF todavia no esta disponible.",
    )
