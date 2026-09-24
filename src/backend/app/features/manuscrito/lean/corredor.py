"""Correr Lean sobre la cronologia de una obra. `RF-FOR-02`, R-3, R-5, R-7.

Junta la plantilla fija con los datos generados, lo escribe en un temporal y se
lo da al compilador. **Un invariante incumplido no compila**, y eso es la puerta:
no hay informe que alguien tenga que leer, hay un proceso que devuelve error.

## Por que `lean` y no `lake build`

El plan dice `lake build`. Medido en esta maquina, sobre un fichero
autocontenido -- sin Mathlib, sin dependencias, sin proyecto --:

    lake build, proyecto de ejemplo   13,1 s en frio · 3,4 s incremental
    lean, fichero suelto, 2 eventos    1,1 s en caliente
    lean, fichero suelto, 40 eventos   2,4 s en caliente

Cuarenta eventos son una novela de diez capitulos con cuatro personajes por
escena. `lake` existe para resolver dependencias y aqui no hay ninguna que
resolver: montar un proyecto por publicacion seria pagar su arranque para nada.
`formal/lean/` sigue compilando con `lake build` y es donde vive el proyecto;
esto es la puerta, y corre en cada publicacion.

Queda anotado como **desviacion del plan**, no como decision en silencio.

## Quien dice que fallo, y quien dice quien

**Lean decide.** Si `decide` prueba que la proposicion es falsa, no compila, y
eso es todo lo que hace falta para no publicar.

**Python explica.** El error de Lean dice que la proposicion es falsa y no dice
de quien: con indices dentro, tampoco podria decir un nombre. Asi que, cuando
Lean rechaza, se recorre el mismo dato -- que lo produjo este proceso, con sus
tablas de nombres -- para encontrar el par culpable y nombrarlo. La fuente de
verdad del si o no es Lean; el nombre es una comodidad para quien lo lee, y si
las dos discreparan **manda Lean**: el fallo se reporta igual, sin nombre.
"""

import asyncio
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.manuscrito.lean.generador import generar_lean

PLANTILLA = Path(__file__).with_name("plantilla.lean")

TEOREMAS = """
-- Las dos pruebas. Si alguna es falsa, esto **no compila**, y sin compilar no
-- se publica. No hay informe intermedio que alguien pueda pasar por alto.
theorem cronologia_sin_ubicuidad : sinUbicuidad eventos = true := by decide
theorem cronologia_sin_reaparecidos : sinReaparecidos eventos exclusiones = true := by decide
"""

_EJECUTABLE = "lean"

_DONDE_LO_DEJA_ELAN = Path.home() / ".elan" / "bin"
"""elan instala `lean` aqui y **no siempre lo deja en el PATH** del proceso.

No es una comodidad para las pruebas. `shutil.which("lean")` devolviendo `None`
en una maquina que **si** tiene Lean instalado bloquearia todas las
publicaciones con «falta Lean»: el servicio corre con el PATH que le den, no con
el del terminal donde alguien instalo elan. Se mira el PATH primero -- quien lo
ponga ahi manda -- y esto es el respaldo.
"""

_ESPERA_MAXIMA_S = 120.0
"""Medido: 2,4 s con 40 eventos. Ciento veinte es margen para una maquina fria
-- la primera invocacion de `lean` tras instalar elan tardo 28 s -- sin dejar
una publicacion colgada para siempre si algo se atasca."""


class HerramientaNoDisponible(RuntimeError):
    """No hay `lean` en el PATH. R-7.

    Un `FileNotFoundError: 'lean'` crudo en mitad de una publicacion no le dice
    a nadie que le falta instalar Lean 4, y ese «nadie» es quien clona el
    repositorio para corregir el examen.
    """

    def __init__(self) -> None:
        super().__init__(
            "Falta Lean 4: no se encuentra `lean` ni `lake` en el PATH. "
            "Se instala con elan (https://github.com/leanprover/elan) y la version "
            "la fija `formal/lean/lean-toolchain`. Sin el no se puede publicar: la "
            "cronologia se verifica antes de cada publicacion (encargo §5c)."
        )


def ruta_de_lean() -> str | None:
    """Donde esta `lean`, o `None`. PATH primero, elan como respaldo.

    Es funcion publica porque la comprueba tambien quien decide si saltarse un
    test: preguntar por `shutil.which` alli y usar otra cosa aqui daria tests
    que se saltan en una maquina donde la puerta si funciona -- o al reves, que
    es peor.
    """
    en_el_path = shutil.which(_EJECUTABLE)
    if en_el_path is not None:
        return en_el_path
    candidato = _DONDE_LO_DEJA_ELAN / _EJECUTABLE
    for ruta in (candidato, candidato.with_suffix(".exe")):
        if ruta.is_file():
            return str(ruta)
    return None


@dataclass(frozen=True)
class Resultado:
    """Lo que Lean dijo, y **cuanto miro**.

    `eventos_comprobados` no es adorno: «Lean paso» sobre una obra sin eventos y
    «Lean paso» sobre una cronologia coherente son el mismo verde y significan
    cosas distintas. Sin este numero, `CA-21` se cumple con una obra vacia.
    """

    ok: bool
    mensaje: str = ""
    eventos_comprobados: int = 0
    culpables: tuple[str, ...] = field(default_factory=tuple)


