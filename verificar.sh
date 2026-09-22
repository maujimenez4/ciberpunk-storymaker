#!/usr/bin/env bash
# Las cuatro puertas de CLAUDE.md §15. Falla entera si falla cualquiera:
# encadenarlas con tuberias enmascara el codigo de salida detras del tail.
set -e
python -m uv run pytest -q
python -m uv run ruff check .
python -m uv run ruff format --check .
python -m uv run mypy
python -m uv run lint-imports
echo "las cuatro puertas en verde"
