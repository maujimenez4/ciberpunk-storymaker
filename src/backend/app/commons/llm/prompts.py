"""Carga de prompts versionados (RI-14, `architecture.md` §5.5, `CLAUDE.md` §10).

`Prompt` **no es una tabla** (RD-01): es un fichero del repositorio. `ejecucion`
guarda `prompt_id`, `version` y el **hash** del fichero, y con eso se reconstruye
el paquete de una ejecucion antigua (RF-CTX-13) sin montar un segundo sistema de
versionado.

Los carga el **orquestador**, no el agente (RF-ORQ-16): ningun agente narrativo
toca el sistema de ficheros. Por eso este modulo vive en `commons/` y no dentro
de `agents.py`.

`CLAUDE.md` §10 prohibe editarlos en sitio: version nueva y se cambia la
referencia. Aqui se hace verificable —el hash viaja con el texto— en vez de
quedarse en una norma que nadie comprueba.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from app.commons.errors import RecursoNoEncontrado

# `escritor.v3.md` -> id "escritor", version "v3".
_NOMBRE = re.compile(r"^(?P<id>[a-z_]+)\.(?P<version>v\d+)\.md$")


@dataclass(frozen=True)
class PromptCargado:
    """Lo que un paso necesita para llamar y para dejar traza de la llamada."""

    prompt_id: str
    version: str
    hash: str
    texto: str


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class CargadorDePrompts:
    """Encuentra la version mas alta de cada prompt bajo una carpeta."""

    def __init__(self, raiz: Path | str) -> None:
        self.raiz = Path(raiz)

    def _candidatos(self, prompt_id: str) -> list[tuple[int, Path]]:
        encontrados = []
        for fichero in self.raiz.rglob("*.md"):
            coincide = _NOMBRE.match(fichero.name)
            if coincide and coincide.group("id") == prompt_id:
                encontrados.append((int(coincide.group("version")[1:]), fichero))
        return sorted(encontrados)

    def cargar(self, prompt_id: str, version: str | None = None) -> PromptCargado:
        """Sin `version`, la mas alta. Con `version`, esa exactamente.

        Pedir una version concreta es lo que permite reproducir una ejecucion
        antigua: `ejecucion` guardo cual se uso, y no la vigente de hoy.
        """
        candidatos = self._candidatos(prompt_id)
        if not candidatos:
            raise RecursoNoEncontrado("Prompt", prompt_id)
        if version is None:
            numero, fichero = candidatos[-1]
        else:
            elegidos = [(n, f) for n, f in candidatos if f"v{n}" == version]
            if not elegidos:
                raise RecursoNoEncontrado("Prompt", f"{prompt_id}.{version}")
            numero, fichero = elegidos[0]
        texto = fichero.read_text(encoding="utf-8")
        return PromptCargado(
            prompt_id=prompt_id, version=f"v{numero}", hash=_hash(texto), texto=texto
        )

    def coincide_el_hash(self, cargado: PromptCargado) -> bool:
        """Detecta un prompt editado en sitio, que `CLAUDE.md` §10 prohibe.

        Sin esta comprobacion la prohibicion es una costumbre: el fichero cambia,
        `ejecucion` sigue guardando el hash viejo y RF-CTX-13 reconstruiria un
        paquete que nunca se envio, sin que nada avisara.
        """
        actual = self.cargar(cargado.prompt_id, cargado.version)
        return actual.hash == cargado.hash
