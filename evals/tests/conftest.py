import sys
from pathlib import Path

# Los scripts de evals se ejecutan como `python evals/x.py` e importan `comun` a secas.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
