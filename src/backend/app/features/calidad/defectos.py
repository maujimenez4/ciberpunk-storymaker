"""El `Defecto` y su cita (RF-CAL-08, D-06, `definitions.md` §8 y §11).

Un defecto sin cita no es reparable: el prompt de reparación necesita el pasaje,
no una descripción. Y la cita se ancla por **desplazamiento sobre una
`VersionDeTexto` inmutable** (axioma 11), que es lo que permite comprobar
mecánicamente que el Continuista no se la inventó.

La taxonomía está **cerrada** (`definitions.md` §8). Un código que no esté en
ella es fallo del paso (RF-ORQ-15), no un defecto: si se admitieran códigos
libres, la puerta G1a dejaría de poder decidir qué bloquea.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CodigoDeDefecto(StrEnum):
    """Taxonomía cerrada de `definitions.md` §8."""

    CAN_01 = "CAN-01"
    CON_01 = "CON-01"
    CON_02 = "CON-02"
    CON_03 = "CON-03"
    VOZ_01 = "VOZ-01"
    VOZ_02 = "VOZ-02"
    VOZ_03 = "VOZ-03"
    PRO_01 = "PRO-01"
    PRO_02 = "PRO-02"
    EST_01 = "EST-01"
    GEN_01 = "GEN-01"
    GEN_02 = "GEN-02"
    SEG_01 = "SEG-01"


# RF-CAL-09: los que bloquean la puerta G1a en la v1. Los de juicio -VOZ-01,
# VOZ-02, PRO-*, GEN-02- necesitan al Critico, que esta fuera de alcance, y por
# eso G1b no bloquea: fingir que la funcion dramatica se comprueba
# mecanicamente seria peor que declararla pendiente.
#
# **CAN-01 y CON-03 no bloquean todavia, y no es un olvido.** Decidido por
# maujimenez4 el 2026-09-23, con RF-CAL-09 incumplido a proposito y anotado en la
# spec. Los dos contrastan **texto libre por igualdad exacta** contra lo que
# escribio el Extractor, y son dos llamadas independientes al modelo: coinciden
# palabra por palabra solo por casualidad. Medido contra los validadores reales:
#
#   CON-03 se emite con cualquier objeto fisico ("la carpeta") y con
#   informacion que el personaje **si** presencio, dicha con otras palabras.
#   CAN-01 se emite cuando el mismo hecho se expresa de otra forma
#   ("no quiere firmar" contra "se niega a firmar").
#
# Bloqueando, cada falso positivo es una ESCALADA: trabajo humano por una
# contradiccion que no existe. Se registran igual -en `no_bloquean`, y de ahi a
# la tabla `defecto`- porque su tasa sobre una corrida real es justo el dato que
# hace falta para elegir el contraste bueno, y hoy no lo tenemos. Vuelven a
# bloquear cuando ese contraste deje de comparar cadenas.
#
# CON-01 si bloquea: contrasta dos afirmaciones **del propio Continuista** entre
# si -el mismo sujeto en dos lugares en el mismo momento-, sin casar nada contra
# el ledger, asi que no tiene el problema.
BLOQUEANTES_EN_G1A = frozenset(
    {
        CodigoDeDefecto.CON_01,
        CodigoDeDefecto.CON_02,
        CodigoDeDefecto.EST_01,
        CodigoDeDefecto.SEG_01,
        CodigoDeDefecto.VOZ_03,
    }
)


class Defecto(BaseModel):
    """Lo que devuelve un validador. Con código, cita y anclaje."""

    model_config = ConfigDict(frozen=True)

    codigo: CodigoDeDefecto
    version_texto_id: str = Field(min_length=1)
    cita: str = Field(min_length=1)
    desplazamiento_inicio: int = Field(ge=0)
    desplazamiento_fin: int = Field(gt=0)
    # Axioma 12: obligatorio en CAN-01. Es condicional por fila, asi que lo
    # comprueba la comprobacion de forma y no una restriccion de columna.
    hecho_canon_id: str | None = None
    # architecture.md §8.3: un defecto mal formado no bloquea ni consume
    # reintento, pero **se registra**. Es hoy la unica senal directa de que el
    # Continuista afirma cosas que no estan en el texto.
    bien_formado: bool = True
    detalle: str = ""

    @model_validator(mode="after")
    def la_cita_no_esta_vacia(self) -> "Defecto":
        if self.desplazamiento_fin <= self.desplazamiento_inicio:
            raise ValueError(
                f"la cita del defecto {self.codigo} va de "
                f"{self.desplazamiento_inicio} a {self.desplazamiento_fin}: "
                f"una cita vacia no ancla nada"
            )
        return self

    def bloquea_g1a(self) -> bool:
        """RF-CAL-09 y RF-CAL-11: uno mal formado **no** bloquea."""
        return self.bien_formado and self.codigo in BLOQUEANTES_EN_G1A


def citar(
    texto: str,
    fragmento: str,
    codigo: CodigoDeDefecto,
    version_texto_id: str,
    hecho_canon_id: str | None = None,
    detalle: str = "",
) -> Defecto:
    """Construye un defecto anclando el fragmento sobre el texto real.

    Se busca el fragmento en vez de recibir los desplazamientos porque así el
    anclaje es correcto **por construcción**: un validador no puede emitir una
    cita que no esté en el texto, que es la mitad de lo que comprueba RF-CAL-11.
    """
    inicio = texto.find(fragmento)
    if inicio < 0:
        raise ValueError(
            f"el fragmento citado no aparece en la version {version_texto_id}: "
            f"{fragmento!r}"
        )
    return Defecto(
        codigo=codigo,
        version_texto_id=version_texto_id,
        cita=fragmento,
        desplazamiento_inicio=inicio,
        desplazamiento_fin=inicio + len(fragmento),
        hecho_canon_id=hecho_canon_id,
        detalle=detalle,
    )


def citar_del_modelo(
    texto: str,
    fragmento: str,
    codigo: CodigoDeDefecto,
    version_texto_id: str,
    hecho_canon_id: str | None = None,
    detalle: str = "",
) -> Defecto | None:
    """Como `citar`, pero la cita **la escribio el modelo** y puede no estar.

    La diferencia con `citar` no es de estilo. Alli el fragmento sale del propio
    texto -`texto[posicion:posicion + len(termino)]`- y que aparezca esta
    garantizado por construccion; aqui lo escribe el Continuista, y que no
    aparezca **es el dato**, no un error de programacion: el modelo parafraseo.

    Reventar con `ValueError` dejaba ese caso sin llegar a ninguna parte. Toda la
    maquinaria que existe para juzgarlo -`comprobar_forma`, los axiomas 11 y 12,
    la tasa de mal formados de §9- vive aguas abajo, en la puerta, y para que un
    defecto mal formado se registre primero tiene que construirse. En la primera
    corrida real con Continuista la excepcion subio por `ciclo_de_escena` y mato
    el proceso en la escena 1.

    Asi que se construye igual, anclado al principio del texto. **No lo declara
    mal formado**: eso lo decide `comprobar_forma`, que comparara la cita con lo
    que hay en el desplazamiento y no cuadrara. El juicio se queda donde estaba;
    lo que se arregla es que el caso llegue hasta el.

    Devuelve `None` cuando no hay cita ninguna: sin pasaje no hay defecto
    reparable (regla 8), y un `Defecto` sin cita no se puede ni construir.
    """
    if not fragmento:
        return None
    if texto.find(fragmento) >= 0:
        return citar(
            texto, fragmento, codigo, version_texto_id, hecho_canon_id, detalle
        )
    return Defecto(
        codigo=codigo,
        version_texto_id=version_texto_id,
        cita=fragmento,
        desplazamiento_inicio=0,
        desplazamiento_fin=len(fragmento),
        hecho_canon_id=hecho_canon_id,
        detalle=detalle,
    )
