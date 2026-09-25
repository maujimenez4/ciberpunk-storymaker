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

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio
from app.commons.observabilidad import Observador, ObservadorNulo, Puntuacion, Span, Traza
from app.features.calidad import (
    CATALOGO_DE_MANUSCRITO,
    Defecto,
    HechoUsado,
    ManuscritoAValidar,
    cerrar_manuscrito,
    emitir,
    puntuaciones_de_g4,
)
from app.features.manuscrito import schemas
from app.features.manuscrito.lean import correr_lean
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
    ficha_de,
    hechos_con_sus_capitulos,
    hechos_vivos,
    presentes_por_capitulo,
    ultima_version,
)

SEPARADOR = "\n\n"
"""Entre capitulos del manuscrito ensamblado. No es el formato del PDF: eso lo
decide quien maqueta, y aqui solo se concatena lo que hay que validar."""

ESTADO_APROBADO = "INTEGRADA"

NOMBRE_DE_LEAN = "cronologia_lean"
"""El nombre de `verification.md` §8.3, sin traducir: es la llave de su *score*."""


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


class ObraSinCapitulos(ErrorDeDominio):
    """La obra no tiene capitulos: **cero capitulos no es «todos pasaron»**.

    Sin esta guarda, la comprobacion por capitulo no encontraba ninguno sin
    puerta y dejaba pasar; lo unico que quedaba delante era Lean, que con cero
    eventos no tiene nada que objetar. El resultado era una tirada en blanco con
    su token repartible (regla de dominio 14).
    """

    def __init__(self, obra_id: int) -> None:
        self.obra_id = obra_id
        super().__init__(
            f"No se puede publicar: la obra {obra_id} no tiene capitulos. "
            "Falta el outline o la novela no se ha escrito."
        )


class CronologiaIncoherente(ErrorDeDominio):
    """Lean rechazo la cronologia, y **por eso no se publica**. `CA-21`.

    T5 hizo que Lean lo diga; esto hace que lo impida. Son cosas distintas y la
    segunda es la que el encargo exige: un validador que detecta y no bloquea
    produce informes que nadie lee.

    El mensaje lleva **quien y donde**. RF-FOR-03 pide que el fallo vuelva al
    editor como *feedback*, y «la cronologia no es coherente» a secas obliga a
    abrir la base para saber que arreglar.
    """

    def __init__(self, detalle: str) -> None:
        self.detalle = detalle
        super().__init__(f"No se puede publicar. {detalle}")


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

    filas = await capitulos_con_su_puerta(sesion, obra_id)
    if not filas:
        raise ObraSinCapitulos(obra_id)

    for fila in filas:
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

    hechos = await hechos_vivos(sesion, obra_id)
    return [
        {
            "nombre": nombre,
            "tipo": "personaje",
            "capitulos": sorted(set(capitulos)),
            "hecho_canon_id": _hecho_de_la_entrada(nombre, hechos),
        }
        for nombre, capitulos in sorted(por_nombre.items())
    ]


async def ficha_para_leer(
    sesion: AsyncSession, version: VersionPublicada
) -> schemas.FichaDeLectura:
    """La ficha de una tirada **con los hechos vivos** de cada entrada (P-37).

    Las entradas y sus capitulos son los que se guardaron al publicar: la ficha
    de una tirada no cambia. Los hechos se leen ahora, del canon, porque lo que
    se puede corregir es lo que sigue vivo. Una tirada sin ficha da la vacia.
    """
    guardada = await ficha_de(sesion, version.id)
    if guardada is None:
        return schemas.FichaDeLectura()
    por_entidad: dict[str, list[schemas.HechoDeFicha]] = {}
    for hecho in await hechos_vivos(sesion, version.obra_id):
        por_entidad.setdefault(str(hecho["entidad"]), []).append(
            schemas.HechoDeFicha(
                hecho_canon_id=int(hecho["id"]),
                atributo=str(hecho["atributo"]),
                valor=str(hecho["valor"]),
            )
        )
    return schemas.FichaDeLectura(
        entradas=[
            schemas.EntradaDeFicha.model_validate(
                {**entrada, "hechos": por_entidad.get(str(entrada["nombre"]), [])}
            )
            for entrada in guardada.entradas
        ]
    )


