"""Acceso a datos de la feature `escena`.

Dos invariantes viven aqui y las dos son de las que se pierden en silencio:

**El texto es inmutable** (RF-ESC-03, RF-ESC-04). No hay ningun `UPDATE` sobre
`texto` en este fichero, y no debe aparecer nunca. Lo sostiene el anclaje de la
cita de un defecto: apunta a una version por desplazamiento (axioma 11), y si el
texto cambiara, la cita dejaria de ser subcadena exacta sin que nadie lo notara.

**Los dos relojes son campos distintos** (RF-ESC-05, RD-04). `orden_discurso` es
en que posicion se cuenta; `tiempo_historia`, cuando ocurre. La coherencia se
calcula por el segundo: ordenar por el primero con una analepsis daria un estado
en T equivocado, y el validador de conocimiento acusaria a un personaje de saber
algo que ya habia vivido.
"""

import json
import sqlite3
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.commons.domain import Reloj
from app.commons.errors import RecursoNoEncontrado
from app.features.escena.schemas import FichaDeEscena, FichaPersistida


class VersionDeTexto(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_texto_id: str
    escena_id: str
    texto: str
    vigente: bool
    run_id: str
    autoria: str


class EscenaPersistida(BaseModel):
    model_config = ConfigDict(frozen=True)

    escena_id: str
    capitulo_id: str
    version_obra_id: str | None
    orden_discurso: int
    tiempo_historia: str | None
    pov: str


class RepositorioDeEscenas:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)

    def _conexion(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self.ruta)
        conexion.execute("PRAGMA foreign_keys=ON")
        return conexion

    def guardar_version(
        self,
        escena_id: str,
        texto: str,
        run_id: str,
        reloj: Reloj,
        autoria: str = "generado",
    ) -> VersionDeTexto:
        """Crea una version nueva y la marca vigente. Nunca edita la anterior."""
        version_id = f"vtexto-{uuid.uuid4().hex[:12]}"
        with self._conexion() as conexion:
            # El indice unico parcial de la migracion solo admite una vigente por
            # escena, asi que hay que retirar la anterior antes de insertar. Que
            # lo imponga el motor y no solo este metodo es lo que hace que una
            # ruta futura no pueda saltarselo.
            conexion.execute(
                "UPDATE version_texto SET vigente = 0 WHERE escena_id = ?",
                (escena_id,),
            )
            conexion.execute(
                "INSERT INTO version_texto (version_texto_id, escena_id, texto,"
                " vigente, run_id, autoria, creada_en) VALUES (?,?,?,1,?,?,?)",
                (
                    version_id,
                    escena_id,
                    texto,
                    run_id,
                    autoria,
                    reloj.ahora().isoformat(),
                ),
            )
        return self.leer_version(version_id)

    def leer_version(self, version_texto_id: str) -> VersionDeTexto:
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT version_texto_id, escena_id, texto, vigente, run_id, autoria"
                " FROM version_texto WHERE version_texto_id = ?",
                (version_texto_id,),
            ).fetchone()
        if fila is None:
            raise RecursoNoEncontrado("VersionDeTexto", version_texto_id)
        return VersionDeTexto(
            version_texto_id=fila[0],
            escena_id=fila[1],
            texto=fila[2],
            vigente=bool(fila[3]),
            run_id=fila[4],
            autoria=fila[5],
        )

    def versiones_de(self, escena_id: str) -> list[VersionDeTexto]:
        with self._conexion() as conexion:
            ids = [
                f[0]
                for f in conexion.execute(
                    "SELECT version_texto_id FROM version_texto WHERE escena_id = ?"
                    " ORDER BY creada_en, rowid",
                    (escena_id,),
                )
            ]
        return [self.leer_version(i) for i in ids]

    def vigente_de(self, escena_id: str) -> VersionDeTexto:
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT version_texto_id FROM version_texto"
                " WHERE escena_id = ? AND vigente = 1",
                (escena_id,),
            ).fetchone()
        if fila is None:
            raise RecursoNoEncontrado("VersionDeTexto vigente de", escena_id)
        return self.leer_version(fila[0])

    def _escenas(
        self, consulta: str, parametros: tuple[str, ...]
    ) -> list[EscenaPersistida]:
        with self._conexion() as conexion:
            filas = conexion.execute(consulta, parametros).fetchall()
        return [
            EscenaPersistida(
                escena_id=f[0],
                capitulo_id=f[1],
                version_obra_id=f[2],
                orden_discurso=f[3],
                tiempo_historia=f[4],
                pov=f[5],
            )
            for f in filas
        ]

    _COLUMNAS = (
        "SELECT escena_id, capitulo_id, version_obra_id, orden_discurso,"
        " tiempo_historia, pov FROM escena"
    )

    def leer_escena(self, escena_id: str) -> EscenaPersistida:
        escenas = self._escenas(f"{self._COLUMNAS} WHERE escena_id = ?", (escena_id,))
        if not escenas:
            raise RecursoNoEncontrado("Escena", escena_id)
        return escenas[0]

    def escenas_por_orden_discurso(self, capitulo_id: str) -> list[EscenaPersistida]:
        """En que orden se **cuentan**."""
        return self._escenas(
            f"{self._COLUMNAS} WHERE capitulo_id = ? ORDER BY orden_discurso",
            (capitulo_id,),
        )

    def escenas_por_tiempo_historia(self, capitulo_id: str) -> list[EscenaPersistida]:
        """En que orden **ocurren**. Es el que vale para derivar estado."""
        return self._escenas(
            f"{self._COLUMNAS} WHERE capitulo_id = ? ORDER BY tiempo_historia",
            (capitulo_id,),
        )

    def ficha_de(self, escena_id: str) -> FichaPersistida:
        """Los campos de ficha de la fila, con las listas ya deserializadas.

        `presentes` y `mencionados` se guardan como JSON y pueden ser `NULL`
        cuando la escena viene del outline y aun no se ha planificado. Se
        devuelven como lista vacia: un `None` aqui obligaria a un `if` en cada
        uso y acabaria colandose uno sin el.
        """
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT escena_id, capitulo_id, orden_discurso, tiempo_historia,"
                " pov, lugar, presentes, mencionados, objetivo_del_pov, obstaculo,"
                " resultado, valor_entrada, valor_salida, extension_objetivo,"
                " densidad_de_dialogo_objetivo, distancia_psiquica, beat_de_genero"
                " FROM escena WHERE escena_id = ?",
                (escena_id,),
            ).fetchone()
        if fila is None:
            raise RecursoNoEncontrado("Escena", escena_id)
        return FichaPersistida(
            escena_id=fila[0],
            capitulo_id=fila[1],
            orden_discurso=fila[2],
            tiempo_historia=fila[3],
            pov=fila[4],
            lugar=fila[5],
            presentes=json.loads(fila[6]) if fila[6] else [],
            mencionados=json.loads(fila[7]) if fila[7] else [],
            objetivo_del_pov=fila[8],
            obstaculo=fila[9],
            resultado=fila[10],
            valor_entrada=fila[11],
            valor_salida=fila[12],
            extension_objetivo=fila[13],
            densidad_de_dialogo_objetivo=fila[14],
            distancia_psiquica=fila[15],
            beat_de_genero=fila[16],
        )

    def guardar_ficha(self, ficha: FichaDeEscena) -> None:
        """RF-ESC-01: lo que el Planificador decidio queda en la fila.

        Actualiza **solo** los campos que la ficha propone. `mencionados`,
        `tiempo_historia` y el resto los pone quien corresponda, y pisarlos con
        un `None` aqui borraria en silencio lo que el outline ya sabia.

        Sin esta escritura, la capa de instruccion del paquete sale de la ficha
        gruesa del outline en vez de la del Planificador, y el Escritor recibe
        menos de lo que se decidio para el.
        """
        with self._conexion() as conexion:
            conexion.execute(
                "UPDATE escena SET pov = ?, presentes = ?, lugar = ?,"
                " objetivo_del_pov = ?, obstaculo = ?, valor_entrada = ?,"
                " valor_salida = ?, distancia_psiquica = ?,"
                " densidad_de_dialogo_objetivo = ?, extension_objetivo = ?"
                " WHERE escena_id = ?",
                (
                    ficha.pov,
                    json.dumps(ficha.presentes),
                    ficha.lugar,
                    ficha.objetivo_del_pov,
                    ficha.obstaculo,
                    ficha.valor_entrada,
                    ficha.valor_salida,
                    ficha.distancia_psiquica,
                    ficha.densidad_de_dialogo_objetivo,
                    ficha.extension_objetivo,
                    ficha.escena_id,
                ),
            )
