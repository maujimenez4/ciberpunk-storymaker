"""Los almacenes reales detrás del Ensamblador (§4.8, RF-CTX-02).

`recoleccion.py` declara `Almacenes` como `Protocol` con **un método por capa**,
y ese uno a uno es lo que hace comprobable que ninguna capa se quede sin origen.
Hasta hoy no lo implementaba nadie: el ensamblador estaba escrito y probado
contra dobles, y `corrida.py` se fabricaba las siete capas con cadenas fijas. De
ahí el síntoma que el Cierre de la spec 001 anotó sin explicar —el canon
aportaba 36 tokens de media al paquete—: **la memoria se escribía y no se leía**.

Esta clase es ese cableado y nada más. No decide qué cabe ni qué se recorta: eso
es `service.py`, y separarlo es lo que permite probar el presupuesto sin base de
datos y la lectura sin contador.

Se entra a cada feature por su `__init__.py`, que es lo que §5.2 regla 1 permite;
`import-linter` lo verifica en la build.
"""

from pathlib import Path

from app.commons.errors import RecursoNoEncontrado
from app.features.canon import RepositorioDeCanon
from app.features.escena import EscenaPersistida, RepositorioDeEscenas
from app.features.obra import RepositorioDeObras
from app.features.outline import RepositorioDeOutline

# §4.2 trabaja con la escena anterior y la penúltima. Un evento nacido en esas
# dos es «reciente»; el resto es conocimiento antiguo, que §2.1 manda ceder
# primero dentro de la capa de estado.
VENTANA_RECIENTE = 2