ATRIBUTO_DE_NOMBRE = "nombre"


def _hecho_de_la_entrada(nombre: str, hechos: Sequence[dict[str, Any]]) -> int | None:
    """El hecho de canon con el que se corrige una entrada de la ficha (D-02).

    Entre los hechos vivos de esa entidad, el de su `nombre` si lo hay; si no,
    el unico que tenga. **Con varios y ninguno de nombre, `None`**: elegir uno
    al azar mandaria la correccion del lector a un hecho que no pidio tocar.
    """
    suyos = [h for h in hechos if str(h["entidad"]) == nombre]
    de_nombre = [h for h in suyos if str(h["atributo"]) == ATRIBUTO_DE_NOMBRE]
    if len(de_nombre) == 1:
        return int(de_nombre[0]["id"])
    if len(suyos) == 1:
        return int(suyos[0]["id"])
    return None


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


class ElementosObligatoriosAusentes(ErrorDeDominio):
    """Falta en la novela un elemento que el comprador pidio: **no se publica**.

    Regla de dominio 11 (`CLAUDE.md` §8) y P-33: «un dato que el comprador pidio
    y no esta no es una omision: es el producto sin entregar». Hasta aqui la
    cobertura se media en G4, emitia su *score* y la novela salia igual.

    El mensaje nombra **cuales** faltan, por lo mismo que `CapituloSinPuerta`
    nombra el capitulo: quien lo recibe es quien tiene que ir a arreglarlo.
    """

    def __init__(self, faltantes: Sequence[str]) -> None:
        self.faltantes = list(faltantes)
        super().__init__(
            "No se puede publicar: faltan en la novela elementos obligatorios del brief: "
            + ", ".join(f"«{f}»" for f in self.faltantes)
        )


def entrada_del_cuadro(capitulo: int, defecto: Defecto) -> dict[str, Any]:
    """Como se guarda un defecto vigente en `cuadro_de_defectos.defectos`.

    Con el **numero de capitulo** fuera del `Defecto`, porque `calidad.Defecto`
    no lo lleva y la clasificacion de la Fase 5 lo necesita en la huella.
    """
    return {"capitulo": capitulo, "defecto": defecto.model_dump()}


async def _cuadro_de_defectos(
    sesion: AsyncSession, obra_id: int, span: Span | None = None
) -> list[dict[str, Any]]:
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
    if span is not None:
        emitir(span, puntuaciones_de_g4(cierre))
    cobertura = cierre.cobertura
    # Antes se leian `cubiertos` y `faltantes` con `getattr`, y `Cobertura` no
    # tiene `faltantes`: se llama `ausentes`. El cuadro decia siempre «no falta
    # nada», que es la otra mitad de P-33.
    return [
        {
            "cobertura": {
                "cubiertos": [c.elemento for c in cobertura.cubiertos],
                "faltantes": [a.elemento for a in cobertura.ausentes],
            }
        }
    ]


def _faltantes(cuadro: Sequence[dict[str, Any]]) -> list[str]:
    return [
        str(f) for entrada in cuadro for f in (entrada.get("cobertura") or {}).get("faltantes", [])
    ]


