#!/usr/bin/env bash
# Las puertas de CLAUDE.md §15, mas la corrida en seco de CA-1. Falla entera si falla cualquiera:
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
# CA-1 con dobles. Entra aqui porque `corrida.py` esta fuera de `testpaths` y
# se rompio en silencio al cambiar `Dependencias`: una demostracion que puede
# romperse sin que nada avise deja de demostrar nada.
python -m uv run python corrida.py --seco
echo "las cinco puertas en verde"
