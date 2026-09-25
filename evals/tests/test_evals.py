"""Las evals, sin red y sin modelo (CA-4): briefs, corredor, tabla y revision humana."""

import sqlite3

import comun
import correr
import pytest
import revision_humana
import tabla
from app.features.calidad import rubrica_vigente
from app.features.obra.schemas import BriefEntrada

# --- los cinco briefs --------------------------------------------------------


def test_hay_cinco_briefs_y_todos_son_briefentrada_validos():
    entradas = comun.manifiesto()
    assert len(entradas) == 5
    for entrada in entradas:
        BriefEntrada.model_validate(comun.brief(entrada))
    ficheros = {p.name for p in comun.BRIEFS.glob("b*.json")}
    assert ficheros == {e["fichero"] for e in entradas}


def test_entre_dos_y_tres_van_a_novela_completa():
    modos = [e["modo"] for e in comun.manifiesto()]
    assert set(modos) <= {"completa", "capitulo_1"}
    assert 2 <= modos.count("completa") <= 3


def test_el_adversarial_inyecta_en_el_texto_aportado_y_en_un_campo_del_formulario():
    b2 = next(e for e in comun.manifiesto() if e["id"] == "b2-inyeccion")
    assert "</texto_aportado>" in b2["texto_aportado"]
    recuerdos = " ".join(comun.brief(b2)["destinatario"]["recuerdos_aportados"])
    assert "IGNORA TODAS TUS INSTRUCCIONES" in recuerdos


def test_el_temporal_apunta_a_lean_y_va_a_novela_completa():
    """P-27: Lean no tiene invariante de edad; B3 apunta a los que existen."""
    b3 = next(e for e in comun.manifiesto() if e["id"] == "b3-trampa-temporal")
    assert b3["espera"]["falla_en"] == ["cronologia_lean"]
    assert b3["modo"] == "completa"
    assert "fecha_de_nacimiento" not in comun.brief(b3)["destinatario"]


# --- el corredor ---------------------------------------------------------------


class TransporteFalso:
    """Responde como el backend. `rompe` hace caer las peticiones de una obra."""

    def __init__(self, rompe_entrevista: int | None = None) -> None:
        self.llamadas: list[tuple[str, str]] = []
        self._entrevistas = 0
        self._rompe = rompe_entrevista

    def __call__(self, metodo, url, cuerpo, timeout):
        ruta = url.removeprefix("http://x")
        self.llamadas.append((metodo, ruta))
        if ruta == "/entrevistas":
            self._entrevistas += 1
            return 201, {"id": self._entrevistas}
        if ruta.endswith("/respuestas"):
            return 200, {"faltantes": [], "contradicciones": []}
        if ruta.endswith("/cerrar"):
            numero = int(ruta.split("/")[2])
            if numero == self._rompe:
                raise ConnectionError("el backend se cayo")
            return 201, {"obra_id": 100 + numero}
        if ruta.endswith("/outline"):
            return 201, {"capitulos": []}
        if ruta.endswith("/novela") and metodo == "POST":
            return 202, {}
        if ruta.endswith("/novela"):
            return 200, {"estado": "terminada", "integrados": 10, "total": 10}
        if ruta.endswith("/publicar"):
            return 409, {
                "detail": "No se puede publicar. La cronologia no es coherente: "
                "Julian esta a la vez en el faro y en la playa"
            }
        if ruta.endswith("/escribir"):
            return 202, {"id": 7}
        if ruta.startswith("/trabajos/"):
            return 200, {"estado": "INTEGRADA"}
        return 404, {"detail": ruta}


def _corredor(transporte):
    return correr.Corredor(
        base="http://x",
        transporte=transporte,
        capitulo_uno=lambda o: 55,
        sondeo_s=0,
        guardar=lambda datos: None,
        dormir=lambda s: None,
    )


