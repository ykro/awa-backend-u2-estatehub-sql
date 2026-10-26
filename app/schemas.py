from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

PropertyStatus = Literal["available", "reserved", "sold"]

MIN_VISIT_MINUTES = 15
MAX_VISIT_MINUTES = 240
MAX_ID = 2_147_483_647
MAX_PAGE = 10_000
MAX_PRICE = 50_000_000


def normalize_utc(dt: datetime) -> datetime:
    """Convierte cualquier fecha a UTC. Una fecha sin zona horaria se interpreta como UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    try:
        return dt.astimezone(UTC)
    except OverflowError as exc:
        raise ValueError("La fecha queda fuera del rango admitido al convertirla a UTC.") from exc


def window_error(start: datetime, end: datetime) -> str | None:
    """Devuelve el motivo por el que la ventana [start, end) es inválida, o None si es válida."""
    if end <= start:
        return "La fecha de fin (scheduled_end) debe ser posterior a scheduled_start."
    minutes = (end - start).total_seconds() / 60.0
    if minutes < MIN_VISIT_MINUTES or minutes > MAX_VISIT_MINUTES:
        return f"La visita debe durar entre {MIN_VISIT_MINUTES} y {MAX_VISIT_MINUTES} minutos."
    return None


def mask_email(email: str) -> str:
    """Enmascara un correo para respuestas públicas: valeria@ejemplo.com -> v***@ejemplo.com."""
    local, _, domain = email.partition("@")
    if not local or not domain:
        return "***"
    return f"{local[0]}***@{domain}"


# Toda fecha de respuesta (y de consulta) se expresa en UTC.
UtcDatetime = Annotated[datetime, AfterValidator(normalize_utc)]


class AgencyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=100, description="Nombre de la agencia")
    email: str = Field(..., min_length=5, max_length=120, description="Correo de contacto")
    phone: str = Field(..., min_length=6, max_length=40, description="Teléfono comercial")

    @field_validator("name", "email", "phone")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El campo no puede estar vacío ni contener solo espacios.")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("El correo electrónico debe tener un formato válido.")
        return value.lower()


class AgencyResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    created_at: UtcDatetime


class PropertyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agency_id: int = Field(..., gt=0, le=MAX_ID, description="ID de la agencia propietaria")
    title: str = Field(..., min_length=3, max_length=140, description="Título del inmueble")
    city: str = Field(..., min_length=2, max_length=80, description="Ciudad de ubicación")
    price: int = Field(..., gt=0, le=MAX_PRICE, description="Precio entero en USD")
    bedrooms: int = Field(..., ge=1, le=20, description="Número de habitaciones")
    status: PropertyStatus = Field(default="available", description="Estado comercial")

    @field_validator("title", "city")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El texto no puede estar vacío.")
        return cleaned


class PropertyResponse(BaseModel):
    id: int
    agency_id: int
    agency_name: str
    title: str
    city: str
    price: int
    bedrooms: int
    status: PropertyStatus
    created_at: UtcDatetime


class PaginatedPropertiesResponse(BaseModel):
    items: list[PropertyResponse]
    total: int
    page: int
    size: int
    pages: int


class VisitCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visitor_name: str = Field(..., min_length=2, max_length=100)
    visitor_email: str = Field(..., min_length=5, max_length=120)
    scheduled_start: datetime = Field(..., description="Inicio de la visita en ISO-8601")
    scheduled_end: datetime = Field(..., description="Fin de la visita en ISO-8601")
    notes: str = Field(default="", max_length=280)

    @field_validator("visitor_name", "visitor_email")
    @classmethod
    def strip_visitor_fields(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El campo del visitante no puede estar vacío.")
        return cleaned

    @field_validator("visitor_email")
    @classmethod
    def validate_visitor_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("El correo del visitante debe ser válido.")
        return value.lower()

    @model_validator(mode="after")
    def validate_time_window(self) -> VisitCreate:
        start_utc = normalize_utc(self.scheduled_start)
        end_utc = normalize_utc(self.scheduled_end)
        problem = window_error(start_utc, end_utc)
        if problem is not None:
            raise ValueError(problem)
        self.scheduled_start = start_utc
        self.scheduled_end = end_utc
        return self


class VisitResponse(BaseModel):
    id: int
    property_id: int
    visitor_name: str
    visitor_email_masked: str = Field(description="Correo enmascarado; el completo no es público")
    scheduled_start: UtcDatetime
    scheduled_end: UtcDatetime
    notes: str
    created_at: UtcDatetime


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
