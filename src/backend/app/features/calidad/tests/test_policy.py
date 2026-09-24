"""El hook de policy: RF-GUA-07 y P-5.

`CLAUDE.md` §11 pide **dos** hooks «fuera del bucle del modelo». El veto de
palabras funcionaba desde la Fase 1 pero vivia dentro de `escribir_capitulo`:
no tenia nombre, no se podia enumerar y **si alguien lo borraba no se enteraba
nadie**. Estos tests comprueban que ahora es una regla con nombre, con punto
declarado y con decision registrada.
"""

from app.features.calidad import (
    CATALOGO_DE_POLICY,
    CapituloAPolicy,
    PuntoDeEjecucion,
    aplicar_policy,
)


def test_el_catalogo_existe_y_declara_su_punto():
    """RF-GUA-07: el hook es un punto ENUMERABLE. Si esta vacio, no hay hook."""
    assert CATALOGO_DE_POLICY
    for regla in CATALOGO_DE_POLICY:
        assert regla.punto is PuntoDeEjecucion.HOOK_DE_POLICY
        assert regla.nombre


def test_un_veto_en_plural_bloquea_con_su_cita():
    texto = "Habia sangres por todo el suelo del invernadero."
    resultado = aplicar_policy(
        CapituloAPolicy(version_texto_id="7", texto=texto, vetos=("sangre",))
    )
    assert resultado.bloquea
    assert resultado.termino_vetado == "sangre"
    (defecto,) = resultado.defectos
    assert defecto.codigo == "SEG-02"
    assert defecto.cita == "sangres"
    assert texto[defecto.desplazamiento_inicio : defecto.desplazamiento_fin] == "sangres"


def test_lo_permitido_tambien_deja_su_decision():
    """RF-GUA-05: el registro dice que se permitio y que se bloqueo, y por que."""
    resultado = aplicar_policy(
        CapituloAPolicy(
            version_texto_id="7", texto="Nadia cerro el invernadero.", vetos=("cuchillo",)
        )
    )
    assert not resultado.bloquea
    (decision,) = resultado.decisiones
    assert decision.regla == "palabras_vetadas"
    assert decision.decision == "permitido"


def test_el_veto_no_salta_dentro_de_otra_palabra():
    """R-7: se compara por palabra, no por subcadena. `ana` no esta en `manana`."""
    resultado = aplicar_policy(
        CapituloAPolicy(version_texto_id="7", texto="Volvera manana temprano.", vetos=("ana",))
    )
    assert not resultado.bloquea
