"""EST-02 vuelve al Escritor con las palabras que lleva y cuántas faltan.

La primera corrida real (2026-09-24) escaló el capítulo 1 con 812, 141 y 621
palabras: la reparación citaba el capítulo entero y pedía «dejar intacto todo lo
demás», justo lo contrario de ampliar.
"""

from app.features.escritura.agents import PLANTILLA_V2, Reparacion


def test_la_plantilla_declara_la_extension_como_restriccion_dura():
    assert PLANTILLA_V2.count("1.000 y 1.500") >= 2


def test_la_reparacion_de_est_02_dice_cuantas_palabras_hay_y_no_repite_el_capitulo():
    capitulo = " ".join(["palabra"] * 812)
    linea = Reparacion(
        codigo="EST-02", cita=capitulo, desplazamiento_inicio=0, desplazamiento_fin=len(capitulo)
    ).como_linea()

    assert "812 palabras" in linea
    assert "entre 1.000 y 1.500" in linea
    assert "amplía" in linea
    assert capitulo not in linea
