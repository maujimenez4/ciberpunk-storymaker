from datetime import UTC, date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.commons.domain.normalizacion import contiene_veto

TextoNoVacio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

EDAD_MINIMA_CONTENIDO_ADULTO = 18
CALOR_QUE_EXIGE_MAYORIA = 2


class DestinatarioEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    edad: int = Field(ge=0, le=120)
    rasgos: list[str] = Field(default_factory=list)
    recuerdos: list[str] = Field(default_factory=list)
    fecha_de_nacimiento: date | None = None


class BriefEntrada(BaseModel):
    destinatario: DestinatarioEntrada
    genero: str
    tono: str
    nivel_de_calor: int = Field(ge=0, le=4)
    vetos: list[str] = Field(default_factory=list)
    elementos_obligatorios: list[TextoNoVacio] = Field(min_length=1)

    @model_validator(mode="after")
    def sin_contenido_adulto_con_menores(self) -> "BriefEntrada":
        """Regla de dominio 6. 18 NO es menor: la comparacion es estricta."""
        if (
            self.destinatario.edad < EDAD_MINIMA_CONTENIDO_ADULTO
            and self.nivel_de_calor >= CALOR_QUE_EXIGE_MAYORIA
        ):
            raise ValueError("nivel_de_calor incompatible con un destinatario menor de 18 anos")
        return self

    @model_validator(mode="after")
    def la_edad_concuerda_con_la_fecha_de_nacimiento(self) -> "BriefEntrada":
        """Regla de dominio 13, cazada en la entrevista y no en G4.

        Si esta contradiccion entra aqui, sobrevive los diez capitulos y la
        detecta Lean al publicar, con la novela entera ya escrita.
        """
        nacimiento = self.destinatario.fecha_de_nacimiento
        if nacimiento is None:
            return self
        # `date.today()` —lo que pedia el plan— no pasa `ruff` (DTZ011) y ademas
        # lee la zona de la maquina, mientras `RelojDelSistema.ahora()` trabaja
        # en UTC: dos "hoy" distintos en el mismo sistema. Se usa UTC, que es el
        # que ya tiene el resto del proyecto. El reloj no se inyecta aqui porque
        # un validador de Pydantic no es un servicio y pasarle contexto cambiaria
        # la firma de `BriefEntrada`, que T7 y T9 ya consumen.
        hoy = datetime.now(UTC).date()
        calculada = (
            hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        )
        if abs(calculada - self.destinatario.edad) > 1:
            raise ValueError(
                f"edad {self.destinatario.edad} no concuerda con "
                f"fecha_de_nacimiento {nacimiento} (seran {calculada})"
            )
        return self

    @model_validator(mode="after")
    def ningun_veto_choca_con_el_nombre_del_destinatario(self) -> "BriefEntrada":
        """R-8. Una contradiccion del brief (RF-ENT-04), cerrada donde se ve.

        `contiene_veto` compara por palabra y `\\w+` parte "Garcia-Ortiz" en
        dos, asi que el veto "Ortiz" saltaria sobre el nombre de la persona a
        quien va el regalo, en cada capitulo de la Fase 2. El tokenizador NO se
        afloja: eso compraria este falso positivo a cambio de falsos negativos,
        y un veto que deja de saltar es peor que uno que salta de mas (R-3).

        La garantia que hace falta —que ningun veto choque con el nombre del
        destinatario— no la puede dar el tokenizador, porque solo ve el texto.
        Aqui estan los dos datos a la vez, y es el ultimo sitio donde corregirla
        cuesta una pregunta en vez de una novela entera.
        """
        choque = contiene_veto(self.destinatario.nombre, self.vetos)
        if choque is not None:
            raise ValueError(
                f"el veto {choque!r} coincide con el nombre del destinatario "
                f"{self.destinatario.nombre!r}: elige otro veto o corrige el nombre"
            )
        return self


class RespuestasEntrada(BaseModel):
    """Lo que el comprador manda a RI-02. Entrada, y solo entrada.

    `respuestas` es un diccionario abierto a proposito: la entrevista se
    responde a trozos y un esquema cerrado obligaria a mandarla entera de una
    vez, que es justo lo que RF-ENT-03 existe para evitar. La forma se exige
    **al cerrar**, contra `BriefEntrada`; aqui solo se acumula.
    """

    respuestas: dict[str, Any] = Field(default_factory=dict)
    texto_aportado: str = ""


class EntrevistaAbierta(BaseModel):
    """Salida de RI-01. Nunca se expone el modelo de base de datos."""

    id: int


class ContradiccionSalida(BaseModel):
    """Los mismos dos campos que devuelve el Entrevistador, ni uno mas."""

    campos: list[str]
    explicacion: str


class EvaluacionSalida(BaseModel):
    """Salida de RI-02: que falta y que se contradice, nombrado (CA-2)."""

    faltantes: list[str]
    contradicciones: list[ContradiccionSalida]


class ObraCreada(BaseModel):
    """Salida de RI-03. La segunda llamada devuelve el mismo `obra_id` (R-5)."""

    obra_id: int
