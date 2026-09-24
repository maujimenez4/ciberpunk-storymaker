"""Que significa «cambiado» en el indice, y por que el enlace no se adivina.

`RF-PUB-06` y `RF-PUB-07`.

**«Cambiado» es diferencia de texto, no de identificador.** Si significara
«tiene otra `version_texto_id`», una reescritura que produce el mismo texto
marcaria el capitulo, y el lector abriria un cambio que no existe. Esa
distincion es todo el valor de `RF-PUB-06`, y es la que estos tests protegen.

**La comparacion recibe textos, no filas.** `features/escritura` lo dice en su
puerta: «quien necesite el texto recibe el texto, no la fila». `VersionTexto`
no cruza la frontera, asi que `manuscrito` no puede leerla y la comparacion es
una funcion sin base de datos. Quien publica -- T6 -- trae los textos.
"""

from app.features.manuscrito import capitulos_cambiados, nuevo_identificador_publico

LONGITUD_MINIMA = 32


def test_los_capitulos_cambiados_se_calculan_por_diferencia_de_texto() -> None:
    anteriores = {1: "Mara abrio la puerta.", 4: "El faro seguia encendido."}
    nuevos = {1: "Mara abrio la puerta.", 4: "El faro llevaba anos apagado."}

    assert capitulos_cambiados(anteriores, nuevos) == [4]


def test_un_capitulo_reescrito_con_el_mismo_texto_no_cuenta_como_cambiado() -> None:
    """El test que da sentido a `RF-PUB-06`.

    La escena se regenero -- hay una `VersionTexto` nueva, con otro `id` y otro
    `run_id` -- y el texto salio identico. Para el lector no ha cambiado nada,
    y el indice no debe decirle que si.
    """
    textos = {1: "Mara abrio la puerta.", 4: "El faro seguia encendido."}

    assert capitulos_cambiados(textos, dict(textos)) == []


def test_la_primera_tirada_no_marca_nada() -> None:
    """Sin tirada anterior no hay con que comparar, y «todo cambiado» seria
    tan falso como «nada cambiado»: es la primera vez que se lee.

    `None` es «no hubo tirada anterior». No es lo mismo que `{}`, que seria
    una que existio y salio sin capitulos -- ver el test siguiente."""
    assert capitulos_cambiados(None, {1: "Mara abrio la puerta.", 2: "Llovia."}) == []


def test_una_tirada_anterior_vacia_no_es_lo_mismo_que_no_haberla() -> None:
    """Si la anterior existio y no tenia capitulos, los de ahora son nuevos."""
    assert capitulos_cambiados({}, {1: "Mara abrio la puerta."}) == [1]


def test_un_capitulo_que_antes_no_existia_cuenta_como_cambiado() -> None:
    """Una novela que gana un capitulo si tiene algo nuevo que leer ahi."""
    assert capitulos_cambiados({1: "Llovia."}, {1: "Llovia.", 2: "Y escampo."}) == [2]


def test_los_capitulos_cambiados_salen_en_orden_de_lectura() -> None:
    """El indice los pinta en orden, y ordenarlos dos veces es una de mas."""
    anteriores = {1: "a", 2: "b", 3: "c"}
    nuevos = {1: "A", 2: "b", 3: "C"}

    assert capitulos_cambiados(anteriores, nuevos) == [1, 3]


def test_un_capitulo_que_desaparece_no_se_cuenta_como_cambiado() -> None:
    """No esta en la tirada nueva, asi que no hay entrada de indice que marcar.

    Marcarlo obligaria al indice a pintar un capitulo que ya no se puede abrir.
    """
    assert capitulos_cambiados({1: "a", 2: "b"}, {1: "a"}) == []


def test_el_identificador_publico_no_deja_adivinar_el_siguiente() -> None:
    """`RF-PUB-07`. Es la unica credencial que protege la lectura del regalo.

    Cinco seguidos, sin relacion entre si. Si se pudiera adivinar el siguiente,
    se leeria el regalo de otra persona.
    """
    identificadores = [nuevo_identificador_publico() for _ in range(5)]

    assert len(set(identificadores)) == 5
    assert all(len(i) >= LONGITUD_MINIMA for i in identificadores)


def test_dos_identificadores_no_comparten_prefijo_largo() -> None:
    """Un contador con sal delante pasaria el test anterior y seria adivinable.

    Con `secrets.token_urlsafe` la probabilidad de compartir ocho caracteres de
    prefijo es despreciable; con un contador, es 1.
    """
    a, b = nuevo_identificador_publico(), nuevo_identificador_publico()

    assert a[:8] != b[:8]
