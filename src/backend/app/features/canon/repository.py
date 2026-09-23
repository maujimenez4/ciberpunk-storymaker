"""Acceso a la memoria de largo plazo: canon, ledger, snapshots.

Tres cosas **no** existen en este fichero, y su ausencia es el diseño:

- Ningun evento se actualiza ni se borra: el ledger es *append-only*
  (RF-CAN-05), y ademas lo impone un disparador de la migracion, asi que ni una
  consulta suelta puede romperlo. Hay un test que busca esas dos sentencias en
  este fichero, asi que no se nombran ni en los comentarios.
- No hay forma de escribir `EstadoEnT`. Se deriva (RF-CAN-06). Una tabla de
  estado editable se desincroniza del texto ya escrito y nadie se entera hasta
  que una escena contradice a otra diez capitulos despues.
- No hay `compactar` ni `purgar`. El canon y el ledger no se compactan nunca
  (RF-CAN-09): el olvido de este sistema es de seleccion —un hecho deja de ser
  relevante y no entra en el paquete—, no de destruccion.

Corregir un hecho tampoco lo edita: registra uno nuevo que cita al anterior
(RF-CAN-07), y eso invalida los *snapshots* posteriores (RF-CAN-13).
"""

import sqlite3
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from app.commons.domain import Reloj

if TYPE_CHECKING:
    from app.features.canon.schemas import Extraccion


class HechoCanon(BaseModel):
    model_config = ConfigDict(frozen=True)

    hc_id: str
    entidad: str
    atributo: str
    valor: str
    escena_de_origen: str
    sustituye_a: str | None = None


class Evento(BaseModel):
    model_config = ConfigDict(frozen=True)

    evt_id: str
    descripcion: str
    escena_de_origen: str | None
    testigos: list[str]
    participantes: list[str]


