#!/usr/bin/env bash
# Las puertas de CLAUDE.md §15, mas la corrida en seco de CA-1. Falla entera si falla cualquiera:
# encadenarlas con tuberias enmascara el codigo de salida detras del tail.
set -e
# import-linter dibuja un spinner con `rich`, que revienta si stdout es
# /dev/null: el guion salia con codigo 1 con los diez contratos en verde, y me
# costo tres commits entender que el fallo era de la comprobacion y no del
# codigo. TERM=dumb desactiva el spinner y el guion se puede redirigir.
export TERM=dumb

# `uv` se resuelve de las dos formas en que puede estar instalado. El instalador
# oficial y Homebrew dejan un **binario**; `pip install uv` deja un **modulo**.
# Este guion usaba solo `python -m uv`, asi que en una maquina recien preparada
# fallaba con «No module named uv» antes de comprobar nada.
if command -v uv >/dev/null 2>&1; then
  UV="uv"
elif python -m uv --version >/dev/null 2>&1; then
  UV="python -m uv"
else
  echo "falta uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

$UV run pytest -q
$UV run ruff check .
$UV run ruff format --check .
$UV run mypy
$UV run lint-imports
# CA-1 con dobles. Entra aqui porque `corrida.py` esta fuera de `testpaths` y
# se rompio en silencio al cambiar `Dependencias`: una demostracion que puede
# romperse sin que nada avise deja de demostrar nada.
$UV run python corrida.py --seco
echo "las cinco puertas en verde"
