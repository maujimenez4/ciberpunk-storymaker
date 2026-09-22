"""Traza estructural y métricas (`architecture.md` §9; RNF-OBS-01 a 03).

**La traza es estructural, no textual** (RNF-OBS-03). Ni prompts de producción ni
fragmentos de manuscrito en los logs por defecto. No es pudor: un log con prosa
dentro convierte cualquier copia de los registros en una copia del manuscrito, y
además hace ilegible lo único que sirve para depurar, que son los identificadores
y los números.

De las ocho métricas de §9, dos son las que este módulo trata aparte porque no
existían hasta la v1.3 y **son las únicas que miden al sistema en vez de a la
obra**:

- **Tasa de defectos mal formados.** Hoy es la única señal directa de que el
  Continuista afirma cosas que no están en el texto (`verification.md` §6.3).
- **Espera por turno y esperas vencidas.** Es lo que dice si el límite de
  concurrencia está estrangulando el proceso o solo ordenándolo (§2.2).
"""

import re
from dataclasses import dataclass, field

# Lo que nunca sale en un log. `texto` y `prosa` cubren los campos del esquema;
# los delimitadores, un paquete de contexto entero pegado por error.
CAMPOS_PROHIBIDOS = ("texto", "prosa", "cita", "prompt", "biblia")
_PROSA_LARGA = re.compile(r"\S+(\s+\S+){12,}")


class TrazaConProsa(ValueError):
    """Se intentó registrar prosa o un prompt (RNF-OBS-03)."""


def traza(evento: str, **datos: object) -> dict[str, object]:
    """Construye una entrada de traza, o falla si lleva texto dentro.

    Falla en vez de recortar en silencio: si recortara, el llamante creería que
    registró algo y estaría registrando otra cosa, y nadie lo notaría hasta
    necesitar ese dato.
    """
    for clave, valor in datos.items():
        if any(prohibido in clave.lower() for prohibido in CAMPOS_PROHIBIDOS):
            raise TrazaConProsa(
                f"el campo '{clave}' no puede ir en la traza: es estructural, no "
                f"textual (RNF-OBS-03)"
            )
        if isinstance(valor, str) and _PROSA_LARGA.search(valor):
            raise TrazaConProsa(
                f"el campo '{clave}' lleva prosa. Un log con prosa dentro convierte "
                f"una copia de los registros en una copia del manuscrito"
            )
    return {"evento": evento, **datos}


@dataclass
class Metricas:
    """Las ocho de §9. Se acumulan en memoria del proceso y se consultan."""

    coste_por_escena: dict[str, float] = field(default_factory=dict)
    tokens_por_capa: dict[str, list[int]] = field(default_factory=dict)
    defectos_por_codigo: dict[str, int] = field(default_factory=dict)
    defectos_mal_formados: int = 0
    defectos_totales: int = 0
    reintentos: int = 0
    escalados: int = 0
    escenas: int = 0
    esperas_de_turno_s: list[float] = field(default_factory=list)
    esperas_vencidas: int = 0

    # --- las dos que miden al sistema ---------------------------------------

    def anotar_defecto(self, codigo: str, bien_formado: bool) -> None:
        self.defectos_totales += 1
        self.defectos_por_codigo[codigo] = self.defectos_por_codigo.get(codigo, 0) + 1
        if not bien_formado:
            self.defectos_mal_formados += 1

    @property
    def tasa_de_defectos_mal_formados(self) -> float:
        """§9 y `verification.md` §6.3. Si sube, el Continuista se está
        inventando citas; si baja a cero de golpe, probablemente dejó de
        emitir."""
        if not self.defectos_totales:
            return 0.0
        return self.defectos_mal_formados / self.defectos_totales

    def anotar_espera_de_turno(self, segundos: float, vencida: bool) -> None:
        self.esperas_de_turno_s.append(segundos)
        if vencida:
            self.esperas_vencidas += 1

    @property
    def espera_media_de_turno_s(self) -> float:
        """RNF-OBS-02: dice si el límite de §2.2 estrangula o solo ordena."""
        if not self.esperas_de_turno_s:
            return 0.0
        return sum(self.esperas_de_turno_s) / len(self.esperas_de_turno_s)

    # --- las de la obra ------------------------------------------------------

    def anotar_escena(
        self, escena_id: str, coste: float, por_capa: dict[str, int]
    ) -> None:
        self.escenas += 1
        self.coste_por_escena[escena_id] = coste
        for capa, tokens in por_capa.items():
            self.tokens_por_capa.setdefault(capa, []).append(tokens)

    @property
    def escalados_por_cien_escenas(self) -> float:
        """§9. La métrica que avisa de que la revisión humana se está
        degradando por volumen, que es un riesgo declarado en `verification.md`
        §7 y hoy sin umbral."""
        return (self.escalados / self.escenas * 100) if self.escenas else 0.0

    def porcentaje_por_capa(self) -> dict[str, float]:
        medias = {
            capa: sum(v) / len(v) for capa, v in self.tokens_por_capa.items() if v
        }
        total = sum(medias.values())
        return {c: (t / total * 100) for c, t in medias.items()} if total else {}
