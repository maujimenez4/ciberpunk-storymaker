"""Publicar: de diez capitulos integrados a una tirada inmutable. `RF-PUB-01..08`.

**Publicar es afirmar que los capitulos pasaron su puerta, no que estan
escritos** (regla de dominio 14). Por eso lo primero que mira este modulo son
los trabajos y no los textos: un capitulo escalado existe, se lee bien, y no
puede ir en un regalo. Y no tener trabajo tampoco es haber pasado -- un capitulo
que nadie valido entraria sin que ningun validador lo hubiera mirado --, asi que
los dos casos fallan igual.

**Una sola transaccion, y no por elegancia.** Media publicacion es peor que
ninguna: una `VersionPublicada` con su token repartible y sin capitulos sirve
una novela en blanco, y el enlace ya salio por correo. `publicar` no hace
`commit`: escribe dentro de la transaccion de quien llama, que es quien sabe si
hay mas cosas que cerrar con ella.

**Por que la cobertura llega calculada y no se va a buscar.** La primera version
importaba `cobertura_de_la_novela` de `escritura`, y eso creo dos ciclos entre
features -- `manuscrito -> escritura -> ... -> canon -> obra -> manuscrito` --,
que `CLAUDE.md` §5.1 regla 5 llama error de diseno. La salida no fue diferir el
import dentro de una funcion: eso arranca y **deja el ciclo en pie**. La salida
fue ver que **la cobertura no es escritura**: es una comprobacion sobre el
resultado, vive en `calidad`, y quien publica no tiene por que saber quien la
calcula. Aqui se le pasan los datos y `calidad` la cierra dentro de su catalogo.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio
from app.features.calidad import (
    CATALOGO_DE_MANUSCRITO,
    HechoUsado,
    ManuscritoAValidar,
    cerrar_manuscrito,
)
from app.features.manuscrito.modelos import (
    CapituloPublicado,
    CuadroDeDefectos,
    FichaDeLectura,
    VersionPublicada,
)
from app.features.manuscrito.repository import (
    capitulos_con_su_puerta,
    capitulos_de,
    dedicatoria_de,
    elementos_obligatorios_de,
    hechos_con_sus_capitulos,
    presentes_por_capitulo,
    ultima_version,
)

SEPARADOR = "\n\n"
"""Entre capitulos del manuscrito ensamblado. No es el formato del PDF: eso lo
decide quien maqueta, y aqui solo se concatena lo que hay que validar."""

ESTADO_APROBADO = "INTEGRADA"


class CapituloSinPuerta(ErrorDeDominio):
    """Un capitulo que no paso su puerta de calidad, y **cual** (R-2, CA-23).

    Hereda de `ErrorDeDominio`, asi que el manejador central la traduce sin
    darla de alta en ningun sitio.

    El numero en el mensaje no es cortesia: «no se puede publicar» obliga a
    abrir la base para saber que capitulo mirar, y quien recibe ese error es
    quien tiene que ir a arreglarlo.
    """

    def __init__(self, numeros: Sequence[int]) -> None:
        self.numeros = list(numeros)
        cuales = ", ".join(str(n) for n in self.numeros)
        super().__init__(
            f"No se puede publicar: los capitulos {cuales} no han pasado su puerta de calidad."
        )


@dataclass(frozen=True)
class _CapituloListo:
    """Un capitulo aprobado, con el texto que se va a fijar."""

    numero: int
    titulo: str | None
    version_texto_id: int
    texto: str


async def _capitulos_listos(sesion: AsyncSession, obra_id: int) -> list[_CapituloListo]:
    """Los capitulos de la obra, comprobando que cada uno paso su puerta.

    La comprobacion y la lectura van juntas a proposito: separarlas dejaria una
    ventana entre validar una cosa y publicar otra.
    """
    listos: list[_CapituloListo] = []
    sin_puerta: list[int] = []

    for fila in await capitulos_con_su_puerta(sesion, obra_id):
        if fila["estado"] != ESTADO_APROBADO or fila["version_texto_id"] is None:
            sin_puerta.append(int(fila["numero"]))
            continue
        listos.append(
            _CapituloListo(
                numero=int(fila["numero"]),
                titulo=fila["titulo"],
                version_texto_id=int(fila["version_texto_id"]),
                texto=str(fila["texto"]),
            )
        )

    if sin_puerta:
        raise CapituloSinPuerta(sorted(set(sin_puerta)))
    return listos


async def ensamblar_manuscrito(sesion: AsyncSession, obra_id: int) -> str:
    """El texto de la novela, y **solo** el texto de la novela.

    La dedicatoria no entra (regla de dominio 15): no es prosa del manuscrito,
    no se valida como tal y no alimenta la lista negra de n-gramas. Meterla aqui
    la pondria en el contexto del Escritor por la puerta de atras.
    """
    listos = await _capitulos_listos(sesion, obra_id)
    return SEPARADOR.join(c.texto for c in listos)


async def _ficha_de_lectura(sesion: AsyncSession, obra_id: int) -> list[dict[str, Any]]:
    """Quien es quien, **con los capitulos en que aparece** (RF-PUB-05).

    Se deriva de los presentes de cada capitulo aprobado y no de una lista
    escrita a mano: una ficha que no salga de los datos se queda desfasada en la
    primera regeneracion, y entonces manda al lector a un capitulo equivocado.
    """
    por_nombre: dict[str, list[int]] = {}
    for fila in await presentes_por_capitulo(sesion, obra_id):
        for nombre in _lista(fila["presentes"]):
            por_nombre.setdefault(nombre, []).append(int(fila["numero"]))

    return [
        {"nombre": nombre, "tipo": "personaje", "capitulos": sorted(set(capitulos))}
        for nombre, capitulos in sorted(por_nombre.items())
    ]


def _lista(crudo: Any) -> list[str]:
    """La columna JSON, venga como lista o como el texto que guardo SQLite."""
    import json

    if isinstance(crudo, str):
        try:
            crudo = json.loads(crudo)
        except json.JSONDecodeError:
            return []
    if not isinstance(crudo, list):
        return []
    return [str(v) for v in crudo if str(v).strip()]


async def _cuadro_de_defectos(sesion: AsyncSession, obra_id: int) -> list[dict[str, Any]]:
    """Lo que la tirada lleva encima, **incluida la cobertura** de §11.

    La juntura con `calidad`, y no es un extra: sin la cobertura, el regalo puede
    salir sin un elemento que el comprador pidio y el cuadro diria que todo esta
    bien.

    Pasa por `cerrar_manuscrito` y no por el validador suelto: «un validador que
    no esta en el catalogo no corre», y llamarlo a pelo lo dejaria corriendo
    fuera de el, que es el otro lado de la misma frase.
    """
    hechos: dict[int, dict[str, Any]] = {}
    for fila in await hechos_con_sus_capitulos(sesion, obra_id):
        entrada = hechos.setdefault(
            int(fila["id"]),
            {
                "entidad": str(fila["entidad"]),
                "atributo": str(fila["atributo"]),
                "valor": str(fila["valor"]),
                "usado_en": [],
            },
        )
        if fila["numero"] is not None:
            entrada["usado_en"].append(int(fila["numero"]))

    cierre = cerrar_manuscrito(
        ManuscritoAValidar(
            elementos_obligatorios=tuple(await elementos_obligatorios_de(sesion, obra_id)),
            hechos=tuple(
                HechoUsado(
                    entidad=h["entidad"],
                    atributo=h["atributo"],
                    valor=h["valor"],
                    usado_en=tuple(h["usado_en"]),
                )
                for h in hechos.values()
            ),
        ),
        CATALOGO_DE_MANUSCRITO,
    )
    cobertura = cierre.cobertura
    return [
        {
            "cobertura": {
                "cubiertos": list(getattr(cobertura, "cubiertos", ()) or ()),
                "faltantes": list(getattr(cobertura, "faltantes", ()) or ()),
            }
        }
    ]


async def publicar(sesion: AsyncSession, obra_id: int) -> VersionPublicada:
    """Una tirada inmutable de la obra, o ninguna.

    **R-1: si nada cambio, se devuelve la tirada que ya hay.** Dos tiradas
    identicas son dos enlaces al mismo contenido y dos fichas, y ni el comprador
    sabria cual mandar. «Publicar de nuevo» sin cambios no es un error: es que no
    habia nada que publicar.
    """
    listos = await _capitulos_listos(sesion, obra_id)
    anterior = await ultima_version(sesion, obra_id)
    fijados = (
        {}
        if anterior is None
        else {c.numero: c.version_texto_id for c in await capitulos_de(sesion, anterior.id)}
    )

    if anterior is not None and not _hay_cambios(fijados, listos):
        return anterior

    # RF-PUB-08, y **el punto de retorno es propio a proposito**. `publicar` no
    # hace `commit` -- escribe en la transaccion de quien llama --, asi que sin
    # este `begin_nested` un fallo a mitad dejaria la `VersionPublicada` escrita
    # y sin capitulos: una novela en blanco con su token ya repartible. El
    # SAVEPOINT deshace **solo lo de aqui** y no toca lo que el llamador tuviera
    # empezado, que no es cosa nuestra.
    async with sesion.begin_nested():
        version = VersionPublicada(
            obra_id=obra_id,
            ordinal=1 if anterior is None else anterior.ordinal + 1,
            sucede_a_id=None if anterior is None else anterior.id,
        )
        sesion.add(version)
        await sesion.flush()

        for capitulo in listos:
            sesion.add(
                CapituloPublicado(
                    version_id=version.id,
                    numero=capitulo.numero,
                    titulo=capitulo.titulo,
                    version_texto_id=capitulo.version_texto_id,
                    cambiado=(
                        anterior is not None
                        and fijados.get(capitulo.numero) != capitulo.version_texto_id
                    ),
                )
            )

        sesion.add(
            FichaDeLectura(version_id=version.id, entradas=await _ficha_de_lectura(sesion, obra_id))
        )
        sesion.add(
            CuadroDeDefectos(
                version_id=version.id, defectos=await _cuadro_de_defectos(sesion, obra_id)
            )
        )

    return version


def _hay_cambios(fijados: dict[int, int], listos: list[_CapituloListo]) -> bool:
    """Si algun capitulo apunta hoy a otro texto que en la tirada anterior.

    Se compara el **identificador de version de texto**, que basta para saber si
    hay algo que publicar. Distinguir «otra version con el mismo texto» es
    RF-PUB-06 y lo cierra T7, que compara el texto de verdad.
    """
    if set(fijados) != {c.numero for c in listos}:
        return True
    return any(fijados[c.numero] != c.version_texto_id for c in listos)


async def dedicatoria_o_nada(sesion: AsyncSession, obra_id: int) -> str | None:
    """La dedicatoria de la obra para la portada, o `None`."""
    fila = await dedicatoria_de(sesion, obra_id)
    return None if fila is None else str(fila.texto)