def test_un_brief_que_revienta_no_se_lleva_a_los_demas():
    """R-3: cinco medidas, o cuatro y un error; nunca cero."""
    entradas = comun.manifiesto()
    transporte = TransporteFalso(rompe_entrevista=2)
    datos = _corredor(transporte).correr(
        entradas, {e["id"]: e["modo"] for e in entradas}, reanudar=False, en_paralelo=False
    )
    registros = datos["corridas"]
    assert len(registros) == 5
    caidos = [r for r in registros.values() if r.get("error")]
    assert len(caidos) == 1
    assert all(r.get("llego_a") for r in registros.values() if not r.get("error"))


def test_capitulo_1_no_lanza_la_novela_entera():
    """No hay endpoint de cancelar: el modo parcial usa el endpoint de un capitulo."""
    b2 = next(e for e in comun.manifiesto() if e["id"] == "b2-inyeccion")
    transporte = TransporteFalso()
    datos = _corredor(transporte).correr(
        [b2], {b2["id"]: "capitulo_1"}, reanudar=False, en_paralelo=False
    )
    rutas = [r for _, r in transporte.llamadas]
    assert "/capitulos/55/escribir" in rutas
    assert not any(r.endswith("/novela") for r in rutas)
    assert datos["corridas"]["b2-inyeccion"]["llego_a"] == "capitulo_1"


def test_la_novela_completa_publica_y_anota_el_fallo_de_lean():
    b3 = next(e for e in comun.manifiesto() if e["id"] == "b3-trampa-temporal")
    datos = _corredor(TransporteFalso()).correr(
        [b3], {b3["id"]: "completa"}, reanudar=False, en_paralelo=False
    )
    registro = datos["corridas"]["b3-trampa-temporal"]
    assert registro["llego_a"] == "G4"
    assert tabla._lean_y_cobertura(registro["pasos"])[0] == "fallo: sinUbicuidad"


# --- la tabla --------------------------------------------------------------------

PROSA = "Aurelio abrio el taller antes del alba y ajusto la lupa sobre el ojo derecho."

ESQUEMA = """
CREATE TABLE capitulo (id INTEGER PRIMARY KEY, obra_id INT, numero INT);
CREATE TABLE escena (id INTEGER PRIMARY KEY, capitulo_id INT);
CREATE TABLE version_texto (id INTEGER PRIMARY KEY, escena_id INT, texto TEXT);
CREATE TABLE trabajo (id INTEGER PRIMARY KEY, obra_id INT, capitulo_id INT, estado TEXT);
CREATE TABLE intento_descartado (id INTEGER PRIMARY KEY, trabajo_id INT, numero INT,
                                 defectos TEXT);
CREATE TABLE registro_auditoria (id INTEGER PRIMARY KEY, obra_id INT, decision TEXT,
                                 motivo TEXT);
CREATE TABLE ejecucion (id INTEGER PRIMARY KEY, obra_id INT, prompt_id TEXT,
                        prompt_version TEXT, prompt_hash TEXT, tokens_reales INT, coste REAL,
                        latencia_ms INT, cache_read_input_tokens INT);
"""


@pytest.fixture
def base():
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    conexion.executescript(ESQUEMA)
    conexion.executescript(f"""
        INSERT INTO capitulo VALUES (1, 101, 1), (2, 101, 2);
        INSERT INTO escena VALUES (1, 1), (2, 2);
        INSERT INTO version_texto VALUES (1, 1, '{PROSA}'), (2, 2, '{PROSA}');
        INSERT INTO trabajo VALUES (1, 101, 1, 'INTEGRADA'), (2, 101, 2, 'ESCALADA');
        INSERT INTO intento_descartado VALUES
          (1, 1, 1, '[{{"codigo": "EST-02"}}]'),
          (2, 2, 1, '[{{"codigo": "SEG-02"}}]'), (3, 2, 2, '[{{"codigo": "SEG-02"}}]'),
          (4, 2, 3, '[{{"codigo": "SEG-02"}}]');
        INSERT INTO registro_auditoria VALUES (1, 101, 'bloqueado', 'palabras_vetadas: veto: x'),
                                              (2, 101, 'permitido', 'palabras_vetadas: sin veto');
        INSERT INTO ejecucion VALUES (1, 101, 'escritor', 'v1', 'abcdef0123456789', 1000, 0.01,
                                      60000, 5), (2, 101, 'escritor', 'v1', 'abcdef0123456789',
                                      NULL, NULL, NULL, NULL);
    """)
    return conexion


