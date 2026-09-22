#!/usr/bin/env bash
# Las cuatro puertas de CLAUDE.md §15. Falla entera si falla cualquiera:
# encadenarlas con tuberias enmascara el codigo de salida detras del tail.
set -e
# import-linter dibuja un spinner con `rich`, que revienta si stdout es
# /dev/null: el guion salia con codigo 1 con los diez contratos en verde, y me
# costo tres commits entender que el fallo era de la comprobacion y no del
# codigo. TERM=dumb desactiva el spinner y el guion se puede redirigir.
export TERM=dumb
python -m uv run pytest -q
python -m uv run ruff check .
python -m uv run ruff format --check .
python -m uv run mypy
python -m uv run lint-imports
echo "las cuatro puertas en verde"
