from datetime import UTC, datetime, timedelta

from app.commons.domain.reloj import Reloj, RelojDelSistema, RelojFijo


def test_el_reloj_del_sistema_devuelve_una_hora_con_zona():
    """Sin zona, comparar con una fecha de la base de datos da un error mudo.

    Si alguien cambiara `datetime.now(UTC)` por `datetime.now()`, ningun test
    se pondria rojo y el fallo saldria mucho mas tarde, al restar dos fechas
    de las que solo una sabe donde esta. Este test es lo que lo impide.
    """
    ahora = RelojDelSistema().ahora()
    assert ahora.tzinfo is not None
    assert ahora.utcoffset() == timedelta(0)


def test_el_reloj_del_sistema_avanza():
    reloj = RelojDelSistema()
    assert reloj.ahora() <= reloj.ahora()


def test_el_reloj_fijo_no_avanza():
    """Es lo unico que lo hace util: dos lecturas iguales hacen el test reproducible."""
    momento = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
    reloj = RelojFijo(momento)
    assert reloj.ahora() == momento
    assert reloj.ahora() == reloj.ahora()


def test_los_dos_relojes_sirven_donde_se_espera_el_protocolo():
    """RI-14: el reloj se inyecta. Si un doble no encaja, no se puede probar nada."""
    relojes: list[Reloj] = [RelojDelSistema(), RelojFijo(datetime.now(UTC))]
    assert all(isinstance(r.ahora(), datetime) for r in relojes)
