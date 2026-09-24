"""La novela entera: el bucle de los diez capitulos. **`CA-1`.**

Cierra la fase, y como `ciclo.py` **no anade comportamiento: conecta**. Todo lo
que este fichero llama estaba escrito y probado por su tarea; lo que no existia
era el bucle, y con el las dos junturas que la ola 2 dejo abiertas.

## Por que el bucle es `reanudar` y no un `for` de uno a diez

Podria escribirse asi, y seria un error. `reanudacion.reanudar` (T8) ya hace,
para **un** capitulo, las cuatro cosas que el bucle necesita: mira por donde va
la novela, cruza la puerta de `checkpoint.empezar_capitulo` —R-6, ni un capitulo
ya integrado, ni un hueco detras—, cierra lo que una caida dejo vivo y abre el
trabajo con las reparaciones que el capitulo ya gasto. Un `for` de uno a diez
tendria que repetir esas cuatro, y entonces habria **dos sitios que deciden cual
es el capitulo siguiente**: el que arranca limpio y el que reanuda. R-6 pasaria
a depender de cual de los dos se toco por ultima vez.

Asi que el bucle es: pedir el siguiente, escribirlo, anotar el avance, repetir.
**Arrancar de cero y reanudar tras una caida son la misma llamada**, y eso no es
elegancia: es lo que hace que `CA-5` y `CA-1` se prueben sobre el mismo codigo.

## Y por que para cuando el capitulo no se integra

`siguiente_capitulo` devuelve **el primero no integrado**. Si el capitulo que
acaba de escribirse termino en `ESCALADA` o en `FALLIDA`, la siguiente vuelta
pediria el mismo y el bucle no acabaria nunca. Por eso la condicion de parada no
es un contador de vueltas —que seria un tope arbitrario disfrazado de guarda—
sino el estado del trabajo: **si el capitulo no quedo `INTEGRADA`, la novela se
detiene y se informa** (R-6). No se salta al siguiente, y esa es justamente la
frase que `architecture.md` §3.9 escribe para `DETENIDA`.

**Un capitulo no integrado no es una averia del bucle**: se devuelve en
`Novela.detenida_en` con su causa, como `ResultadoDelCiclo` devuelve la suya. Lo
que se propaga es lo que no es de dominio.

## Los diez no se paralelizan

Y conviene decirlo aqui, donde la tentacion vive: la restriccion es **CU-03**,
no el limite de concurrencia. Cada capitulo necesita integrado el anterior
porque su paquete lleva el texto del N-1 en la capa de continuidad y su resumen
en la de memoria. Lo que se solapa son **obras distintas** (`architecture.md`
§3.8).

## La cobertura, que solo existe con la novela entera

`CA-15` se demostro como funcion en T7 y quedo sin cerrar de extremo a extremo:
faltaba **la consulta** que junta `hecho_canon` con `hecho_usado_en` y con
`capitulo.numero`, y faltaba que alguien ejecutara el validador. Las dos estan
aqui — la consulta en `hechos_usados`, la ejecucion en `cobertura_de_la_novela`,
que pasa por `CATALOGO_DE_MANUSCRITO` y no por la funcion suelta.

**`usado_en` lleva el `numero` del capitulo, no su `capitulo_id`.** La tabla
guarda identificadores y el informe lo lee una persona: «falta el perro Luna» es
util, «esta en el capitulo 47» con diez capitulos es un informe que parece que
funciona y no sirve para nada.

**Las tablas de otras features se leen por SQL con su nombre** —`capitulo` es de
`outline`, `hecho_canon` y `entrevista` de `obra`, `hecho_usado_en` de `canon`—:
una feature no entra a los ficheros internos de otra (`CLAUDE.md` §5.1). Es el
mismo trato que `ciclo.py` y `checkpoint.py` dan a las suyas.
"""

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.jobs.turnos import CerrojoDeEscena, PresupuestoConcurrente
from app.commons.llm.contador import ContadorDeTokens
from app.features.calidad import (
    CATALOGO_DE_MANUSCRITO,
    Cobertura,
    HechoUsado,
    ManuscritoAValidar,
    ValidadorDeManuscrito,
    cerrar_manuscrito,
)
from app.features.canon import Vector
from app.features.contexto import VectorStore
from app.features.escritura.checkpoint import (
    Checkpoint,
    TrabajoSinCapitulo,
    registrar_checkpoint,
    ultimo_capitulo_completado,
)
from app.features.escritura.ciclo import (
    Agentes,
    ResultadoDelCiclo,
    TrabajoDesconocido,
    ejecutar_ciclo,
)
from app.features.escritura.maquina import Estado
from app.features.escritura.modelos import Trabajo
from app.features.escritura.reanudacion import reanudar

