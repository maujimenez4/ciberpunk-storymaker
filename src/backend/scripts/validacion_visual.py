"""La validacion visual de una version publicada (plan 7 T9, `RF-VAL-08`).

Envoltorio de `app.features.calidad.visual.main`, para lanzarlo desde la raiz
del repositorio con la lectura levantada (`pnpm dev` y el backend):

    uv run python src/backend/scripts/validacion_visual.py --token <token>

Opciones: `--base` (por defecto http://127.0.0.1:5173), `--capitulos 10`,
`--sin-dedicatoria`, `--capturas <dir fuera del repo>`, `--obra-id <id>` para
emitir los *scores* a la sesion de Langfuse de esa novela, `--json`.
Sale con 0 si aprueba y 1 si hay algun `REN-01`. No llama al modelo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.features.calidad.visual import main

if __name__ == "__main__":
    sys.exit(main())
