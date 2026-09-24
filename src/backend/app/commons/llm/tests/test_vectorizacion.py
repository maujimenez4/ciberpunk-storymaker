"""La juntura 4 de la Fase 2: `ClienteModelo` sabe vectorizar.

Sin este metodo el indice **no se llena en produccion** y la capa de memoria
recuperada sale siempre vacia, de modo que RF-CTX-04 solo era demostrable en
tests. Aqui se cierra, y se cierra sin llamar al proveedor: Anthropic no
publica un extremo de *embeddings*, y P-02 ademas prohibe una segunda
credencial. Lo que hay es una senal **lexica**, declarada como tal.

Ni un solo test de este fichero abre el SDK (CA-4).
"""

import os
import subprocess
import sys

import pytest

from app.commons.db.vectores import desempaquetar_vector, distancia_coseno
from app.commons.llm.claude_code import ClienteClaudeCode
from app.commons.llm.cliente import (
    DIMENSION_DEL_VECTOR,
    MODELO_DEL_VECTOR,
    ClienteModelo,
    Vectorizacion,
    vectorizar_texto,
)
from app.commons.llm.doble import DobleDeterminista


def _revienta(**_: object) -> object:
    raise AssertionError("vectorizar no debe llamar al proveedor")


def test_el_protocolo_declara_el_metodo_de_vectorizar():
    """La deuda, enunciada donde se paga: el contrato la tiene."""
    assert hasattr(ClienteModelo, "vectorizar")


def test_el_cliente_real_vectoriza_y_no_llama_al_proveedor():
    """CA-4: la suite corre sin red. Y vectorizar no es una llamada al modelo."""
    cliente: ClienteModelo = ClienteClaudeCode(consulta=_revienta)

    vector = cliente.vectorizar("Nadia abrio la puerta del invernadero.")

    assert isinstance(vector, Vectorizacion)
    assert vector.dimension == DIMENSION_DEL_VECTOR
    assert vector.modelo == MODELO_DEL_VECTOR


def test_el_doble_vectoriza_sin_ninguna_respuesta_preparada():
    """T11 de la Fase 2 lo aviso: el doble hereda del protocolo por subclase
    explicita, asi que un miembro sin implementar lo vuelve abstracto. Que
    `DobleDeterminista({})` se construya y vectorice **es** la comprobacion."""
    doble = DobleDeterminista({})

    assert doble.vectorizar("Nadia abrio la puerta.").dimension == DIMENSION_DEL_VECTOR


def test_las_dos_implementaciones_definen_vectorizar_y_no_lo_heredan_en_blanco():
    """**T11 de la Fase 2 temia lo contrario, y el peligro real es peor.**

    Un miembro de `Protocol` con cuerpo `...` **no** vuelve abstracta a la
    subclase explicita: `__abstractmethods__` queda vacio y la clase hereda un
    metodo que devuelve `None` en silencio. Lo comprobado en este interprete.

    Asi que la suite no revienta: el indice se llenaria de `None` y nadie se
    enteraria. Lo unico que lo impide es exigir que cada implementacion lo
    **defina**, y eso es lo que mira este test.
    """
    assert "vectorizar" in ClienteClaudeCode.__dict__
    assert "vectorizar" in DobleDeterminista.__dict__


def test_los_dos_clientes_dan_exactamente_el_mismo_vector():
    """Lo que la suite indexa es lo que produccion indexara. Si divergieran,
    ningun test diria nada del indice de verdad."""
    texto = "El invernadero olia a tierra mojada."
    esperado = vectorizar_texto(texto)

    assert esperado.datos != b""
    assert DobleDeterminista({}).vectorizar(texto) == esperado
    assert ClienteClaudeCode(consulta=_revienta).vectorizar(texto) == esperado


def test_el_blob_es_float32_de_la_dimension_declarada():
    """`vec_distance_cosine` lee float32: si esto cambia, los dos almacenes
    dejan de leer lo mismo."""
    vector = vectorizar_texto("una frase cualquiera")

    assert len(vector.datos) == 4 * DIMENSION_DEL_VECTOR
    assert len(desempaquetar_vector(vector.datos)) == DIMENSION_DEL_VECTOR


def test_el_mismo_texto_da_el_mismo_vector_en_otro_proceso():
    """`hash()` de una cadena esta salado por proceso, y con el los vectores
    guardados ayer no se podrian comparar con los de hoy. El indice quedaria
    lleno de ruido **sin que fallara nada**. Por eso el reparto es `blake2b`.
    """
    codigo = (
        "from app.commons.llm.cliente import vectorizar_texto;"
        "print(vectorizar_texto('el invernadero').datos.hex())"
    )
    entorno = {**os.environ, "PYTHONHASHSEED": "1"}
    otro = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, env=entorno, check=True
    )

    assert otro.stdout.strip() == vectorizar_texto("el invernadero").datos.hex()


def test_dos_textos_del_mismo_asunto_estan_mas_cerca_que_uno_ajeno():
    """Es una senal **lexica** y no semantica, y por eso se mide lo que da:
    comparte vocabulario, se acerca. Declararlo aqui evita que alguien lea la
    capa de memoria recuperada como mas de lo que es."""
    invernadero = desempaquetar_vector(vectorizar_texto("Nadia entro en el invernadero").datos)
    plantas = desempaquetar_vector(vectorizar_texto("el invernadero estaba lleno de plantas").datos)
    ajeno = desempaquetar_vector(vectorizar_texto("Teo firmo los papeles del banco").datos)

    assert distancia_coseno(invernadero, plantas) < distancia_coseno(invernadero, ajeno)


def test_un_texto_sin_palabras_da_un_vector_nulo_y_no_revienta():
    """Un fragmento en blanco no se parece a nada. Un `nan` aqui no ordena:
    envenena la lista entera sin fallar."""
    componentes = desempaquetar_vector(vectorizar_texto("   \n\n  ").datos)

    assert componentes == pytest.approx([0.0] * DIMENSION_DEL_VECTOR)
    assert distancia_coseno(componentes, [1.0] * DIMENSION_DEL_VECTOR) == pytest.approx(1.0)


def test_el_vector_esta_normalizado_y_la_longitud_del_texto_no_decide():
    """Sin normalizar, el coseno seguiria funcionando pero un fragmento largo
    dominaria cualquier suma que alguien hiciera despues. Se normaliza aqui,
    una vez, y no en cada lector."""
    corto = desempaquetar_vector(vectorizar_texto("la puerta").datos)
    repetido = desempaquetar_vector(vectorizar_texto("la puerta la puerta la puerta").datos)

    assert sum(c * c for c in corto) == pytest.approx(1.0, abs=1e-5)
    assert distancia_coseno(corto, repetido) == pytest.approx(0.0, abs=1e-6)
