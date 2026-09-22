"""P-05: toda conexion nace con WAL, foreign_keys y busy_timeout (RI-16).

Las tres son PRAGMA **por conexion**, no propiedades del fichero: se aplican en
cada apertura o no estan. Por eso el test abre dos conexiones distintas: una
fabrica que solo configure la primera pasaria una comprobacion ingenua y dejaria
el resto del proceso sin integridad referencial.
"""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.commons.db import BUSY_TIMEOUT_MS, crear_motor


async def _pragmas(motor: AsyncEngine) -> dict[str, object]:
    async with motor.connect() as conexion:
        return {
            nombre: (await conexion.exec_driver_sql(f"PRAGMA {nombre}")).scalar()
            for nombre in ("journal_mode", "foreign_keys", "busy_timeout")
        }


async def test_conexion_tiene_wal_foreign_keys_y_busy_timeout(tmp_path: Path) -> None:
    motor = crear_motor(tmp_path / "obra.db")
    try:
        valores = await _pragmas(motor)
        assert valores["journal_mode"] == "wal"
        assert valores["foreign_keys"] == 1
        assert valores["busy_timeout"] == BUSY_TIMEOUT_MS
    finally:
        await motor.dispose()


async def test_los_pragmas_valen_para_toda_conexion_no_solo_la_primera(
    tmp_path: Path,
) -> None:
    motor = crear_motor(tmp_path / "obra.db")
    try:
        primera = await _pragmas(motor)
        await motor.dispose()  # tira el pool: la siguiente abre de cero
        segunda = await _pragmas(motor)
        assert primera == segunda
        assert segunda["foreign_keys"] == 1
    finally:
        await motor.dispose()


async def test_las_claves_ajenas_se_aplican_de_verdad(tmp_path: Path) -> None:
    """foreign_keys=ON sin comprobarlo es la ilusion mas cara: SQLite lo ignora
    en silencio si el PRAGMA no llego a esa conexion."""
    from sqlalchemy.exc import IntegrityError

    motor = crear_motor(tmp_path / "obra.db")
    try:
        async with motor.begin() as conexion:
            await conexion.exec_driver_sql(
                "CREATE TABLE padre (id INTEGER PRIMARY KEY)"
            )
            await conexion.exec_driver_sql(
                "CREATE TABLE hijo (id INTEGER PRIMARY KEY,"
                " padre_id INTEGER REFERENCES padre(id))"
            )
        try:
            async with motor.begin() as conexion:
                await conexion.exec_driver_sql("INSERT INTO hijo VALUES (1, 99)")
        except IntegrityError:
            pass
        else:
            raise AssertionError("SQLite acepto una clave ajena inexistente")
    finally:
        await motor.dispose()