class RepositorioDeCanon:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)

    def _conexion(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self.ruta)
        conexion.execute("PRAGMA foreign_keys=ON")
        return conexion

    def ejecutar_sql_crudo(self, sentencia: str) -> None:
        """Solo para pruebas: comprobar que el motor rechaza lo prohibido."""
        with self._conexion() as conexion:
            conexion.execute(sentencia)

    # --- ledger --------------------------------------------------------------

    def registrar_evento(
        self,
        serie_id: str,
        escena_de_origen: str,
        descripcion: str,
        testigos: list[str] | None = None,
        participantes: list[str] | None = None,
    ) -> Evento:
        import json

        evt_id = f"evt-{uuid.uuid4().hex[:12]}"
        with self._conexion() as conexion:
            conexion.execute(
                "INSERT INTO evento (evt_id, serie_id, descripcion, escena_de_origen,"
                " testigos, participantes) VALUES (?,?,?,?,?,?)",
                (
                    evt_id,
                    serie_id,
                    descripcion,
                    escena_de_origen,
                    json.dumps(testigos or []),
                    json.dumps(participantes or []),
                ),
            )
        return Evento(
            evt_id=evt_id,
            descripcion=descripcion,
            escena_de_origen=escena_de_origen,
            testigos=testigos or [],
            participantes=participantes or [],
        )

    def eventos_hasta(self, orden_discurso: int) -> list[Evento]:
        """Los eventos de escenas **anteriores** a la dada, en orden.

        Estrictamente anteriores: el estado en T es el de justo antes de la
        escena, no el de despues de escribirla.
        """
        import json

        with self._conexion() as conexion:
            filas = conexion.execute(
                "SELECT e.evt_id, e.descripcion, e.escena_de_origen, e.testigos,"
                " e.participantes FROM evento e JOIN escena s"
                " ON s.escena_id = e.escena_de_origen"
                " WHERE s.orden_discurso < ? ORDER BY s.orden_discurso",
                (orden_discurso,),
            ).fetchall()
        return [
            Evento(
                evt_id=f[0],
                descripcion=f[1],
                escena_de_origen=f[2],
                testigos=json.loads(f[3] or "[]"),
                participantes=json.loads(f[4] or "[]"),
            )
            for f in filas
        ]

    def orden_de(self, escena_id: str) -> int:
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT orden_discurso FROM escena WHERE escena_id = ?", (escena_id,)
            ).fetchone()
        if fila is None:
            from app.commons.errors import RecursoNoEncontrado

            raise RecursoNoEncontrado("Escena", escena_id)
        return int(fila[0])

    # --- canon ---------------------------------------------------------------

    def registrar_hecho(
        self,
        serie_id: str,
        escena_de_origen: str,
        entidad: str,
        atributo: str,
        valor: str,
        sustituye_a: str | None = None,
    ) -> HechoCanon:
        """RF-CAN-04: todo hecho cita la escena que lo establecio."""
        hc_id = f"hc-{uuid.uuid4().hex[:12]}"
        with self._conexion() as conexion:
            conexion.execute(
                "INSERT INTO hecho_canon (hc_id, serie_id, entidad, atributo, valor,"
                " escena_de_origen, sustituye_a) VALUES (?,?,?,?,?,?,?)",
                (
                    hc_id,
                    serie_id,
                    entidad,
                    atributo,
                    valor,
                    escena_de_origen,
                    sustituye_a,
                ),
            )
        return HechoCanon(
            hc_id=hc_id,
            entidad=entidad,
            atributo=atributo,
            valor=valor,
            escena_de_origen=escena_de_origen,
            sustituye_a=sustituye_a,
        )

    def leer_hecho(self, hc_id: str) -> HechoCanon:
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT hc_id, entidad, atributo, valor, escena_de_origen, sustituye_a"
                " FROM hecho_canon WHERE hc_id = ?",
                (hc_id,),
            ).fetchone()
        if fila is None:
            from app.commons.errors import RecursoNoEncontrado

            raise RecursoNoEncontrado("HechoCanon", hc_id)
        return HechoCanon(
            hc_id=fila[0],
            entidad=fila[1],
            atributo=fila[2],
            valor=fila[3],
            escena_de_origen=fila[4],
            sustituye_a=fila[5],
        )

    def sustituir_hecho(
        self,
        serie_id: str,
        escena_de_origen: str,
        hc_id_anterior: str,
        entidad: str,
        atributo: str,
        valor: str,
    ) -> HechoCanon:
        """RF-CAN-07: corregir **no edita**, registra uno nuevo que cita al viejo.

        Y RF-CAN-13: invalida los *snapshots* posteriores a la escena de origen
        del **sustituido**, no del nuevo. Esa es la escena a partir de la cual el
        estado derivado empezo a mentir.
        """
        anterior = self.leer_hecho(hc_id_anterior)
        nuevo = self.registrar_hecho(
            serie_id, escena_de_origen, entidad, atributo, valor, hc_id_anterior
        )
        self.invalidar_snapshots_posteriores_a(anterior.escena_de_origen)
        return nuevo

    # --- snapshots: cache del estado derivado, nunca su origen ---------------

    def crear_snapshot_si_toca(self, escena_id: str, cada_n: int, reloj: Reloj) -> bool:
        """Devuelve si lo creo. Cada N escenas de `orden_discurso` (D-01: N=5)."""
        import json

        orden = self.orden_de(escena_id)
        if orden % cada_n != 0:
            return False
        estado = derivar_estado_en_t(self, escena_id)
        with self._conexion() as conexion:
            conexion.execute(
                "INSERT OR REPLACE INTO snapshot_estado_en_t (snapshot_id, escena_id,"
                " estado, valido, creado_en) VALUES (?,?,?,1,?)",
                (
                    f"snap-{uuid.uuid4().hex[:10]}",
                    escena_id,
                    json.dumps(estado.conocimientos),
                    reloj.ahora().isoformat(),
                ),
            )
        return True

    def invalidar_snapshots_posteriores_a(self, escena_id: str) -> int:
        """Se marcan, no se borran: la traza de que existieron tambien importa."""
        orden = self.orden_de(escena_id)
        with self._conexion() as conexion:
            cursor = conexion.execute(
                "UPDATE snapshot_estado_en_t SET valido = 0 WHERE escena_id IN"
                " (SELECT escena_id FROM escena WHERE orden_discurso > ?)",
                (orden,),
            )
            return cursor.rowcount

    def snapshot_valido_en(self, escena_id: str) -> bool | None:
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT valido FROM snapshot_estado_en_t WHERE escena_id = ?",
                (escena_id,),
            ).fetchone()
        return None if fila is None else bool(fila[0])

    # --- consolidacion: el paso EXTRAYENDO, en una transaccion ---------------

    def consolidar(
        self,
        serie_id: str,
        escena_id: str,
        version_texto_id: str,
        extraccion: "Extraccion",
        reloj: Reloj,
    ) -> None:
        """RF-CAN-03: o entra el conjunto, o no entra nada.

        Una sola conexion y una sola transaccion. Si algo revienta a mitad
        -en el ultimo paso, al fragmentar-, el canon y el ledger ya escritos se
        deshacen con ella.
        """
        import json

        conexion = self._conexion()
        try:
            with conexion:
                for hecho in extraccion.hechos:  # 1. canon
                    conexion.execute(
                        "INSERT INTO hecho_canon (hc_id, serie_id, entidad, atributo,"
                        " valor, escena_de_origen) VALUES (?,?,?,?,?,?)",
                        (
                            f"hc-{uuid.uuid4().hex[:12]}",
                            serie_id,
                            hecho.entidad,
                            hecho.atributo,
                            hecho.valor,
                            escena_id,
                        ),
                    )
                for evento in extraccion.eventos:  # 2. ledger
                    conexion.execute(
                        "INSERT INTO evento (evt_id, serie_id, descripcion,"
                        " escena_de_origen, testigos, participantes)"
                        " VALUES (?,?,?,?,?,?)",
                        (
                            f"evt-{uuid.uuid4().hex[:12]}",
                            serie_id,
                            evento.descripcion,
                            escena_id,
                            json.dumps(evento.testigos),
                            json.dumps(evento.participantes),
                        ),
                    )
                conexion.execute(  # 3. resumen
                    "INSERT OR REPLACE INTO resumen (resumen_id, nivel,"
                    " referencia_id, texto) VALUES (?,?,?,?)",
                    (
                        f"res-{uuid.uuid4().hex[:10]}",
                        "escena",
                        escena_id,
                        extraccion.resumen,
                    ),
                )
                for hilo in extraccion.hilos:  # 4. hilos
                    conexion.execute(
                        "INSERT INTO hilo_narrativo (hilo_id, pregunta,"
                        " escena_de_apertura, estado) VALUES (?,?,?,?)",
                        (
                            f"hilo-{uuid.uuid4().hex[:10]}",
                            hilo.pregunta,
                            escena_id,
                            hilo.estado,
                        ),
                    )
                for plantado in extraccion.plantados:
                    conexion.execute(
                        "INSERT INTO plantado (plantado_id, escena_de_origen,"
                        " importancia) VALUES (?,?,?)",
                        (
                            f"pl-{uuid.uuid4().hex[:10]}",
                            escena_id,
                            plantado.importancia,
                        ),
                    )
                obra_id = conexion.execute(
                    "SELECT p.obra_id FROM escena e JOIN capitulo c"
                    " ON c.capitulo_id = e.capitulo_id JOIN parte p"
                    " ON p.parte_id = c.parte_id WHERE e.escena_id = ?",
                    (escena_id,),
                ).fetchone()[0]
                for ngrama in extraccion.ngramas_gastados:  # RD-13
                    conexion.execute(
                        "INSERT OR IGNORE INTO ngrama_vetado (ngrama, obra_id)"
                        " VALUES (?,?)",
                        (ngrama, obra_id),
                    )
                texto = conexion.execute(
                    "SELECT texto FROM version_texto WHERE version_texto_id = ?",
                    (version_texto_id,),
                ).fetchone()[0]
                conexion.execute(  # 5. fragmentos
                    "INSERT INTO fragmento (fragmento_id, version_texto_id, texto)"
                    " VALUES (?,?,?)",
                    (f"frag-{uuid.uuid4().hex[:10]}", version_texto_id, texto),
                )
        finally:
            conexion.close()

    # --- consultas ------------------------------------------------------------

    def hechos_de_escena(self, escena_id: str) -> list[HechoCanon]:
        with self._conexion() as conexion:
            ids = [
                f[0]
                for f in conexion.execute(
                    "SELECT hc_id FROM hecho_canon WHERE escena_de_origen = ?"
                    " ORDER BY rowid",
                    (escena_id,),
                )
            ]
        return [self.leer_hecho(i) for i in ids]

    def hechos_hasta(self, orden_discurso: int) -> list[HechoCanon]:
        """Los hechos **vigentes** establecidos antes de esa escena (§4.8).

        Estrictamente anteriores, igual que `eventos_hasta`: el canon de una
        escena es el de justo antes de escribirla.

        Y solo los vigentes. Corregir no edita (RF-CAN-07): registra un hecho
        nuevo que cita al viejo por `sustituye_a`. Devolver el sustituido
        meteria en el paquete la afirmacion que el canon ya desmintio, y el
        Escritor la trataria como verdad porque no tiene forma de saber que no
        lo es: solo ve el paquete.
        """
        with self._conexion() as conexion:
            ids = [
                f[0]
                for f in conexion.execute(
                    "SELECT h.hc_id FROM hecho_canon h"
                    " JOIN escena s ON s.escena_id = h.escena_de_origen"
                    " WHERE s.orden_discurso < ?"
                    " AND h.hc_id NOT IN (SELECT sustituye_a FROM hecho_canon"
                    " WHERE sustituye_a IS NOT NULL)"
                    " ORDER BY s.orden_discurso, h.rowid",
                    (orden_discurso,),
                )
            ]
        return [self.leer_hecho(i) for i in ids]

    def hechos_de_obra(
        self,
        obra_id: str,
        entidad: str | None = None,
        atributo: str | None = None,
    ) -> list[HechoCanon]:
        """RI-08: el canon de una obra, filtrable, y **solo lo vigente**.

        Sube de la escena a la obra por el mismo camino que `outline`, porque
        `hecho_canon` cuelga de la serie (RD-11) y la v1 tiene una sola. Un
        hecho sustituido no sale: quien consulta el canon quiere saber que es
        verdad ahora, no que se llego a creer (RF-CAN-07).
        """
        condiciones = ["p.obra_id = ?"]
        parametros: list[str] = [obra_id]
        if entidad:
            condiciones.append("h.entidad = ?")
            parametros.append(entidad)
        if atributo:
            condiciones.append("h.atributo = ?")
            parametros.append(atributo)

        with self._conexion() as conexion:
            ids = [
                f[0]
                for f in conexion.execute(
                    "SELECT h.hc_id FROM hecho_canon h"
                    " JOIN escena e ON e.escena_id = h.escena_de_origen"
                    " JOIN capitulo c ON c.capitulo_id = e.capitulo_id"
                    " JOIN parte p ON p.parte_id = c.parte_id"
                    f" WHERE {' AND '.join(condiciones)}"
                    " AND h.hc_id NOT IN (SELECT sustituye_a FROM hecho_canon"
                    " WHERE sustituye_a IS NOT NULL)"
                    " ORDER BY e.orden_discurso, h.rowid",
                    tuple(parametros),
                )
            ]
        return [self.leer_hecho(i) for i in ids]

    def eventos_de_escena(self, escena_id: str) -> list[str]:
        with self._conexion() as conexion:
            return [
                f[0]
                for f in conexion.execute(
                    "SELECT descripcion FROM evento WHERE escena_de_origen = ?",
                    (escena_id,),
                )
            ]

    def resumen_de(self, nivel: str, referencia_id: str) -> str | None:
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT texto FROM resumen WHERE nivel = ? AND referencia_id = ?",
                (nivel, referencia_id),
            ).fetchone()
        return None if fila is None else str(fila[0])

    def hilos_abiertos(self) -> list[str]:
        with self._conexion() as conexion:
            return [
                f[0]
                for f in conexion.execute(
                    "SELECT pregunta FROM hilo_narrativo WHERE estado = ?",
                    ("abierto",),
                )
            ]

    def ngramas_vetados(self, obra_id: str) -> list[str]:
        with self._conexion() as conexion:
            return [
                f[0]
                for f in conexion.execute(
                    "SELECT ngrama FROM ngrama_vetado WHERE obra_id = ?", (obra_id,)
                )
            ]

    def fragmentos_de(self, escena_id: str) -> list[str]:
        with self._conexion() as conexion:
            return [
                f[0]
                for f in conexion.execute(
                    "SELECT f.texto FROM fragmento f JOIN version_texto v"
                    " ON v.version_texto_id = f.version_texto_id"
                    " WHERE v.escena_id = ? ORDER BY f.rowid",
                    (escena_id,),
                )
            ]

    def reconstruir_fragmentos(self) -> int:
        """RF-CAN-12: los fragmentos se rehacen enteros desde el texto aprobado.

        Sigue valiendo sin vectores: garantiza que el indice nunca es una fuente
        de verdad paralela al manuscrito.
        """
        with self._conexion() as conexion:
            vigentes = conexion.execute(
                "SELECT version_texto_id, texto FROM version_texto WHERE vigente = 1"
            ).fetchall()
            conexion.execute("DELETE FROM fragmento")
            for version_texto_id, texto in vigentes:
                conexion.execute(
                    "INSERT INTO fragmento (fragmento_id, version_texto_id, texto)"
                    " VALUES (?,?,?)",
                    (f"frag-{uuid.uuid4().hex[:10]}", version_texto_id, texto),
                )
        return len(vigentes)

    def candidatos_para_ordenar(self, tope: int) -> dict[str, str]:
        """Los fragmentos que vera el ordenador semantico (RNF-REN-04).

        El filtro estructural va antes y hace el trabajo pesado; esto solo pone
        el techo, para que el coste del ensamblado no crezca con la obra.
        """
        with self._conexion() as conexion:
            return {
                f[0]: f[1]
                for f in conexion.execute(
                    "SELECT fragmento_id, texto FROM fragmento"
                    " ORDER BY rowid DESC LIMIT ?",
                    (tope,),
                )
            }


class EstadoEnT(BaseModel):
    """Vista derivada, nunca una tabla que se edita (RF-CAN-06)."""

    model_config = ConfigDict(frozen=True)

    escena_id: str
    conocimientos: dict[str, list[str]]

    def sabe(self, pj_id: str) -> list[str]:
        return self.conocimientos.get(pj_id, [])


def derivar_estado_en_t(repositorio: RepositorioDeCanon, escena_id: str) -> EstadoEnT:
    """Aplica en orden los eventos anteriores a la escena (RF-CAN-06).

    El conocimiento sale de `testigos[]` y no de `participantes[]` (RF-CAN-11):
    estar en una escena no es haberse enterado. Es la distincion que hace
    detectable el defecto CON-03.
    """
    orden = repositorio.orden_de(escena_id)
    conocimientos: dict[str, list[str]] = {}
    for evento in repositorio.eventos_hasta(orden):
        for testigo in evento.testigos:
            conocimientos.setdefault(testigo, []).append(evento.descripcion)
    return EstadoEnT(escena_id=escena_id, conocimientos=conocimientos)
