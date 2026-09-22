#!/usr/bin/env python
"""CA-4: desactiva cada validación y comprueba que su test **se pone en rojo**.

`verification.md` §2 aplaza los tests de mutación; la spec dice que CA-4 hace su
trabajo a mano mientras tanto. Esto lo automatiza, que es lo mismo pero repetible.

**Por qué importa.** Un test que pasa no dice que la validación funcione: dice
que el test pasa. Si se desactiva la validación y el test sigue verde, ese test
no comprobaba nada y llevamos meses creyendo que sí. Es la salvaguarda más barata
contra una suite que da confianza sin darla.

Cada fila desactiva una validación sustituyendo su primera línea ejecutable por
un retorno inocuo, corre **solo** el test que le toca, y exige que falle. El
fichero se restaura siempre, incluso si el script revienta.

    uv run python verificar_ca4.py
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
APP = RAIZ / "src" / "backend" / "app"


@dataclass(frozen=True)
class Mutacion:
    """Una validación, cómo desactivarla y qué test debería cazarlo."""

    nombre: str
    fichero: Path
    ancla: str
    reemplazo: str
    test: str


MUTACIONES = (
    Mutacion(
        "RF-CAL-01 · giro de valor",
        APP / "features/calidad/validadores.py",
        "    if valor_entrada and valor_salida and valor_entrada != valor_salida:\n        return []",  # noqa: E501 - literal del codigo fuente: partirlo rompe la coincidencia
        "    if True:\n        return []",
        "test_una_ficha_sin_giro_da_est_01",
    ),
    Mutacion(
        "RF-CAL-02 · nivel de calor",
        APP / "features/calidad/validadores.py",
        "    bajo = texto.lower()",
        "    return []\n    bajo = texto.lower()",
        "test_un_termino_por_encima_del_nivel_da_seg_01",
    ),
    Mutacion(
        "RF-CAL-04 · continuidad fisica",
        APP / "features/calidad/validadores.py",
        "    defectos: list[Defecto] = []\n    por_sujeto",
        "    return []\n    defectos: list[Defecto] = []\n    por_sujeto",
        "test_estar_en_dos_lugares_a_la_vez_da_con_01",
    ),
    Mutacion(
        "RF-CAL-12 · persona y tiempo verbal (VOZ-03)",
        APP / "features/calidad/validadores.py",
        "    narracion = solo_narracion(texto)",
        "    return []\n    narracion = solo_narracion(texto)",
        "test_narrar_en_primera_cuando_la_obra_es_en_tercera_da_voz_03",
    ),
    Mutacion(
        "RF-CAL-11 · comprobacion de forma",
        APP / "features/calidad/puerta.py",
        "    motivos: list[str] = []",
        "    return defecto\n    motivos: list[str] = []",
        "test_una_cita_que_no_coincide_con_el_texto_queda_mal_formada",
    ),
    Mutacion(
        "RG-09 · edad minima por esquema",
        APP / "commons/domain/escena.py",
        "        if not self.nivel_de_calor.implica_contenido_romantico():\n            return self",  # noqa: E501 - literal del codigo fuente: partirlo rompe la coincidencia
        "        if True:\n            return self",
        "test_el_esquema_rechaza_calor_con_un_menor",
    ),
    Mutacion(
        "RF-CTX-14 · capa vacia",
        APP / "features/contexto/service.py",
        "        if capa in ORIGEN and contenido.esta_vacia:",
        "        if False and contenido.esta_vacia:",
        "test_una_capa_vacia_falla_antes_de_llamar_al_modelo",
    ),
    Mutacion(
        "RF-ORQ-08 · reintento generico prohibido",
        APP / "features/escritura/ciclo.py",
        "    if not defectos:",
        "    if False:",
        "test_no_se_repara_sin_defecto_adjunto",
    ),
    Mutacion(
        "RF-ORQ-03 · ningun estado se salta",
        APP / "commons/jobs/trabajos.py",
        "        exigir(actual.estado, hasta)",
        "        pass",
        "test_un_salto_no_declarado_se_rechaza",
    ),
    Mutacion(
        "RNF-OBS-03 · traza sin prosa",
        APP / "commons/config/observabilidad.py",
        "    for clave, valor in datos.items():",
        "    for clave, valor in []:",
        "test_los_campos_con_prosa_se_rechazan_por_nombre",
    ),
)


def _correr(test: str) -> bool:
    """True si el test pasa."""
    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-k", test, "--no-header", "-x"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    return resultado.returncode == 0


def main() -> int:
    ciegos: list[str] = []
    print(f"CA-4: {len(MUTACIONES)} validaciones\n")

    for mutacion in MUTACIONES:
        original = mutacion.fichero.read_text(encoding="utf-8")
        if mutacion.ancla not in original:
            print(f"  ?  {mutacion.nombre}: no se encontro el ancla, revisar")
            ciegos.append(f"{mutacion.nombre} (ancla perdida)")
            continue
        try:
            mutacion.fichero.write_text(
                original.replace(mutacion.ancla, mutacion.reemplazo, 1),
                encoding="utf-8",
                newline="",
            )
            paso_igual = _correr(mutacion.test)
        finally:
            mutacion.fichero.write_text(original, encoding="utf-8", newline="")

        if paso_igual:
            print(f"  X  {mutacion.nombre}: el test SIGUE EN VERDE sin la validacion")
            ciegos.append(mutacion.nombre)
        else:
            print(f"  ok {mutacion.nombre}: el test se pone en rojo")

    print()
    if ciegos:
        print(f"{len(ciegos)} validaciones sin test que las respalde:")
        for nombre in ciegos:
            print(f"  - {nombre}")
        return 1
    print("las 10 validaciones tienen un test que falla al desactivarlas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