Ejecutar = Callable[[Trabajo], Awaitable[Any]]
"""Lo que el bucle hace con cada trabajo. Es el tipo que `reanudar` ya pide, y
se repite aqui con nombre para que la firma del bucle se lea."""


@dataclass(frozen=True, slots=True)
class CapituloDeLaNovela:
    """Un capitulo por el que la novela paso, con **su numero y su estado**.

    Lleva `numero` ademas de `capitulo_id` por lo mismo que `Checkpoint`: quien
    lee razona en numeros de outline, y un identificador no dice cuanto queda.
    """

    capitulo_id: int
    numero: int
    trabajo_id: int
    estado: str


@dataclass(frozen=True, slots=True)
class Novela:
    """Lo que el bucle hizo. **Se informa, no se lanza.**

    Una novela que se detiene en el capitulo siete no es una averia del proceso:
    es un final previsto que alguien tiene que poder contarle a una persona, y
    es el mismo trato que `ResultadoDelCiclo` le da a un capitulo escalado.
    """

    obra_id: int
    integrados: tuple[CapituloDeLaNovela, ...]
    checkpoint: Checkpoint
    detenida_en: CapituloDeLaNovela | None = None
    causa: str | None = None

    @property
    def completa(self) -> bool:
        """No queda capitulo por integrar. **Se deriva de `detenida_en`** y no
        es una bandera aparte: asi «completa y detenida» no se puede ni
        representar."""
        return self.detenida_en is None


def ciclo_de_la_novela(
    sesion: AsyncSession,
    *,
    agentes: Agentes,
    contador: ContadorDeTokens,
    presupuesto: PresupuestoConcurrente,
    cerrojo: CerrojoDeEscena,
    almacen: VectorStore | None = None,
    consulta: Sequence[float] | None = None,
    vectorizar: Callable[[str], Vector] | None = None,
    modelo: str = "desconocido",
    semilla: int = 0,
) -> Ejecutar:
    """Compone el `ejecutar` que el bucle inyecta: **un capitulo, el del trabajo.**

    Existe para que el bucle no sepa componer un ciclo y el router no sepa
    recorrer una novela. Es la misma inversion que `reanudar` ya hacia con su
    parametro, y lo que permite que un test pruebe el bucle con un ciclo falso.

    El capitulo sale de `trabajo.capitulo_id`, que `abrir_trabajo` rellena. Si
    faltara, se lanza `TrabajoSinCapitulo` en vez de adivinarlo: un trabajo sin
    capitulo no es escribible, y callarlo escribiria el equivocado.
    """

    async def ejecutar(trabajo: Trabajo) -> ResultadoDelCiclo:
        if trabajo.capitulo_id is None:
            raise TrabajoSinCapitulo(trabajo.id)
        return await ejecutar_ciclo(
            sesion,
            trabajo,
            capitulo_id=trabajo.capitulo_id,
            agentes=agentes,
            contador=contador,
            presupuesto=presupuesto,
            cerrojo=cerrojo,
            almacen=almacen,
            consulta=consulta,
            vectorizar=vectorizar,
            modelo=modelo,
            semilla=semilla,
        )

    return ejecutar


