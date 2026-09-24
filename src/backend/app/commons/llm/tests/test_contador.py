from app.commons.llm.contador import ContadorDeTokens


class ContadorDePalabras:
    """Un doble minimo. NO es el contador de produccion: `CLAUDE.md` §4.1
    prohibe estimar, y esto estima. Existe para comprobar que el protocolo
    se puede satisfacer sin heredar de el."""

    def contar(self, texto: str) -> int:
        return len(texto.split())


def test_el_protocolo_se_satisface_por_forma_y_no_por_herencia():
    """RI-14: el contador se inyecta, asi que un doble tiene que encajar sin heredar."""
    contador: ContadorDeTokens = ContadorDePalabras()
    assert contador.contar("tres palabras aqui") == 3


def test_contar_devuelve_un_entero():
    contador: ContadorDeTokens = ContadorDePalabras()
    assert isinstance(contador.contar(""), int)
