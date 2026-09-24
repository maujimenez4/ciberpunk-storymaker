import tiktoken

from app.commons.llm.contador import CODIFICACION_POR_DEFECTO, ContadorDeTokens, ContadorTiktoken


class ContadorDePalabras:
    """Un doble minimo. NO es el contador de produccion: `CLAUDE.md` §4.1
    prohibe estimar, y esto estima. Existe para comprobar que el protocolo
    se puede satisfacer sin heredar de el."""

    def contar(self, texto: str) -> int:
        return len(texto.split())


def codificacion_de_juguete() -> tiktoken.Encoding:
    """Un BPE de verdad, construido en memoria y sin salir de la maquina.

    Existe porque el vocabulario de `cl100k_base` lo descarga `tiktoken` la
    primera vez, y la suite corre **sin red** (RNF-FIA-01, CA-4). Lo que se
    prueba aqui es el contador, no el vocabulario: con dos fusiones basta para
    que el conteo deje de ser proporcional a los caracteres.
    """
    rangos = {bytes([i]): i for i in range(256)}
    rangos[b"ab"] = 256
    rangos[b"abab"] = 257
    return tiktoken.Encoding(
        name="juguete",
        pat_str=r"\S+|\s+",
        mergeable_ranks=rangos,
        special_tokens={},
    )


def test_el_protocolo_se_satisface_por_forma_y_no_por_herencia():
    """RI-14: el contador se inyecta, asi que un doble tiene que encajar sin heredar."""
    contador: ContadorDeTokens = ContadorDePalabras()
    assert contador.contar("tres palabras aqui") == 3


def test_contar_devuelve_un_entero():
    contador: ContadorDeTokens = ContadorDePalabras()
    assert isinstance(contador.contar(""), int)


def test_el_contador_real_satisface_el_protocolo():
    contador: ContadorDeTokens = ContadorTiktoken(cargar=lambda _: codificacion_de_juguete())
    assert contador.contar("") == 0


def test_el_contador_real_no_estima_por_caracteres():
    """P-A: RF-CTX-02 prohibe «una estimacion **por caracteres**».

    Dos textos de la **misma longitud en caracteres** tienen que dar cuentas
    distintas. Un `len(texto) // 4` pasa por contador hasta que un paquete que
    no cabia se manda igual y la llamada se gasta para nada.
    """
    contador = ContadorTiktoken(cargar=lambda _: codificacion_de_juguete())

    denso, disperso = "abababab", "acacacac"
    assert len(denso) == len(disperso)
    assert contador.contar(denso) == 2
    assert contador.contar(disperso) == 8


def test_el_contador_no_carga_el_vocabulario_al_construirse():
    """Construirlo no puede costar una descarga: se inyecta en el arranque."""
    cargas: list[str] = []

    def cargar(nombre: str) -> tiktoken.Encoding:
        cargas.append(nombre)
        return codificacion_de_juguete()

    contador = ContadorTiktoken(cargar=cargar)
    assert cargas == []

    contador.contar("hola")
    contador.contar("adios")
    assert cargas == [CODIFICACION_POR_DEFECTO]


def test_la_codificacion_por_defecto_esta_declarada():
    assert CODIFICACION_POR_DEFECTO == "cl100k_base"
    assert ContadorTiktoken().codificacion == CODIFICACION_POR_DEFECTO