async def escribir_novela(sesion: AsyncSession, *, obra_id: int, ejecutar: Ejecutar) -> Novela:
    """Los diez capitulos, **en orden y cada uno con el anterior integrado**.

    Cuatro pasos por vuelta, y el orden importa:

    1. **`reanudar`**, que elige el capitulo, cruza la puerta y abre el trabajo.
       Si no queda ninguno, la novela esta escrita y se sale por arriba.
    2. **Se escribe**, con el ciclo que llega inyectado.
    3. **Se relee el estado del trabajo.** No se cree lo que devolvio el paso:
       `architecture.md` §3.4 dice que cada paso persiste su salida y se vuelve
       a leer, y es lo que hace que reanudar sea identico a ejecutar.
    4. **Se anota el avance** si el capitulo quedo `INTEGRADA`, y si no, se para.

    `registrar_checkpoint` va **despues** de comprobar el estado y no antes: su
    propia guarda rechaza un capitulo que no se integro (`CheckpointPrematuro`),
    y apoyarse en la excepcion para decidir el flujo convertiria un final
    previsto —la novela se detiene— en una averia.

    **Y el checkpoint que se devuelve es el que ella anota**, no uno que se
    vuelva a leer al final. Eso tiene un motivo que costo verlo: el avance se
    *deriva* de `trabajo`, asi que releerlo da el mismo numero **aunque nadie
    haya anotado nada**, y con esa forma se podia borrar la llamada a
    `registrar_checkpoint` sin que cayera un solo test. Quedaba una linea que
    RF-ORQ-05 exige y que ninguna prueba sostenia. Encadenar su valor de vuelta
    la vuelve comprobable: si no se llama, no hay checkpoint que devolver.
    """
    integrados: list[CapituloDeLaNovela] = []
    checkpoint = await ultimo_capitulo_completado(sesion, obra_id=obra_id)

    while True:
        retomada = await reanudar(sesion, obra_id=obra_id, ejecutar=ejecutar)
        if retomada.capitulo_id is None or retomada.numero is None or retomada.trabajo_id is None:
            # Es `Retomada.terminada` escrito sobre sus tres campos, y se
            # escribe asi por dos motivos: los tres van juntos —`reanudar` los
            # devuelve o los omite a la vez— y es lo unico que deja al
            # comprobador de tipos ver que mas abajo ya no son nulos. Una
            # propiedad no estrecha nada, y la alternativa seria un `assert` o
            # un valor inventado.
            return Novela(obra_id=obra_id, integrados=tuple(integrados), checkpoint=checkpoint)

        trabajo = await _trabajo(sesion, retomada.trabajo_id)
        capitulo = CapituloDeLaNovela(
            capitulo_id=retomada.capitulo_id,
            numero=retomada.numero,
            trabajo_id=trabajo.id,
            estado=trabajo.estado,
        )

        if trabajo.estado != Estado.INTEGRADA.value:
            return Novela(
                obra_id=obra_id,
                integrados=tuple(integrados),
                checkpoint=checkpoint,
                detenida_en=capitulo,
                causa=trabajo.causa_fallo,
            )

        checkpoint = await registrar_checkpoint(sesion, trabajo)
        integrados.append(capitulo)


async def numero_de_capitulo(sesion: AsyncSession, *, capitulo_id: int | None) -> int | None:
    """El numero de outline de un capitulo, para que RI-06 sea **legible por el**.

    Devuelve `None` en vez de lanzar cuando no hay capitulo o no existe: quien
    pregunta es la consulta de un trabajo, y un trabajo sin capitulo —o de un
    capitulo borrado— es legible igual. Negarse a responder el estado por no
    poder traducir un numero seria cambiar un dato que falta por un error.
    """
    if capitulo_id is None:
        return None
    numero = (
        await sesion.execute(
            text("SELECT numero FROM capitulo WHERE id = :id"), {"id": capitulo_id}
        )
    ).scalar_one_or_none()
    return None if numero is None else int(numero)


async def elementos_obligatorios_de(sesion: AsyncSession, *, obra_id: int) -> tuple[str, ...]:
    """Lo que el comprador pidio que apareciera, tal y como lo escribio.

    **Salen de `obra.elementos_obligatorios` desde T3, y esa es la mitad que
    cierra P-2.** Hasta entonces se leian del brief en bruto —el JSON de
    `entrevista.respuestas`— porque no se persistian en ninguna columna, y de
    ahi salia la forma de aprobar de balde: una obra creada por cualquier ruta
    que no fuera la entrevista no tenia elementos que cubrir, y
    `cobertura_de_personalizacion` **decia que todo estaba bien sin haber
    comprobado nada**.

    Cambiar la columna no habria bastado por si sola: mientras la lectura
    siguiera yendo a la entrevista, la columna seria un dato que nadie mira. Por
    eso el test que cierra P-2 borra la entrevista entera y exige que esto siga
    devolviendo los elementos.

    La lista **nunca esta vacia**: lo garantiza el `CheckConstraint` de `obra`,
    no una comprobacion de aqui. Y una obra que no existe devuelve `()`, que no
    es «todo cubierto» sino «no se comprobo nada» — quien lea el informe ve cero
    elementos y eso es lo que tiene que ver.
    """
    elementos = (
        await sesion.execute(
            text("SELECT elementos_obligatorios FROM obra WHERE id = :obra_id"),
            {"obra_id": obra_id},
        )
    ).scalar_one_or_none()
    if elementos is None:
        return ()
    return tuple(str(e) for e in _json(elementos))


