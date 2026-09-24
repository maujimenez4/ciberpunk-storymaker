"""Las tablas de la publicacion: lo que se fija al publicar y ya no se mueve.

Una `VersionPublicada` es el regalo entregado. Todo lo de aqui existe para que
**lo que el destinatario lee hoy siga siendo lo que lea dentro de un ano**,
aunque el manuscrito cambie por debajo: republicar crea otra version y conserva
la anterior (`CLAUDE.md` §7), y el enlace repartido sigue llevando a la suya.

De ahi la decision que gobierna el modulo: `CapituloPublicado` guarda el
`version_texto_id` **concreto** (RF-PUB-01) en vez de resolver la version
vigente al leer. Resolverla al leer es mas simple y es justo lo que no se puede
hacer: una regeneracion posterior cambiaria en silencio un enlace ya repartido,
y nadie se enteraria porque la pagina seguiria cargando.
"""

import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, DateTime

from app.commons.db.base import Base
from app.commons.domain.reloj import RelojDelSistema

BYTES_DEL_IDENTIFICADOR = 32
"""RF-PUB-07. `token_urlsafe(32)` da 43 caracteres de base64 para URL.

Treinta y dos bytes son 256 bits: adivinarlo no es un problema de paciencia. Y
`urlsafe` no es cosmetico -- el identificador viaja en la ruta del enlace que se
le manda al destinatario, y un `+` o un `/` obligarian a escaparlo.
"""


def nuevo_identificador_publico() -> str:
    """La llave de entrada de la lectura, y la unica credencial que la protege.

    `secrets` y no `random`: `random` es un generador predecible en cuanto se
    conoce la semilla, y aqui adivinar el identificador es leer el regalo de
    otra persona.

    Es funcion y no una expresion dentro de `mapped_column` para que se pueda
    probar sola. El `default` de una columna se aplica **al insertar**, asi que
    un test que lo leyera de un objeto recien construido recibiria `None` y
    pasaria por el motivo equivocado.
    """
    return secrets.token_urlsafe(BYTES_DEL_IDENTIFICADOR)


class VersionPublicada(Base):
    """Una tirada del regalo. Inmutable por contrato, no por disparador.

    `ordinal` es el numero de tirada dentro de la obra, y es unico con ella: dos
    versiones con el mismo ordinal dejarian «la version 2» sin significado en
    cuanto alguien la citara.

    `sucede_a_id` apunta a la anterior y hace la cadena de republicaciones
    recorrible hacia atras. Es nulo en la primera, que no sucede a ninguna.
    """

    __tablename__ = "version_publicada"
    __table_args__ = (
        UniqueConstraint("obra_id", "ordinal", name="uq_version_publicada_obra_ordinal"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", name="fk_version_publicada_obra_id"))
    ordinal: Mapped[int]
    publicada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: RelojDelSistema().ahora()
    )
    sucede_a_id: Mapped[int | None] = mapped_column(
        ForeignKey("version_publicada.id", name="fk_version_publicada_sucede_a_id")
    )
    # `unique`: una colision serviria el regalo de otro. Con 256 bits no va a
    # pasar, y aun asi la comprobacion barata es que el esquema lo impida --
    # confiar en la improbabilidad es confiar en que nadie escriba el valor a
    # mano, y T6 y T7 van a escribir en esta tabla.
    identificador_publico: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=nuevo_identificador_publico
    )


class CapituloPublicado(Base):
    """Un capitulo dentro de una tirada, **fijado** a su version de texto.

    `titulo` y `cambiado` estan aqui y no en el navegador porque el indice de la
    002 los necesita (`RF-IND-01` y `RF-IND-02`) y **no los puede calcular**:
    `cambiado` compara esta tirada con la anterior, y el navegador solo tiene
    delante la que esta leyendo. Lo que no salga en el esquema no existe para el
    cliente generado del OpenAPI.
    """

    __tablename__ = "capitulo_publicado"
    __table_args__ = (
        UniqueConstraint("version_id", "numero", name="uq_capitulo_publicado_version_numero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("version_publicada.id", name="fk_capitulo_publicado_version_id")
    )
    numero: Mapped[int]
    titulo: Mapped[str | None] = mapped_column(String(200))
    version_texto_id: Mapped[int] = mapped_column(
        ForeignKey("version_texto.id", name="fk_capitulo_publicado_version_texto_id")
    )
    # Falso en la primera tirada, donde no hay nada con que comparar. Lo calcula
    # T7 al publicar y lo pinta el indice sin volver a pensarlo.
    cambiado: Mapped[bool] = mapped_column(default=False)


class FichaDeLectura(Base):
    """Quien es quien, y **en que capitulos aparece** (RF-PUB-05, spec v3.1).

    Los capitulos no son un adorno de la entrada: la ficha existe para volver al
    pasaje, y una entrada que dice quien es alguien sin decir donde sale obliga a
    releer la novela para encontrarlo.

    `entradas` es JSON y no una tabla por entrada porque la ficha se escribe
    entera al publicar y se lee entera al abrir: no hay consulta que pida una
    entrada suelta, y normalizarla costaria una union para servir la portada.
    """

    __tablename__ = "ficha_de_lectura"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("version_publicada.id", name="fk_ficha_de_lectura_version_id"),
        unique=True,
    )
    entradas: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class CuadroDeDefectos(Base):
    """Lo que la version llevaba encima al publicarse.

    Cuelga de la version y no de la obra porque la Fase 5 clasifica los defectos
    en **preexistentes** e **introducidos**, y esa diferencia solo se puede
    calcular teniendo el cuadro de cada tirada. Guardar solo el ultimo haria la
    pregunta incontestable en cuanto se republicara una vez.
    """

    __tablename__ = "cuadro_de_defectos"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("version_publicada.id", name="fk_cuadro_de_defectos_version_id"),
        unique=True,
    )
    defectos: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class Dedicatoria(Base):
    """Del regalo, no de la tirada: republicar no la reescribe.

    Por eso cuelga de la obra y no de `VersionPublicada`. Y **no es prosa del
    manuscrito** (regla de dominio 15): no entra en el ensamblado, ni en el PDF
    como capitulo, ni en la lista negra de n-gramas. Confundirla con prosa la
    metria en el contexto del Escritor, que es justo lo que no debe pasar.
    """

    __tablename__ = "dedicatoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(
        ForeignKey("obra.id", name="fk_dedicatoria_obra_id"), unique=True
    )
    texto: Mapped[str] = mapped_column(Text)
