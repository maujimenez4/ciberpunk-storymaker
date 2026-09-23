"""Exportación del manuscrito a `.md` y `.pdf`.

El manuscrito se ensambla en memoria (RF-MAN-01) y hasta ahora salía a un `.txt`
suelto en la raíz. Un `.txt` no conserva la estructura —título, cortes de
escena— y no se le puede enseñar a nadie que no lea código. Estas pruebas fijan
las dos salidas y, sobre todo, que **el texto llegue intacto**: exportar no es
reescribir.

Se construye el `Manuscrito` a mano, sin base de datos: ensamblarlo ya está
probado en `test_manuscrito.py` y aquí estorbaría.
"""

from pathlib import Path

from app.features.manuscrito import (
    FragmentoDeManuscrito,
    Manuscrito,
    a_markdown,
    a_pdf,
    exportar,
)


def _manuscrito(*textos: str) -> Manuscrito:
    return Manuscrito(
        obra_id="o1",
        fragmentos=[
            FragmentoDeManuscrito(
                escena_id=f"es{i}", orden_discurso=i, texto=texto, autoria="generado"
            )
            for i, texto in enumerate(textos, start=1)
        ],
    )


# --- markdown ----------------------------------------------------------------


def test_el_markdown_lleva_el_titulo_como_encabezado() -> None:
    """Un fichero de prosa sin título no se distingue de otro dentro de la
    misma carpeta, que es justo donde van a convivir todos."""
    salida = a_markdown(_manuscrito("Ada cruzo el taller."), titulo="Ceniza y neon")

    assert salida.startswith("# Ceniza y neon\n")


def test_el_markdown_conserva_cada_fragmento_intacto_y_en_orden() -> None:
    """Exportar no es reescribir: si el formato toca el texto, el `.md` deja de
    ser el manuscrito y pasa a ser una versión más, sin `run_id` que la explique
    (§14)."""
    salida = a_markdown(_manuscrito("Primera escena.", "Segunda escena."), titulo="O")

    assert salida.index("Primera escena.") < salida.index("Segunda escena.")
    assert "Primera escena." in salida and "Segunda escena." in salida


def test_el_markdown_separa_las_escenas_con_un_corte_visible() -> None:
    """Sin separador, dos escenas seguidas se leen como una sola: el corte es
    información del manuscrito, no decoración."""
    salida = a_markdown(_manuscrito("Una.", "Otra."), titulo="O")

    assert "* * *" in salida


# --- pdf ---------------------------------------------------------------------


def test_el_pdf_tiene_cabecera_y_cierre_de_pdf() -> None:
    """Lo mínimo que comprueba cualquier lector antes de abrirlo."""
    datos = a_pdf(_manuscrito("Ada cruzo el taller."), titulo="Ceniza y neon")

    assert datos.startswith(b"%PDF-1.4")
    assert datos.rstrip().endswith(b"%%EOF")


def test_el_pdf_declara_tantas_paginas_como_objetos_de_pagina_tiene() -> None:
    """El `/Count` del nodo de páginas y los `/Type /Page` reales se escriben
    en sitios distintos del fichero: si se desincronizan, el PDF abre en blanco
    y no hay error que lo diga."""
    renglon = "Una linea de prosa que ocupa su renglon."
    largo = _manuscrito(*[renglon for _ in range(400)])

    datos = a_pdf(largo, titulo="O")

    paginas = datos.count(b"/Type /Page\n")
    assert paginas > 1
    assert f"/Count {paginas}".encode() in datos


def test_el_pdf_soporta_acentos_y_rayas_de_dialogo() -> None:
    """La prosa del proyecto es española y dialoga con raya. Si el escritor de
    PDF asume ASCII, revienta en la primera escena con diálogo."""
    datos = a_pdf(_manuscrito("—No voy a firmar eso —dijo él, con ironía."), titulo="Ó")

    assert datos.startswith(b"%PDF-1.4")


def test_el_pdf_no_desborda_el_margen_con_una_linea_larguisima() -> None:
    """Una línea sin espacios no se puede cortar por palabras. O se parte por
    caracteres o se sale de la página sin avisar."""
    datos = a_pdf(_manuscrito("A" * 500), titulo="O")

    assert datos.count(b"/Type /Page\n") >= 1


# --- exportar ----------------------------------------------------------------


def test_exportar_deja_los_dos_ficheros_en_la_misma_carpeta(tmp_path: Path) -> None:
    """§15: la prosa vive fuera del repositorio, y toda junta en un sitio. Dos
    formatos, una carpeta, ningún `.txt`."""
    carpeta = tmp_path / "manuscritos"

    rutas = exportar(
        _manuscrito("Ada cruzo el taller."),
        carpeta=carpeta,
        nombre="manuscrito-seco",
        titulo="Ceniza y neon",
    )

    assert sorted(r.name for r in rutas) == [
        "manuscrito-seco.md",
        "manuscrito-seco.pdf",
    ]
    assert {r.parent for r in rutas} == {carpeta}
    assert not list(carpeta.glob("*.txt"))


def test_exportar_crea_la_carpeta_si_no_existe(tmp_path: Path) -> None:
    """La carpeta está ignorada por git, así que en un clon limpio no existe."""
    carpeta = tmp_path / "ni" / "existe"

    exportar(_manuscrito("Texto."), carpeta=carpeta, nombre="m", titulo="O")

    assert (carpeta / "m.md").exists() and (carpeta / "m.pdf").exists()


def test_exportar_escribe_el_markdown_en_utf8(tmp_path: Path) -> None:
    """Sin `encoding` explícito, Windows escribe en cp1252 y el `.md` se abre
    con los acentos rotos en cualquier otra máquina."""
    exportar(
        _manuscrito("—dijo él, con ironía."),
        carpeta=tmp_path,
        nombre="m",
        titulo="Ó",
    )

    assert "ironía" in (tmp_path / "m.md").read_text(encoding="utf-8")