async def publicar(
    sesion: AsyncSession,
    obra_id: int,
    *,
    observador: Observador | None = None,
    defectos_vigentes: Sequence[tuple[int, Defecto]] = (),
) -> VersionPublicada:
    """Una tirada inmutable de la obra, o ninguna.

    **R-1: si nada cambio, se devuelve la tirada que ya hay.** Dos tiradas
    identicas son dos enlaces al mismo contenido y dos fichas, y ni el comprador
    sabria cual mandar. «Publicar de nuevo» sin cambios no es un error: es que no
    habia nada que publicar.

    **Una traza `publicacion`** en la sesion de la obra (`CLAUDE.md` §4.3), con
    un span por validador: `cronologia_lean` y `puerta_g4`, cada uno con su
    *score*. El observador de produccion llega blindado: si Langfuse se cae, se
    publica igual.

    **La tirada nueva queda vigente** y la anterior deja de serlo (plan-5 T1):
    publicar es lo que el lector pasa a tener delante.

    `defectos_vigentes` son los `(numero de capitulo, Defecto)` que la tirada
    lleva encima sin que impidan publicar; van al cuadro, que es contra lo que
    la Fase 5 clasifica preexistente frente a introducido (RF-PET-05).
    """
    observador = observador if observador is not None else ObservadorNulo()
    async with observador.traza(obra_id=obra_id, nombre="publicacion") as traza:
        return await _publicar(sesion, obra_id, traza, defectos_vigentes)


async def _publicar(
    sesion: AsyncSession,
    obra_id: int,
    traza: Traza,
    defectos_vigentes: Sequence[tuple[int, Defecto]] = (),
) -> VersionPublicada:
    listos = await _capitulos_listos(sesion, obra_id)

    # `CA-21`. **Antes de escribir nada**: `publicar` ya es atomico por su
    # SAVEPOINT, pero verificar primero es mas barato y deja el fallo mas claro,
    # porque no hay nada que deshacer.
    #
    # Si falta la herramienta, `correr_lean` lanza `HerramientaNoDisponible` y
    # **tampoco se publica**: que no este instalado Lean no puede degradar a
    # «pues entregamos sin comprobar». La verificacion formal es eliminatoria.
    # En ese caso **no hay score**: un validador que no llego a correr no
    # produce un cero, que seria un numero inventado (`calidad/scores.py`).
    async with traza.span("cronologia_lean") as span:
        veredicto = await correr_lean(sesion, obra_id)
        emitir(
            span,
            [Puntuacion(nombre=NOMBRE_DE_LEAN, valor=1.0 if veredicto.ok else 0.0)],
        )
        if not veredicto.ok:
            span.salida(veredicto.mensaje)
    if not veredicto.ok:
        raise CronologiaIncoherente(veredicto.mensaje)

    anterior = await ultima_version(sesion, obra_id)
    fijados = (
        {}
        if anterior is None
        else {c.numero: c.version_texto_id for c in await capitulos_de(sesion, anterior.id)}
    )

    if anterior is not None and not _hay_cambios(fijados, listos):
        return anterior

    # P-33 y regla de dominio 11. **Antes de crear la version**: una novela sin
    # un elemento que el comprador pidio es el producto sin entregar, y el
    # *score* de G4 ya se emite aunque no se publique.
    async with traza.span("puerta_g4") as span:
        defectos = await _cuadro_de_defectos(sesion, obra_id, span)
    faltantes = _faltantes(defectos)
    if faltantes:
        raise ElementosObligatoriosAusentes(faltantes)
    defectos = [*defectos, *(entrada_del_cuadro(c, d) for c, d in defectos_vigentes)]

    # RF-PUB-08, y **el punto de retorno es propio a proposito**. `publicar` no
    # hace `commit` -- escribe en la transaccion de quien llama --, asi que sin
    # este `begin_nested` un fallo a mitad dejaria la `VersionPublicada` escrita
    # y sin capitulos: una novela en blanco con su token ya repartible. El
    # SAVEPOINT deshace **solo lo de aqui** y no toca lo que el llamador tuviera
    # empezado, que no es cosa nuestra.
    async with sesion.begin_nested():
        # Se apaga la vigente **antes** de insertar la nueva: el indice parcial
        # admite una sola vigente por obra, y al reves lanza `IntegrityError`.
        await sesion.execute(
            update(VersionPublicada)
            .where(VersionPublicada.obra_id == obra_id, VersionPublicada.vigente.is_(True))
            .values(vigente=False)
        )
        version = VersionPublicada(
            vigente=True,
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
        sesion.add(CuadroDeDefectos(version_id=version.id, defectos=defectos))

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