def _fuente(datos: str) -> str:
    """Plantilla + datos + teoremas, en un solo fichero sin imports."""
    return f"{PLANTILLA.read_text(encoding='utf-8')}\n{datos}\n{TEOREMAS}"


def _cuantos_eventos(datos: str) -> int:
    """Las filas de `eventos`, contadas sobre el texto que se le dio a Lean.

    Sobre el texto y no sobre la base: lo que hay que saber es cuanto miro
    **Lean**, y entre la consulta y el fichero hay un filtro -- los eventos sin
    participantes no producen fila --.
    """
    bloque = datos.split("def eventos : List Evento :=", 1)
    if len(bloque) < 2 or bloque[1].lstrip().startswith("[]"):
        return 0
    return bloque[1].split("]", 1)[0].count("⟨")


def _nombres(datos: str, tabla: str) -> list[str]:
    encontrado = re.search(rf"def {tabla} : List String := \[(.*?)\]", datos, re.DOTALL)
    if not encontrado:
        return []
    return [json.loads(t) for t in re.findall(r'"(?:[^"\\]|\\.)*"', encontrado.group(1))]


def _filas(datos: str, nombre: str, aridad: int) -> list[tuple[int, ...]]:
    bloque = re.search(rf"def {nombre} : List \w+ := \[(.*?)\]", datos, re.DOTALL)
    if not bloque:
        return []
    return [
        tuple(int(n) for n in fila.split(","))
        for fila in re.findall(r"⟨([^⟩]*)⟩", bloque.group(1))
        if len(fila.split(",")) == aridad
    ]


def _culpables(datos: str) -> tuple[str, ...]:
    """El par que rompe un invariante, con nombres. **Solo para el mensaje.**

    Recorre el mismo dato que se le dio a Lean. Si no encontrara nada -- porque
    Lean rechazo por otra cosa -- devuelve vacio y el error se reporta igual:
    quien decide es Lean.
    """
    personajes = _nombres(datos, "personajes")
    lugares = _nombres(datos, "lugares")
    momentos = _nombres(datos, "momentos")

    def nombre(tabla: list[str], indice: int) -> str:
        return tabla[indice] if 0 <= indice < len(tabla) else f"#{indice}"

    eventos = _filas(datos, "eventos", 3)
    for i, (momento_a, persona_a, lugar_a) in enumerate(eventos):
        for momento_b, persona_b, lugar_b in eventos[i + 1 :]:
            if persona_a == persona_b and momento_a == momento_b and lugar_a != lugar_b:
                return (
                    (
                        f"{nombre(personajes, persona_a)} esta a la vez en "
                        f"{nombre(lugares, lugar_a)} y en {nombre(lugares, lugar_b)} "
                        f"durante «{nombre(momentos, momento_a)}»"
                    ),
                )

    for momento_x, persona_x in _filas(datos, "exclusiones", 2):
        for momento_e, persona_e, _ in eventos:
            if persona_e == persona_x and momento_x < momento_e:
                return (
                    (
                        f"{nombre(personajes, persona_x)} aparece en "
                        f"«{nombre(momentos, momento_e)}», despues de «"
                        f"{nombre(momentos, momento_x)}», que lo excluye"
                    ),
                )
    return ()


async def correr_lean(sesion: AsyncSession, obra_id: int) -> Resultado:
    """Verifica la cronologia de una obra con Lean. No lanza si es incoherente.

    Devuelve el veredicto en vez de lanzarlo: quien decide que hacer con una
    cronologia rota es la puerta (T8), no el corredor. Lo unico que si lanza es
    `HerramientaNoDisponible`, porque eso no es un veredicto sobre la novela.
    """
    ejecutable = ruta_de_lean()
    if ejecutable is None:
        raise HerramientaNoDisponible

    datos = await generar_lean(sesion, obra_id)
    comprobados = _cuantos_eventos(datos)

    with TemporaryDirectory(prefix="cronologia-") as carpeta:
        fichero = Path(carpeta) / "Cronologia.lean"
        fichero.write_text(_fuente(datos), encoding="utf-8")

        proceso = await asyncio.create_subprocess_exec(
            ejecutable,
            str(fichero),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            salida, _ = await asyncio.wait_for(proceso.communicate(), timeout=_ESPERA_MAXIMA_S)
        except TimeoutError:
            proceso.kill()
            await proceso.wait()
            return Resultado(
                ok=False,
                mensaje=f"Lean no termino en {_ESPERA_MAXIMA_S:.0f} s",
                eventos_comprobados=comprobados,
            )

    texto = salida.decode("utf-8", errors="replace").strip()
    if proceso.returncode == 0 and "error" not in texto.lower():
        return Resultado(ok=True, eventos_comprobados=comprobados)

    culpables = _culpables(datos)
    detalle = ". ".join(culpables) if culpables else texto
    return Resultado(
        ok=False,
        mensaje=f"La cronologia no es coherente: {detalle}",
        eventos_comprobados=comprobados,
        culpables=culpables,
    )
