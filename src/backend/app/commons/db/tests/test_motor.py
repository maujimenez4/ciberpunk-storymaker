from pathlib import Path

from sqlalchemy import text

from app.commons.db.motor import crear_motor


async def test_la_conexion_trae_wal_claves_foraneas_y_espera(tmp_path: Path):
    motor = crear_motor(tmp_path / "obra.db")
    async with motor.connect() as con:
        modo = (await con.execute(text("PRAGMA journal_mode"))).scalar_one()
        claves = (await con.execute(text("PRAGMA foreign_keys"))).scalar_one()
        espera = (await con.execute(text("PRAGMA busy_timeout"))).scalar_one()
    assert modo.lower() == "wal"
    assert claves == 1
    assert espera >= 5000
    await motor.dispose()


async def test_la_fixture_sesion_trabaja_sobre_la_base_del_test(sesion, tmp_path: Path):
    """Las fixtures `motor` y `sesion` las consumen las Tareas 4, 8, 9 y 10.

    Se prueban aqui, donde nacen, y no alli: una fixture que solo se ejecuta
    por primera vez en la ola siguiente hace fallar la tarea de otro agente
    con un error que no es suyo.
    """
    fichero = (await sesion.execute(text("PRAGMA database_list"))).all()[0][2]
    assert Path(fichero).parent == tmp_path
    assert (await sesion.execute(text("PRAGMA foreign_keys"))).scalar_one() == 1