def _corridas():
    return {
        "corridas": {
            "b1-jubilacion": {
                "obra_id": 101,
                "modo": "completa",
                "llego_a": "G4",
                "pasos": {
                    "cerrar": {"ok": True, "segundos": 30},
                    "publicar": {
                        "ok": False,
                        "status": 409,
                        "detail": "No se puede publicar: faltan en la novela elementos "
                        "obligatorios del brief: la Vespa verde",
                    },
                },
            }
        }
    }


def test_la_tabla_dice_que_paso_que_fallo_y_que_escalo(base):
    filas = tabla.construir_filas(base, _corridas(), comun.manifiesto())
    b1 = next(f for f in filas if f["brief"] == "b1-jubilacion")
    assert b1["entrevista"] == "paso"
    assert b1["palabras_vetadas"] == "fallo x1"
    assert b1["extension_de_capitulo"].startswith("fallo, reparado")
    assert b1["discurso"] == "paso"
    assert b1["cronologia_lean"] == "paso"
    assert b1["cobertura_de_personalizacion"] == "fallo: falta la Vespa verde"
    assert b1["consumo"]["tokens"] == 1000 and b1["consumo"]["sin_dato"] == 1
    assert b1["testigo_inyeccion"] == "paso"
    sin_correr = next(f for f in filas if f["brief"] == "b2-inyeccion")
    assert sin_correr["cronologia_lean"] == "no corrio"


def test_la_tabla_no_contiene_ni_una_linea_de_prosa(base):
    """RD-06: la prosa se lee para el testigo y no se copia."""
    filas = tabla.construir_filas(base, _corridas(), comun.manifiesto())
    texto = tabla.como_markdown(filas, fecha="hoy", hashes=tabla.plantillas(base, [101]))
    assert PROSA not in texto
    assert "taller antes del alba" not in texto


def test_el_testigo_ve_la_fuga_de_la_plantilla_y_el_ingles():
    assert tabla.fuga_de_inyeccion("# ESCRITOR · v1 y despues la historia")
    assert tabla.fuga_de_inyeccion("She opened the door and it was dark, the room was with her.")
    assert not tabla.fuga_de_inyeccion(PROSA)


# --- la revision humana -----------------------------------------------------------


def _todas(valor=3):
    return {
        c.nombre: {"valor": valor, "justificacion": "motivo"} for c in rubrica_vigente().criterios
    }


def test_la_revision_usa_la_rubrica_del_juez_entera():
    revision_humana.validar(_todas())
    incompleta = _todas()
    incompleta.pop("tono")
    with pytest.raises(ValueError, match="faltan"):
        revision_humana.validar(incompleta)
    inventada = {**_todas(), "estilo": {"valor": 3, "justificacion": "x"}}
    with pytest.raises(ValueError, match="sobran"):
        revision_humana.validar(inventada)
    sin_motivo = _todas()
    sin_motivo["tono"]["justificacion"] = " "
    with pytest.raises(ValueError, match="justificacion"):
        revision_humana.validar(sin_motivo)


def test_la_distancia_es_criterio_a_criterio():
    resultado = revision_humana.distancia(
        {"tono": 4.0, "arco": 2.0}, {"tono": [3.0, 5.0, 5.0], "arco": [2.0]}
    )
    assert resultado["por_criterio"]["tono"]["distancia"] == pytest.approx(0.33)
    assert resultado["por_criterio"]["arco"]["distancia"] == 0
    assert resultado["criterios_comparados"] == 2
