"""Fixtures compartidas por los tests de `manuscrito`.

`version` -- una tirada publicada de verdad, con dedicatoria y diez capitulos --
la define `test_lectura.py` y la necesita tambien `test_pdf.py`. Se re-exporta
desde aqui, que es la via de pytest para compartir una fixture entre ficheros:
importarla en el test que la usa hace que `ruff` la vea redefinida en cada
parametro (F811).
"""

from app.features.manuscrito.tests.test_lectura import version

__all__ = ["version"]
