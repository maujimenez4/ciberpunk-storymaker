import hashlib
import re
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from app.commons.domain.normalizacion import normalizar

DIMENSION_DEL_VECTOR = 256
"""Componentes del vector. Pequena a proposito: lo que se ordena es el conjunto
**ya filtrado** —decenas de fragmentos, no la obra entera—, y una dimension
mayor solo engordaria la tabla sin cambiar el orden."""

MODELO_DEL_VECTOR = "lexico-blake2b-v1"
"""Va en `embedding.modelo`, y por eso lleva version: el dia que esto cambie,
los vectores viejos dejan de ser comparables con los nuevos y la columna es lo
unico que permite saberlo sin adivinar."""

_PALABRA = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Vectorizacion:
    """Un texto ya vectorizado, en la forma que la tabla `embedding` guarda.

    Repite los tres campos de `canon.Vector` y no lo importa: `commons/` no
    importa de ninguna feature (primer contrato de `import-linter`). Quien
    orqueste traduce de una a otra en una linea.
    """

    datos: bytes
    dimension: int
    modelo: str


def vectorizar_texto(
    texto: str, *, dimension: int = DIMENSION_DEL_VECTOR, modelo: str = MODELO_DEL_VECTOR
) -> Vectorizacion:
    """Bolsa de palabras con reparto por `blake2b`, normalizada y en float32.

    **Lo que esto es, dicho sin adornos: una senal lexica, no semantica.** El
    proveedor no publica un extremo de *embeddings* y P-02 prohibe una segunda
    credencial, asi que la alternativa habria sido un decimoquinto paquete con
    un modelo que descargar — que es justo lo que `CLAUDE.md` §3, punto 7, manda
    preguntar antes de meter. Lo que se gana con esto es concreto: el indice
    **se llena en produccion**, que hasta hoy no ocurria, y la capa de memoria
    recuperada deja de salir siempre vacia. Lo que no se gana es que dos
    fragmentos que dicen lo mismo con otras palabras se reconozcan.

    Tres decisiones que no son de estilo:

    - **El reparto es `blake2b` y no `hash()`.** El `hash()` de una cadena esta
      salado por proceso: los vectores de ayer no se podrian comparar con los de
      hoy, y el indice se llenaria de ruido **sin que fallara nada**.
    - **Se normaliza el texto** con `commons/domain/normalizacion`: minusculas,
      sin tildes y sin la -s del plural simple. Es lo mismo que hacen los vetos,
      y por el mismo motivo: comparar la forma exacta no compara.
    - **Se normaliza el vector** a longitud 1, para que un fragmento largo no
      pese mas que uno corto en ninguna suma posterior.

    El signo por palabra —el bit 32 del digest— es lo que evita que dos palabras
    que caen en la misma componente se sumen siempre: con signo se cancelan la
    mitad de las veces, y el sesgo de las colisiones deja de tener direccion.
    """
    componentes = np.zeros(dimension, dtype=np.float64)
    for encontrada in _PALABRA.finditer(texto):
        digest = hashlib.blake2b(
            normalizar(encontrada.group(0)).encode("utf-8"), digest_size=8
        ).digest()
        indice = int.from_bytes(digest[:4], "little") % dimension
        componentes[indice] += 1.0 if digest[4] & 1 else -1.0

    norma = float(np.linalg.norm(componentes))
    if norma:
        componentes /= norma

    return Vectorizacion(
        datos=componentes.astype("<f4").tobytes(), dimension=dimension, modelo=modelo
    )


class ClienteModelo(Protocol):
    """El contrato del modelo. **`vectorizar` no llama al proveedor**, y por eso
    no es `async`: lo que hace es local y sincrono.

    **`modelo` es parametro de la llamada y no solo del constructor**, y eso es
    P-02 escrito donde se puede incumplir: `CLAUDE.md` §4 dice que Haiku 4.5
    escribe y Opus 5 juzga, «porque un juez que comparte modelo con quien
    escribio tiende a aprobar su propio estilo». Mientras el modelo lo fijara
    solo el constructor, la separacion **no se podia pedir y ningun test podia
    caer por incumplirla**. `None` deja el que el cliente declare, que es el
    Escritor: quien ya llamaba no cambia.

    Que viva aqui y no en otra interfaz es lo que la Fase 2 dejo decidido al
    dejar el hueco —`consolidar_escena` recibe un `vectorizar` inyectado—, y lo
    que evita una segunda dependencia que inyectar por todo el arbol.

    **Cuidado al anadir miembros.** Un metodo con cuerpo `...` **no** vuelve
    abstracta a la subclase explicita: `__abstractmethods__` queda vacio y quien
    no lo implemente hereda uno que devuelve `None` en silencio. Lo guarda
    `test_vectorizacion.py`, exigiendo que cada implementacion lo **defina**.
    """

    async def completar(self, prompt: str, semilla: int, modelo: str | None = None) -> str: ...

    def vectorizar(self, texto: str) -> Vectorizacion: ...


def obtener_cliente_modelo() -> ClienteModelo:
    """La dependencia por la que entra el modelo (RI-14, `CLAUDE.md` §6).

    Devuelve el cliente real: el **Claude Agent SDK** ya autenticado contra la
    cuenta (P-08). Con esto se cierra el hueco que la Fase 1 dejo declarado —
    `POST /entrevistas/{id}/respuestas` y `.../cerrar` respondian 500 contra la
    aplicacion levantada, porque la unica implementacion de `ClienteModelo`
    que existia era `DobleDeterminista`.

    **Construirlo no llama a nadie ni lee credenciales**, y eso importa: es
    una dependencia de FastAPI, asi que se resuelve en cada peticion. Lo que
    abre el proceso del proveedor es `completar`, y solo `completar`.

    En pruebas se sustituye por `DobleDeterminista` con
    `dependency_overrides`: la suite corre sin red y sin credenciales
    (RNF-FIA-01, CA-4). Que el cliente exista no cambia eso.

    El import va dentro de la funcion a proposito: `claude_code` importa
    `ClienteModelo` de aqui, y al reves seria un ciclo. De paso, importar este
    modulo —que es lo que hace `features/obra/router.py`— no arrastra el SDK.
    """
    from app.commons.llm.claude_code import ClienteClaudeCode

    return ClienteClaudeCode()
