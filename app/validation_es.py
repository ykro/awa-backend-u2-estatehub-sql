"""Mensajes de validación en español, comunes a las 3 unidades del Curso 1.

Copia canónica: curso1-backend-fastapi/shared/validation_es.py. Cada proyecto la incluye como
app/validation_es.py, idéntica byte a byte (scripts/check_course1.py lo verifica).

Uso en el handler de RequestValidationError:
    details = validation_details(exc.errors())
Devuelve solo loc, msg y type: nunca input ni ctx, para no repetir datos del cliente.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

_MESSAGES: dict[str, str] = {
    "missing": "Campo obligatorio",
    "extra_forbidden": "Campo no permitido",
    "greater_than": "Debe ser mayor que {gt}",
    "greater_than_equal": "Debe ser mayor o igual que {ge}",
    "less_than": "Debe ser menor que {lt}",
    "less_than_equal": "Debe ser menor o igual que {le}",
    "multiple_of": "Debe ser múltiplo de {multiple_of}",
    "int_type": "Debe ser un número entero",
    "int_parsing": "Debe ser un número entero válido",
    "int_from_float": "Debe ser un número entero, sin decimales",
    "float_type": "Debe ser un número",
    "float_parsing": "Debe ser un número válido",
    "finite_number": "Debe ser un número finito",
    "decimal_type": "Debe ser un número o un texto con el monto",
    "decimal_parsing": "Debe ser un monto numérico válido",
    "decimal_max_digits": "Admite como máximo {max_digits} dígitos",
    "decimal_max_places": "Admite como máximo {decimal_places} decimales",
    "decimal_whole_digits": "Admite como máximo {whole_digits} dígitos antes del punto decimal",
    "bool_type": "Debe ser verdadero o falso",
    "bool_parsing": "Debe ser verdadero o falso",
    "string_type": "Debe ser texto",
    "string_too_short": "Debe tener al menos {min_length} caracteres",
    "string_too_long": "Debe tener como máximo {max_length} caracteres",
    "string_pattern_mismatch": "No tiene el formato esperado",
    "string_unicode": "Debe ser texto Unicode válido",
    "too_short": "Debe tener al menos {min_length} elemento(s)",
    "too_long": "Debe tener como máximo {max_length} elemento(s)",
    "list_type": "Debe ser una lista",
    "dict_type": "Debe ser un objeto",
    "model_type": "Debe ser un objeto JSON",
    "model_attributes_type": "El cuerpo debe ser un objeto JSON",
    "enum": "Valor no permitido; usa {expected}",
    "literal_error": "Valor no permitido; usa {expected}",
    "json_invalid": "El cuerpo no es JSON válido",
    "json_type": "El cuerpo debe ser JSON",
    "datetime_type": "Debe ser una fecha y hora",
    "datetime_parsing": "Debe ser una fecha y hora ISO 8601 válida",
    "datetime_from_date_parsing": "Debe ser una fecha y hora ISO 8601 válida",
    "date_type": "Debe ser una fecha",
    "date_parsing": "Debe ser una fecha ISO 8601 válida",
    "timezone_aware": "Debe incluir la zona horaria",
    "uuid_type": "Debe ser un UUID",
    "uuid_parsing": "Debe ser un UUID válido",
    "none_required": "Debe ser nulo",
}
FALLBACK = "Valor inválido"


def _expected(raw: str) -> str:
    """Pydantic escribe "'a', 'b' or 'c'"; aquí queda "'a', 'b' o 'c'"."""
    return re.sub(r"\s+or\s+", " o ", raw)


def spanish_message(error: Mapping[str, Any]) -> str:
    kind = str(error.get("type", ""))
    if kind in ("value_error", "assertion_error"):
        msg = str(error.get("msg", ""))
        return msg.removeprefix("Value error, ").removeprefix("Assertion failed, ") or FALLBACK
    template = _MESSAGES.get(kind)
    if template is None:
        return FALLBACK
    ctx = {
        key: _expected(str(value)) if key == "expected" else value
        for key, value in (error.get("ctx") or {}).items()
    }
    try:
        return template.format(**ctx)
    except (KeyError, IndexError):
        return FALLBACK


def validation_details(errors: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"loc": list(e.get("loc", ())), "msg": spanish_message(e), "type": str(e.get("type", ""))}
        for e in errors
    ]
