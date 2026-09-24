"""Checkpoint por capitulo, y el contador que no se hereda. **RF-ORQ-05 y R-3.**

`architecture.md` §3.3 describe el ciclo de **una escena**; §3.9 la maquina de
la **novela**. Este fichero es la parte de §3.9 que la Fase 3 necesita, y son
dos frases:

> «Al integrar un capitulo se persiste el avance, de modo que una caida reanuda
> desde **el ultimo capitulo completado** y no desde el principio.»

> «`SiguienteCapitulo` — pasa al capitulo N+1 … **No.** Cada capitulo empieza
> con su propio contador.»

La segunda parece una obviedad y no lo es. El documento escribe al lado la
consecuencia de equivocarse: *«avanzar de capitulo consumiria reintentos, y una
novela de diez capitulos se detendria sola por agotamiento sin que hubiera
fallado nada»*. Por eso el contador **no es un argumento que viaje por el
orquestador**: se pregunta a la base, por capitulo, cada vez.

## No hay tabla de checkpoint, y es a proposito

El avance **se deriva** de `trabajo`: el ultimo capitulo cuyo trabajo llego a
`INTEGRADA`. Es el mismo principio que `idempotencia.py` dejo escrito —*la
idempotencia vive en el dato, no en la memoria del proceso*— y el mismo que
`CLAUDE.md` §8 regla 3 aplica al estado en T. Una tabla aparte seria un segundo
relato de lo ocurrido, que puede divergir del primero justo cuando importa
—tras una caida— y que ademas es esquema y migracion.

Lo que si es una escritura es **atar el trabajo a su capitulo**: sin
`trabajo.capitulo_id` —la columna que T1 anadio— el avance no se puede
preguntar, porque un trabajo recien abierto todavia no tiene escena.

## Las dos reglas que dejan empezar el capitulo N+1

Son distintas y conviene no confundirlas, porque la ola 1 dejo abierta
precisamente esa pregunta:

| Regla | Que impide | De donde sale |
| --- | --- | --- |
| **La novela no esta detenida** | Que se siga escribiendo con un capitulo `ESCALADA` esperando a una persona | R-6, `maquina.exigir_que_la_novela_siga` |
| **El capitulo anterior esta integrado** | Que se escriba encima de un hueco, sea cual sea su causa | `architecture.md` §3.9 y CU-03 |

**Por que `FALLIDA` no detiene la novela.** `DETIENEN_LA_NOVELA` sigue
conteniendo solo `ESCALADA`, y la decision esta razonada: §3.6 declara `FALLIDA`
un **error tecnico relanzable como trabajo nuevo**, no un juicio de calidad, y
meterlo en el conjunto convertiria un remedio automatico en una decision humana
—habria que «desdetener» la obra a mano tras cada 5xx del proveedor—. Lo que
impide escribir el capitulo N+1 sobre un N averiado **no es ese conjunto**: es
la segunda regla, que exige `INTEGRADA` y por tanto tambien frena un `FALLIDA`
sin relanzar, un `CANCELADA` y un capitulo que nadie intento. Y desbloquea sola
en cuanto el relanzamiento integra el capitulo, que es justo lo que §3.6 pide y
lo que una entrada en `DETIENEN_LA_NOVELA` no sabria expresar.

**El contador es del capitulo, no del trabajo.** Un `FALLIDA` se relanza como
trabajo nuevo (§3.3), asi que contar por trabajo daria reparaciones infinitas:
bastaria con que el proveedor fallara una vez para que las dos vueltas de
RF-ORQ-04 volvieran a estar disponibles. Se cuenta con el maximo de la fila
`intento` **de todos los trabajos del capitulo**.

**Las tablas de otras features se leen por SQL con su nombre** —`capitulo` es de
`outline`—, que es el mismo trato que `ciclo.py` e `idempotencia.py` dan a las
suyas: una feature no entra a los ficheros internos de otra (`CLAUDE.md` §5.1).
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio
from app.features.contexto import CapituloDesconocido
from app.features.escritura.maquina import Estado, estado_de, exigir_que_la_novela_siga
from app.features.escritura.modelos import Trabajo


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """El avance de una obra: hasta que capitulo esta escrita.

    Lleva `numero` ademas de `capitulo_id` porque quien reanuda razona en
    numeros de outline —«vas por el cuatro»— y un identificador no dice cuanto
    queda. Y lleva `trabajo_id` porque es lo que ata el avance a su traza:
    RF-OBS-06 pregunta por trabajo, no por capitulo.
    """

    obra_id: int
    capitulo_id: int | None = None
    numero: int | None = None
    trabajo_id: int | None = None

    @property
    def hay_avance(self) -> bool:
        """Falso en una obra recien planificada. **No es el capitulo cero:**
        inventar un capitulo cero obligaria a todo el que lea el checkpoint a
        acordarse de que ese capitulo no existe."""
        return self.capitulo_id is not None


@dataclass(frozen=True, slots=True)
class CapituloPendiente:
    """Un capitulo del outline que todavia no esta integrado."""

    capitulo_id: int
    numero: int


@dataclass(frozen=True, slots=True)
class Arranque:
    """Lo que hace falta para empezar un capitulo, ya comprobado.

    `intento` es **el contador de este capitulo**, no el de la obra, y viene ya
    resuelto para que quien orqueste no tenga ocasion de sumar el de otro: es
    exactamente el error que R-3 nombra.
    """

    obra_id: int
    capitulo_id: int
    numero: int
    intento: int
    anterior: Checkpoint


class CheckpointPrematuro(ErrorDeDominio):
    """Se quiso anotar avance de un capitulo que no llego a `INTEGRADA`.

    «Al **integrar**» no es «al terminar»: un capitulo escalado o fallido
    tambien termina, y anotarlo haria que la reanudacion lo diera por hecho —que
    es justo la mitad de `CA-5` que dice «sin perder ninguno».
    """

    def __init__(self, trabajo_id: int, estado: Estado) -> None:
        self.trabajo_id = trabajo_id
        self.estado = estado
        super().__init__(
            f"El trabajo {trabajo_id} esta en {estado.value} y solo se anota avance "
            "al integrar el capitulo"
        )


class TrabajoSinCapitulo(ErrorDeDominio):
    """El trabajo no dice de que capitulo es, asi que su avance no es anotable.

    Se lanza en vez de no hacer nada porque un checkpoint que no se escribe es
    invisible: la reanudacion empezaria por el principio y nadie sabria por que.
    """

    def __init__(self, trabajo_id: int) -> None:
        self.trabajo_id = trabajo_id
        super().__init__(
            f"El trabajo {trabajo_id} no esta atado a ningun capitulo: sin "
            "`capitulo_id` no hay avance que anotar"
        )


class CapituloYaIntegrado(ErrorDeDominio):
    """Se pidio empezar un capitulo que ya forma parte del manuscrito.

    Es la mitad «sin duplicar» de `CA-5`: una reanudacion que rehiciera un
    capitulo integrado produciria prosa nueva sobre hechos que el Extractor ya
    escribio en el canon.
    """

    def __init__(self, obra_id: int, capitulo_id: int, numero: int) -> None:
        self.obra_id = obra_id
        self.capitulo_id = capitulo_id
        self.numero = numero
        super().__init__(
            f"El capitulo {numero} de la obra {obra_id} ya esta integrado: no se reescribe"
        )


class CapituloAnteriorSinIntegrar(ErrorDeDominio):
    """Queda un capitulo anterior por integrar. **Los diez no se paralelizan.**

    No distingue la causa —fallido, cancelado, escalado o nunca intentado— y no
    hace falta: lo que hace inseguro escribir el capitulo N+1 es el hueco, no su
    motivo. El capitulo siguiente se construiria sobre un estado en T que el
    anterior nunca produjo, y lo que falta **no se nota al escribirlo**: se nota
    tres capitulos despues, cuando ya no se sabe de donde viene el agujero.
    """

    def __init__(self, obra_id: int, numero: int, numero_pendiente: int) -> None:
        self.obra_id = obra_id
        self.numero = numero
        self.numero_pendiente = numero_pendiente
        super().__init__(
            f"No se puede empezar el capitulo {numero} de la obra {obra_id}: el "
            f"{numero_pendiente} todavia no esta integrado"
        )


async def atar_al_capitulo(sesion: AsyncSession, trabajo: Trabajo, *, capitulo_id: int) -> None:
    """Deja escrito de que capitulo es el trabajo. **Es lo que hace anotable el avance.**

    Se llama al abrir el trabajo y no al integrarlo: un trabajo que se cae a
    mitad tiene que seguir sabiendo a que capitulo pertenece, o el contador de
    reparaciones del capitulo se pondria a cero en la reanudacion y el limite de
    dos dejaria de ser un limite.

    Persiste, como `maquina.avanzar`: un `capitulo_id` que solo viva en el objeto
    no sobrevive a la caida que justifica que exista.
    """
    trabajo.capitulo_id = capitulo_id
    await sesion.commit()


async def registrar_checkpoint(sesion: AsyncSession, trabajo: Trabajo) -> Checkpoint:
    """RF-ORQ-05. Anota el avance al integrar un capitulo y devuelve el checkpoint.

    Devuelve el de la **obra** y no el de este trabajo: lo que la reanudacion
    necesita saber es por donde va la novela, y eso es el capitulo de mayor
    numero integrado, que no tiene por que ser el ultimo que se escribio.
    """
    if trabajo.capitulo_id is None:
        raise TrabajoSinCapitulo(trabajo.id)
    estado = estado_de(trabajo.estado)
    if estado is not Estado.INTEGRADA:
        raise CheckpointPrematuro(trabajo.id, estado)
    await sesion.commit()
    return await ultimo_capitulo_completado(sesion, obra_id=trabajo.obra_id)


async def ultimo_capitulo_completado(sesion: AsyncSession, *, obra_id: int) -> Checkpoint:
    """El capitulo por el que va la obra, leido de la base.

    **Ordena por `capitulo.numero` y no por `trabajo.id`**: el orden en que se
    escribio no es el orden del outline —una regeneracion rehace un capitulo del
    medio—, y un checkpoint que dijera «vas por el 1» despues de integrar el 2
    haria que la reanudacion reescribiera el 2.
    """
    fila = (
        (
            await sesion.execute(
                text(
                    "SELECT t.capitulo_id AS capitulo_id, c.numero AS numero, "
                    "       t.id AS trabajo_id "
                    "FROM trabajo AS t "
                    "JOIN capitulo AS c ON c.id = t.capitulo_id "
                    "WHERE t.obra_id = :obra_id AND t.estado = :integrada "
                    "ORDER BY c.numero DESC "
                    "LIMIT 1"
                ),
                {"obra_id": obra_id, "integrada": Estado.INTEGRADA.value},
            )
        )
        .mappings()
        .first()
    )
    if fila is None:
        return Checkpoint(obra_id=obra_id)
    return Checkpoint(
        obra_id=obra_id,
        capitulo_id=int(fila["capitulo_id"]),
        numero=int(fila["numero"]),
        trabajo_id=int(fila["trabajo_id"]),
    )


async def siguiente_capitulo(sesion: AsyncSession, *, obra_id: int) -> CapituloPendiente | None:
    """El primer capitulo del outline que no esta integrado, o `None` si no queda.

    Esto es lo que la maquina de estados **no sabe** y por lo que R-6 vivia sin
    efecto: `maquina.py` decide el siguiente estado de un capitulo y nadie
    decidia el siguiente capitulo.

    `None` significa que la novela esta escrita entera. Se pregunta por lo que
    falta y no se cuenta hasta diez: el numero de capitulos es del outline.
    """
    fila = (
        (
            await sesion.execute(
                text(
                    "SELECT c.id AS capitulo_id, c.numero AS numero "
                    "FROM capitulo AS c "
                    "WHERE c.obra_id = :obra_id AND NOT EXISTS ("
                    "  SELECT 1 FROM trabajo AS t "
                    "  WHERE t.capitulo_id = c.id AND t.estado = :integrada"
                    ") "
                    "ORDER BY c.numero "
                    "LIMIT 1"
                ),
                {"obra_id": obra_id, "integrada": Estado.INTEGRADA.value},
            )
        )
        .mappings()
        .first()
    )
    if fila is None:
        return None
    return CapituloPendiente(capitulo_id=int(fila["capitulo_id"]), numero=int(fila["numero"]))


async def reparaciones_del_capitulo(sesion: AsyncSession, *, obra_id: int, capitulo_id: int) -> int:
    """R-3. Las reparaciones gastadas **en este capitulo**, y en ninguno mas.

    El maximo y no la suma: `trabajo.intento` es un contador, no un incremento,
    y sumarlo entre el trabajo fallido y su relanzamiento escalaria a la primera
    vuelta. El maximo es lo que hace que el contador **solo crezca**, que es la
    tercera garantia de `architecture.md` §3.9.
    """
    gastadas = (
        await sesion.execute(
            text(
                "SELECT COALESCE(MAX(intento), 0) FROM trabajo "
                "WHERE obra_id = :obra_id AND capitulo_id = :capitulo_id"
            ),
            {"obra_id": obra_id, "capitulo_id": capitulo_id},
        )
    ).scalar_one()
    return int(gastadas)


async def empezar_capitulo(sesion: AsyncSession, *, obra_id: int, capitulo_id: int) -> Arranque:
    """Lo primero que se hace antes de escribir un capitulo. **R-6 y R-3 juntos.**

    Las tres comprobaciones van en este orden y no es indiferente:

    1. **La novela no esta detenida.** Es la llamada que faltaba: R-6 estaba
       probado y sin efecto en produccion porque `exigir_que_la_novela_siga` no
       tenia quien la llamara, y quien sabe cual es el capitulo siguiente es
       este fichero. Va primera porque un `ESCALADA` espera a una persona, y
       decirle «falta integrar el anterior» seria contarle la consecuencia en
       vez de la causa.
    2. **Este capitulo no esta ya integrado** (`CA-5`, «sin duplicar»).
    3. **No queda ninguno anterior por integrar** (§3.9 y CU-03).

    Y devuelve el contador **a cero** para un capitulo que nadie ha empezado,
    que es la mitad de `CA-9` que un contador global rompe.
    """
    numero = await _numero_del_capitulo(sesion, obra_id=obra_id, capitulo_id=capitulo_id)

    await exigir_que_la_novela_siga(sesion, obra_id=obra_id)

    pendiente = await siguiente_capitulo(sesion, obra_id=obra_id)
    if pendiente is None or pendiente.numero > numero:
        raise CapituloYaIntegrado(obra_id, capitulo_id, numero)
    if pendiente.numero < numero:
        raise CapituloAnteriorSinIntegrar(obra_id, numero, pendiente.numero)

    return Arranque(
        obra_id=obra_id,
        capitulo_id=capitulo_id,
        numero=numero,
        intento=await reparaciones_del_capitulo(sesion, obra_id=obra_id, capitulo_id=capitulo_id),
        anterior=await ultimo_capitulo_completado(sesion, obra_id=obra_id),
    )


async def _numero_del_capitulo(sesion: AsyncSession, *, obra_id: int, capitulo_id: int) -> int:
    """El numero de outline del capitulo, **comprobando que es de esta obra**.

    Sin el `obra_id` en el filtro, empezar el capitulo de otra obra pasaria las
    tres comprobaciones de `empezar_capitulo` contra un outline que no es el
    suyo. `CapituloDesconocido` es el error que `contexto` ya usa para esto: no
    se inventa aqui un segundo nombre para lo mismo (`CLAUDE.md` §2).
    """
    numero = (
        await sesion.execute(
            text("SELECT numero FROM capitulo WHERE id = :id AND obra_id = :obra_id"),
            {"id": capitulo_id, "obra_id": obra_id},
        )
    ).scalar_one_or_none()
    if numero is None:
        raise CapituloDesconocido(capitulo_id)
    return int(numero)
