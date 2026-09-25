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

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.sesion import obtener_sesion
from app.commons.observabilidad import Observador, obtener_observador
from app.features.manuscrito import modelos
from app.features.manuscrito.pdf import (
    Capitulo,
    Impresora,
    ImpresoraNoDisponible,
    componer_html,
    obtener_impresora,
)
from app.features.manuscrito.repository import (
    capitulos_de,
    dedicatoria_de,
    texto_publicado,
    titulo_de_obra,
    version_por_token,
    versiones_de,
)
from app.features.manuscrito.reversion import revertir
from app.features.manuscrito.schemas import (
    CapituloPublicado,
    FichaDeLectura,
    VersionPublicada,
)
from app.features.manuscrito.service import ficha_para_leer, publicar

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]

router = APIRouter(prefix="/lectura", tags=["lectura"])

# --- La publicacion, que es del Autor y va por `obra_id` ---------------------
#
# Router aparte y prefijo distinto **a proposito**. Las rutas de lectura se
# indexan por el token porque es lo unico que las protege; esta la usa quien ya
# es dueño de la obra y todavia **no tiene token** -- se lo da esta llamada --,
# asi que indexarla por token seria imposible: pediria la llave que viene a
# entregar.
publicacion = APIRouter(prefix="/obras", tags=["publicacion"])


@publicacion.post("/{obra_id}/publicar")
async def publicar_obra(
    obra_id: int,
    sesion: Sesion,
    observador: Annotated[Observador, Depends(obtener_observador)],
) -> dict[str, object]:
    """Fija una tirada inmutable y **devuelve el token con el que se lee**.

    `publicar` existia en el servicio desde la Fase 4 y no tenia ruta, asi que
    desde el navegador no habia forma de publicar ni de saber cuando una novela
    se podia leer: el frontend llegaba hasta «se esta escribiendo» y ahi se
    cortaba. No faltaba una pantalla, **faltaba el dato**.

    **Es la unica ruta que devuelve el `identificador_publico`**, y la asimetria
    con las de lectura es deliberada: alli no sale porque quien lee ya entro con
    el, y repetirlo solo lo pondria en un sitio mas -- un registro, una captura,
    un historial compartido --. Aqui sale porque quien publica aun no lo tiene.

    Los fallos de dominio -- un capitulo que no paso su puerta, una cronologia
    que Lean rechaza -- los traduce el manejador central de `commons/errors`
    (`CLAUDE.md` §6). Aqui no hay ni un `HTTPException`: un 500 dejaria al
    frontend sin nada que contarle a quien acaba de encargar la novela.
    """
    version = await publicar(sesion, obra_id, observador=observador)
    await sesion.commit()
    return {"token": version.identificador_publico, "ordinal": version.ordinal}


@publicacion.post("/{obra_id}/versiones/{version}/revertir")
async def revertir_la_version(obra_id: int, version: int, sesion: Sesion) -> dict[str, object]:
    """RI-10. `version` es el identificador de la `VersionPublicada`.

    **No es larga y no va a segundo plano:** mover una bandera no llama al
    modelo. La revertida no se borra (RF-PET-08) y su enlace sigue leyendose.
    """
    vuelta = await revertir(sesion, obra_id=obra_id, version_publicada_id=version)
    await sesion.commit()
    return {"token": vuelta.identificador_publico, "ordinal": vuelta.ordinal}


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
    return await ficha_para_leer(sesion, version)


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


@router.get(
    "/{token}/pdf",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "La novela publicada, en PDF"},
        404: {"description": NO_ENCONTRADO},
        503: {"description": "No hay navegador con el que imprimir"},
    },
)
async def pdf(
    token: str,
    sesion: Sesion,
    impresora: Annotated[Impresora, Depends(obtener_impresora)],
) -> Response:
    """El regalo en un fichero, para imprimir o guardar (T10, `RI-11`).

    **Sale de la version publicada, nunca del texto vigente** (regla de dominio
    14): cada capitulo se lee con `texto_publicado`, lo mismo que la ruta del
    capitulo. Y la dedicatoria va en la portada, no como capitulo (regla 15).

    Respuesta sincrona y no trabajo en segundo plano: el spike midio 1,2-2,4 s
    por novela, casi todo arranque del navegador.

    Si no hay navegador, **503 con motivo y no 500**. `ImpresoraNoDisponible`
    no es un error de dominio -- es una herramienta ausente -- y el manejador
    central de `commons/errors/` no la conoce; se traduce aqui, que es el unico
    sitio que la ve. **Ni el HTML ni la prosa se escriben en ningun log.**
    """
    version = await _version_o_404(sesion, token)

    capitulos: list[Capitulo] = []
    for capitulo in await capitulos_de(sesion, version.id):
        texto = await texto_publicado(sesion, version.id, capitulo.numero)
        if texto is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
        capitulos.append((capitulo.numero, capitulo.titulo, texto, capitulo.cambiado))

    titulo = await titulo_de_obra(sesion, version.obra_id)
    dedicatoria = await dedicatoria_de(sesion, version.obra_id)
    documento = componer_html(
        titulo=titulo or "Novela",
        dedicatoria=dedicatoria.texto if dedicatoria else None,
        capitulos=capitulos,
    )

    try:
        contenido = await impresora.a_pdf(documento)
    except ImpresoraNoDisponible as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se puede generar el PDF ahora mismo: {error}",
        ) from error

    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_nombre_de_fichero(titulo)}"'},
    )


def _nombre_de_fichero(titulo: str) -> str:
    """`novela-<titulo>.pdf` solo con ASCII seguro: la cabecera no admite mas
    sin la forma `filename*`, y un nombre feo es mejor que una cabecera rota."""
    base = "".join(c if c.isalnum() else "-" for c in titulo.lower()).strip("-")
    base = "-".join(p for p in base.split("-") if p)[:60]
    return f"novela-{base}.pdf" if base else "novela.pdf"
