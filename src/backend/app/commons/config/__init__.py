"""API publica de commons/config."""

from app.commons.config.ajustes import Ajustes, AjustesInvalidos, cargar_ajustes

__all__ = ["Ajustes", "AjustesInvalidos", "cargar_ajustes"]
