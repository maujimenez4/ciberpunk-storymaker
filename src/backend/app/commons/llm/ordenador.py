"""Ordenación semántica de candidatos (RI-17, RI-20, RI-22, D-02).

Sustituye al índice vectorial que hubo hasta la v1.4 de `architecture.md`. El
motivo fue de entorno: solo hay una credencial, la del proveedor de generación,
y su API no ofrece *embeddings*. Así que ordena el mismo modelo que escribe.

**Tres cosas que conviene tener presentes al leer esto:**

1. **No es determinista.** Dos llamadas con los mismos candidatos pueden
   devolver otro orden. Por eso RF-CTX-01 se retiró: el paquete ya no se promete
   reproducible. Lo que sigue siéndolo es el presupuesto y el recorte.
2. **Cuesta una llamada.** Pasa por el turno único de §2.2 igual que la
   escritura, y se registra en `ejecucion`.
3. **Opera sobre lo ya filtrado.** El filtro estructural reduce el manuscrito a
   decenas de candidatos antes de que el modelo vea nada, y `TOPE_DE_CANDIDATOS`
   pone un techo. Sin ese tope, el coste del ensamblado crecería con la obra, que
   es exactamente lo que el presupuesto por capas existe para evitar.
"""

import json
import re
from typing import Protocol

from app.commons.llm.cliente import ClienteDeModelo

# RNF-REN-04. Por encima de esto se recorta por recencia antes de llamar.
TOPE_DE_CANDIDATOS = 50


class OrdenadorSemantico(Protocol):
    def ordenar(self, consulta: str, candidatos: dict[str, str], k: int) -> list[str]:
        """Devuelve hasta `k` identificadores, del más pertinente al menos."""
        ...


class DobleDeOrdenador:
    """Determinista y sin red: la suite entera corre con esto (RI-13).

    Ordena por solapamiento de palabras. No pretende ser bueno —eso es lo que
    aporta el modelo— sino **estable**: los tests comprueban que el ensamblador
    respeta el orden que recibe, no que el orden sea acertado.
    """

    def ordenar(self, consulta: str, candidatos: dict[str, str], k: int) -> list[str]:
        palabras = set(re.findall(r"\w+", consulta.lower()))

        def solapa(texto: str) -> int:
            return len(palabras & set(re.findall(r"\w+", texto.lower())))

        orden = sorted(candidatos, key=lambda i: (-solapa(candidatos[i]), i))
        return orden[:k]


class OrdenadorPorModelo:
    """El de produccion. Le pide al modelo que ordene, y **verifica** lo que dice.

    La verificacion no es paranoia: un modelo puede devolver identificadores que
    no estaban entre los candidatos. Si se colaran, el ensamblador pediria
    fragmentos inexistentes y la capa de memoria recuperada llegaria vacia, que
    es justo el fallo que RF-CTX-14 existe para cazar. Se descartan en silencio y
    se completa por recencia.
    """

    def __init__(self, cliente: ClienteDeModelo, prompt: str) -> None:
        self._cliente = cliente
        self._prompt = prompt

    def ordenar(self, consulta: str, candidatos: dict[str, str], k: int) -> list[str]:
        if not candidatos:
            return []
        peticion = (
            f"{self._prompt}\n\n## Escena a escribir\n{consulta}\n\n## Candidatos\n"
            + "\n".join(f"[{i}] {texto}" for i, texto in candidatos.items())
            + f"\n\nDevuelve solo un array JSON con los {k} identificadores mas "
            f"pertinentes, del mas al menos."
        )
        respuesta = self._cliente.generar(peticion)
        elegidos = self._leer_orden(respuesta.texto, candidatos)
        # Completar por recencia lo que el modelo no haya cubierto: la capa nunca
        # debe llegar vacia por un fallo de formato.
        for identificador in candidatos:
            if len(elegidos) >= k:
                break
            if identificador not in elegidos:
                elegidos.append(identificador)
        return elegidos[:k]

    @staticmethod
    def _leer_orden(texto: str, candidatos: dict[str, str]) -> list[str]:
        try:
            crudo = json.loads(texto[texto.index("[") : texto.rindex("]") + 1])
        except (ValueError, json.JSONDecodeError):
            return []
        vistos: list[str] = []
        for elemento in crudo if isinstance(crudo, list) else []:
            identificador = str(elemento)
            if identificador in candidatos and identificador not in vistos:
                vistos.append(identificador)
        return vistos