async def hechos_usados(sesion: AsyncSession, *, obra_id: int) -> tuple[HechoUsado, ...]:
    """El grafo de canon **con los capitulos que se apoyan en cada hecho**.

    Es la consulta que T7 dejo nombrada y sin escribir: junta `hecho_canon` con
    `hecho_usado_en` y con `capitulo`, y lo que sale por `usado_en` son los
    **numeros** de capitulo (RF-MEM-02).

    El `LEFT JOIN` no es indiferencia: un hecho que ningun capitulo usa
    —los del brief, que entran en la entrevista antes de la primera linea de
    prosa (RF-ENT-06)— **tiene que llegar** a la cobertura. Si se filtraran
    aqui, la guarda de `cobertura.py` que los descarta no tendria nunca contra
    que defenderse, y esa regla seria inalcanzable: cubierta por construccion y
    sin ningun test capaz de caer.
    """
    filas = (
        (
            await sesion.execute(
                text(
                    "SELECT h.id AS id, h.entidad AS entidad, h.atributo AS atributo, "
                    "       h.valor AS valor, c.numero AS numero "
                    "FROM hecho_canon AS h "
                    "LEFT JOIN hecho_usado_en AS u ON u.hecho_canon_id = h.id "
                    "LEFT JOIN capitulo AS c ON c.id = u.capitulo_id "
                    "WHERE h.obra_id = :obra_id "
                    "ORDER BY h.id, c.numero"
                ),
                {"obra_id": obra_id},
            )
        )
        .mappings()
        .all()
    )

    partes: dict[int, tuple[str, str, str]] = {}
    capitulos: dict[int, list[int]] = {}
    for fila in filas:
        identificador = int(fila["id"])
        partes.setdefault(
            identificador, (str(fila["entidad"]), str(fila["atributo"]), str(fila["valor"]))
        )
        if fila["numero"] is not None:
            capitulos.setdefault(identificador, []).append(int(fila["numero"]))

    return tuple(
        HechoUsado(
            entidad=entidad,
            atributo=atributo,
            valor=valor,
            usado_en=tuple(sorted(set(capitulos.get(identificador, ())))),
        )
        for identificador, (entidad, atributo, valor) in partes.items()
    )


async def cobertura_de_la_novela(
    sesion: AsyncSession,
    *,
    obra_id: int,
    catalogo: Sequence[ValidadorDeManuscrito] = CATALOGO_DE_MANUSCRITO,
) -> Cobertura:
    """`CA-15` de extremo a extremo: **contra la tabla de hechos, y ejecutado.**

    Pasa por `cerrar_manuscrito` y no por `cobertura_de_obligatorios` a pelo, y
    no es ceremonia: «un validador que no esta en el catalogo no corre», y hasta
    hoy este estaba probado y no lo ejecutaba nadie. Llamar a la funcion suelta
    desde aqui lo habria dejado corriendo **fuera** del catalogo, que es el otro
    lado de la misma frase.
    """
    cierre = cerrar_manuscrito(
        ManuscritoAValidar(
            elementos_obligatorios=await elementos_obligatorios_de(sesion, obra_id=obra_id),
            hechos=await hechos_usados(sesion, obra_id=obra_id),
        ),
        catalogo,
    )
    return cierre.cobertura


async def _trabajo(sesion: AsyncSession, trabajo_id: int) -> Trabajo:
    """El trabajo releido de la base, que es de donde se lee el estado (§3.4)."""
    trabajo = await sesion.get(Trabajo, trabajo_id)
    if trabajo is None:
        raise TrabajoDesconocido(trabajo_id)
    return trabajo


def _json(valor: Any) -> dict[str, Any]:
    """La columna `JSON`, venga como `dict` de SQLAlchemy o como texto crudo."""
    if isinstance(valor, str):
        cargado: dict[str, Any] = json.loads(valor)
        return cargado
    return dict(valor) if valor else {}
