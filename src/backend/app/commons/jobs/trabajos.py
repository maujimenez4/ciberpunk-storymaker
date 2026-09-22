"""El `trabajo` persistido y su reanudación (`architecture.md` §3.2 y §3.7).

**El estado vive en SQLite, nunca en memoria del proceso** (§3.1, punto 2). Una
caída a mitad de escena no pierde trabajo: al arrancar se leen los trabajos vivos
y se continúa.

**El orquestador persiste la salida de cada paso y la vuelve a leer**, en vez de
encadenar objetos en memoria (RF-ORQ-14). Es lo que hace que reanudar sea
idéntico a ejecutar: si el paso siguiente leyera una variable viva, reanudar
tomaría un camino distinto del normal y solo se probaría uno de los dos.

**Un paso interrumpido se repite entero**, nunca se reanuda a medias (§3.7). Es
posible porque la salida solo se persiste al completarse y porque el `run_id`
evita duplicados. El único caro de repetir es `ESCRIBIENDO`, que vuelve a pagar
la llamada; se acepta a cambio de no razonar sobre respuestas parciales.
"""

import sqlite3
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.commons.domain import Reloj
from app.commons.errors import RecursoNoEncontrado
from app.commons.jobs.estados import TERMINALES_DEFINITIVOS, Estado, exigir

MAXIMO_DE_REPARACIONES = 2


class Trabajo(BaseModel):
    """Los campos de §3.2, uno a uno."""

    model_config = ConfigDict(frozen=True)

    trabajo_id: str
    obra_id: str
    escena_id: str | None
    tipo: str
    estado: Estado
    intento: int
    run_id: str
    causa_fallo: str | None = None
    defecto_anulado_id: str | None = None
    anulado_por: str | None = None


class RepositorioDeTrabajos:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)

    def _conexion(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self.ruta)
        conexion.execute("PRAGMA foreign_keys=ON")
        return conexion

    def crear(
        self, obra_id: str, escena_id: str | None, tipo: str, reloj: Reloj
    ) -> Trabajo:
        ahora = reloj.ahora().isoformat()
        trabajo_id = f"trab-{uuid.uuid4().hex[:12]}"
        with self._conexion() as conexion:
            conexion.execute(
                "INSERT INTO trabajo (trabajo_id, obra_id, escena_id, tipo, estado,"
                " intento, run_id, creado_en, actualizado_en)"
                " VALUES (?,?,?,?,?,0,?,?,?)",
                (
                    trabajo_id,
                    obra_id,
                    escena_id,
                    tipo,
                    Estado.PLANIFICANDO.value,
                    f"run-{uuid.uuid4().hex[:12]}",
                    ahora,
                    ahora,
                ),
            )
        return self.leer(trabajo_id)

    def leer(self, trabajo_id: str) -> Trabajo:
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT trabajo_id, obra_id, escena_id, tipo, estado, intento, run_id,"
                " causa_fallo, defecto_anulado_id, anulado_por FROM trabajo"
                " WHERE trabajo_id = ?",
                (trabajo_id,),
            ).fetchone()
        if fila is None:
            raise RecursoNoEncontrado("Trabajo", trabajo_id)
        return Trabajo(
            trabajo_id=fila[0],
            obra_id=fila[1],
            escena_id=fila[2],
            tipo=fila[3],
            estado=Estado(fila[4]),
            intento=fila[5],
            run_id=fila[6],
            causa_fallo=fila[7],
            defecto_anulado_id=fila[8],
            anulado_por=fila[9],
        )

    def transitar(
        self,
        trabajo_id: str,
        hasta: Estado,
        reloj: Reloj,
        causa_fallo: str | None = None,
        incrementa_intento: bool = False,
    ) -> Trabajo:
        """Cambia de estado **y lo persiste** (RF-ORQ-04).

        La transición se valida contra la tabla antes de escribir: un salto no
        declarado es un error del orquestador, no un estado nuevo.
        """
        actual = self.leer(trabajo_id)
        exigir(actual.estado, hasta)
        intento = actual.intento + 1 if incrementa_intento else actual.intento
        with self._conexion() as conexion:
            conexion.execute(
                "UPDATE trabajo SET estado = ?, intento = ?, causa_fallo = ?,"
                " actualizado_en = ? WHERE trabajo_id = ?",
                (
                    hasta.value,
                    intento,
                    causa_fallo,
                    reloj.ahora().isoformat(),
                    trabajo_id,
                ),
            )
        return self.leer(trabajo_id)

    def registrar_anulacion(
        self, trabajo_id: str, defecto_id: str, quien: str, reloj: Reloj
    ) -> Trabajo:
        """RF-ORQ-18: sin este registro no se avanza a `EXTRAYENDO`.

        Es lo que impide que un validador equivocado deje el trabajo atrapado, y
        a la vez deja constancia de quién decidió saltarse la puerta.
        """
        with self._conexion() as conexion:
            conexion.execute(
                "UPDATE trabajo SET defecto_anulado_id = ?, anulado_por = ?,"
                " actualizado_en = ? WHERE trabajo_id = ?",
                (defecto_id, quien, reloj.ahora().isoformat(), trabajo_id),
            )
        return self.leer(trabajo_id)

    def vivos(self) -> list[Trabajo]:
        """RF-ORQ-05: los no terminales, para retomarlos al arrancar.

        `ESCALADA` **no** entra: es terminal hasta que el autor actúe. Retomarlo
        solo lo devolvería a la misma espera, y además pisaría una decisión
        humana pendiente.
        """
        terminales = ",".join("?" * len(TERMINALES_DEFINITIVOS))
        with self._conexion() as conexion:
            ids = [
                f[0]
                for f in conexion.execute(
                    f"SELECT trabajo_id FROM trabajo WHERE estado NOT IN"
                    f" ({terminales}) AND estado != ? ORDER BY creado_en",
                    (
                        *[e.value for e in sorted(TERMINALES_DEFINITIVOS)],
                        Estado.ESCALADA.value,
                    ),
                )
            ]
        return [self.leer(i) for i in ids]
