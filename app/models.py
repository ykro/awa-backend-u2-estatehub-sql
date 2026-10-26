import unicodedata
from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


def make_city_key(city: str) -> str:
    """Clave de búsqueda de ciudad: NFC + casefold (SQLite lower() solo baja ASCII)."""
    return unicodedata.normalize("NFC", city.strip()).casefold()


class Agency(SQLModel, table=True):
    """Tabla relacional de agencias inmobiliarias."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=2, max_length=100)
    email: str = Field(index=True, max_length=120)
    phone: str = Field(max_length=40)
    created_at: datetime = Field(default_factory=utc_now)

    properties: list["Property"] = Relationship(back_populates="agency")


class Property(SQLModel, table=True):
    """Tabla relacional de propiedades inmobiliarias vinculadas a una agencia."""

    id: int | None = Field(default=None, primary_key=True)
    agency_id: int = Field(foreign_key="agency.id", index=True)
    title: str = Field(min_length=3, max_length=140)
    city: str = Field(min_length=2, max_length=80)
    city_key: str = Field(default="", index=True, max_length=80)
    price: int = Field(gt=0, index=True, description="Precio entero en USD, sin flotantes")
    bedrooms: int = Field(ge=1, le=20, index=True)
    status: str = Field(default="available", index=True)
    created_at: datetime = Field(default_factory=utc_now)

    agency: Agency | None = Relationship(back_populates="properties")
    visits: list["Visit"] = Relationship(back_populates="property")


class Visit(SQLModel, table=True):
    """Tabla relacional de visitas agendadas sobre una propiedad.

    SQLModel declara estas columnas como UTCDateTime: exige fechas con zona horaria,
    las guarda en UTC y las devuelve en UTC. Una fecha sin zona provoca un error al guardar.
    """

    id: int | None = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    visitor_name: str = Field(min_length=2, max_length=100)
    visitor_email: str = Field(max_length=120)
    scheduled_start: datetime = Field(index=True)
    scheduled_end: datetime = Field(index=True)
    notes: str = Field(default="", max_length=280)
    created_at: datetime = Field(default_factory=utc_now)

    property: Property | None = Relationship(back_populates="visits")