class AlmacenesDeLaObra:
    """Implementa `Almacenes` contra las tablas reales de una obra."""

    def __init__(self, ruta: Path | str) -> None:
        self.obras = RepositorioDeObras(ruta)
        self.outline = RepositorioDeOutline(ruta)
        self.escenas = RepositorioDeEscenas(ruta)
        self.canon = RepositorioDeCanon(ruta)

    # --- capa constitucional -------------------------------------------------

    def biblia_y_discurso(self, escena_id: str) -> list[str]:
        ubicacion = self.outline.ubicacion_de(escena_id)
        obra = self.obras.leer(ubicacion.obra_id)
        piezas = [
            f"Obra «{obra.titulo}». Persona {obra.persona}, tiempo verbal "
            f"{obra.tiempo_verbal}, esquema de POV {obra.esquema_de_pov}, "
            f"nivel de calor {obra.nivel_de_calor.value}."
        ]

        escena = self.escenas.leer_escena(escena_id)
        if escena.version_obra_id is None:
            return piezas

        # La escena recuerda con qué versión de biblia se escribió (RF-ESC-06),
        # así que se lee **esa** y no la vigente: si no, una escena antigua
        # traería al paquete un canon que no existía cuando se escribió.
        biblia = self.obras.leer_version(escena.version_obra_id).biblia
        piezas.append(f"Tropo: {biblia.tropo}.")
        piezas.append(f"Promesa de apertura: {biblia.promesa_de_apertura}")
        piezas += [
            f"{p.nombre} ({p.pj_id}), {p.rol_narrativo.value}, {p.edad} años."
            for p in biblia.personajes
        ]
        piezas += [f"Lugar {p.nombre} ({p.lug_id})." for p in biblia.lugares]
        piezas += [
            f"De {d.origen_id} a {d.destino_id}: {d.tiempo_de_viaje}."
            for d in biblia.distancias
        ]
        piezas += [f"Regla del mundo: {r.enunciado}" for r in biblia.reglas_de_mundo]
        return piezas

    # --- capa estructural ----------------------------------------------------

    def outline_del_capitulo(self, escena_id: str) -> list[str]:
        ubicacion = self.outline.ubicacion_de(escena_id)
        piezas = [
            f"Parte {ubicacion.funcion_estructural}. Capítulo "
            f"{ubicacion.capitulo_numero}: {ubicacion.capitulo_titulo}."
        ]
        for escena in self.escenas.escenas_por_orden_discurso(ubicacion.capitulo_id):
            ficha = self.escenas.ficha_de(escena.escena_id)
            piezas.append(
                f"Escena {ficha.orden_discurso} (POV {ficha.pov}) en "
                f"{ficha.lugar or 'lugar sin declarar'}: beat "
                f"{ficha.beat_de_genero or 'sin beat'}."
            )
        return piezas

    # --- capa de canon relevante ---------------------------------------------

    def canon_relevante(self, escena_id: str) -> list[tuple[str, bool]]:
        """`(texto, esta_presente)`. §2.1 cede primero a los mencionados."""
        ficha = self.escenas.ficha_de(escena_id)
        presentes = set(ficha.presentes)
        return [
            (
                f"{hecho.entidad}: {hecho.atributo} = {hecho.valor} "
                f"(establecido en {hecho.escena_de_origen})",
                hecho.entidad in presentes,
            )
            for hecho in self.canon.hechos_hasta(ficha.orden_discurso)
        ]

    # --- capa de estado en T -------------------------------------------------

    def estado_en_t(self, escena_id: str) -> list[tuple[str, bool]]:
        """`(texto, es_reciente)`. §2.1 cede primero lo antiguo ya usado.

        El conocimiento sale de `testigos`, no de `participantes` (RF-CAN-11):
        estar en una escena no es haberse enterado.
        """
        ficha = self.escenas.ficha_de(escena_id)
        salida: list[tuple[str, bool]] = []
        for evento in self.canon.eventos_hasta(ficha.orden_discurso):
            # Un evento sin escena de origen no deberia existir -el ledger la
            # exige- pero el modelo la declara opcional. Se trata como antiguo
            # en vez de reventar: perder recencia degrada el recorte, reventar
            # deja la escena sin escribir.
            reciente = False
            if evento.escena_de_origen is not None:
                orden = self.canon.orden_de(evento.escena_de_origen)
                reciente = orden >= ficha.orden_discurso - VENTANA_RECIENTE
            testigos = ", ".join(evento.testigos) or "nadie"
            salida.append((f"{testigos} sabe: {evento.descripcion}", reciente))
        return salida

    # --- capa de continuidad local -------------------------------------------

    def escena_anterior_integra(self, escena_id: str) -> str | None:
        anterior = self._vecina(escena_id, atras=1)
        if anterior is None:
            return None
        try:
            return self.escenas.vigente_de(anterior.escena_id).texto
        except RecursoNoEncontrado:
            # La escena existe en el outline pero aún no se ha escrito. Que la
            # capa quede vacía es asunto de RF-CTX-14; inventarse un texto sería
            # peor, porque el Escritor creería que hubo una escena.
            return None

    def resumen_de_la_penultima(self, escena_id: str) -> str | None:
        penultima = self._vecina(escena_id, atras=2)
        if penultima is None:
            return None
        return self.canon.resumen_de("escena", penultima.escena_id)

    # --- capa de memoria recuperada ------------------------------------------

    def fragmentos_candidatos(self, escena_id: str, tope: int) -> dict[str, str]:
        """Ya filtrados por el filtro estructural (§4.6, paso 1)."""
        return self.canon.candidatos_para_ordenar(tope)

    def muestras_ancla(self, escena_id: str, cuantas: int) -> list[str]:
        """Escenas anteriores del **mismo POV**, que es lo que contiene la
        deriva de voz (RF-CTX-08)."""
        ficha = self.escenas.ficha_de(escena_id)
        salida: list[str] = []
        for escena in self.escenas.escenas_por_orden_discurso(ficha.capitulo_id):
            if escena.orden_discurso >= ficha.orden_discurso or escena.pov != ficha.pov:
                continue
            try:
                salida.append(self.escenas.vigente_de(escena.escena_id).texto)
            except RecursoNoEncontrado:
                continue
            if len(salida) >= cuantas:
                break
        return salida

    # --- capa de instrucción -------------------------------------------------

    def instruccion(self, escena_id: str) -> list[str]:
        ficha = self.escenas.ficha_de(escena_id)
        piezas = [
            f"Escribe la escena {ficha.orden_discurso}, POV {ficha.pov}, en "
            f"{ficha.lugar or 'el lugar que declare la ficha'}."
        ]
        if ficha.objetivo_del_pov:
            piezas.append(f"Objetivo del POV: {ficha.objetivo_del_pov}.")
        if ficha.obstaculo:
            piezas.append(f"Obstáculo: {ficha.obstaculo}.")
        if ficha.valor_entrada and ficha.valor_salida:
            piezas.append(
                f"Giro de valor: de {ficha.valor_entrada} a {ficha.valor_salida}."
            )
        if ficha.presentes:
            piezas.append(f"Presentes: {', '.join(ficha.presentes)}.")
        if ficha.extension_objetivo:
            piezas.append(f"Extensión objetivo: {ficha.extension_objetivo} palabras.")
        return piezas

    # --- interno -------------------------------------------------------------

    def _vecina(self, escena_id: str, atras: int) -> EscenaPersistida | None:
        """La escena `atras` posiciones antes, dentro del mismo capítulo."""
        ficha = self.escenas.ficha_de(escena_id)
        objetivo = ficha.orden_discurso - atras
        for escena in self.escenas.escenas_por_orden_discurso(ficha.capitulo_id):
            if escena.orden_discurso == objetivo:
                return escena
        return None
