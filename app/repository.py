from __future__ import annotations

from sqlmodel import Session, col, select

from app.database import begin_write
from app.models import Agency, Property, Visit, make_city_key
from app.schemas import (
    AgencyCreate,
    AgencyResponse,
    PaginatedPropertiesResponse,
    PropertyCreate,
    PropertyResponse,
    VisitCreate,
    VisitResponse,
    mask_email,
)


class DomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class AgencyNotFoundError(DomainError):
    def __init__(self, agency_id: int) -> None:
        super().__init__(
            code="AGENCY_NOT_FOUND",
            message=f"La agencia con id {agency_id} no existe.",
            status_code=404,
        )


class PropertyNotFoundError(DomainError):
    def __init__(self, property_id: int) -> None:
        super().__init__(
            code="PROPERTY_NOT_FOUND",
            message=f"La propiedad con id {property_id} no existe.",
            status_code=404,
        )


class VisitNotFoundError(DomainError):
    def __init__(self, visit_id: int) -> None:
        super().__init__(
            code="VISIT_NOT_FOUND",
            message=f"La visita con id {visit_id} no existe para esta propiedad.",
            status_code=404,
        )


class VisitSlotConflictError(DomainError):
    def __init__(self, property_id: int) -> None:
        super().__init__(
            code="VISIT_SLOT_CONFLICT",
            message=f"La propiedad {property_id} ya tiene una visita en ese horario.",
            status_code=409,
        )


class PropertyUnavailableError(DomainError):
    def __init__(self, property_id: int, status: str) -> None:
        super().__init__(
            code="PROPERTY_UNAVAILABLE",
            message=f"La propiedad {property_id} tiene estado '{status}' y no admite visitas.",
            status_code=409,
        )


def to_visit_response(visit: Visit) -> VisitResponse:
    """Convierte la fila Visit en el contrato público (correo enmascarado, fechas en UTC)."""
    return VisitResponse(
        id=visit.id,
        property_id=visit.property_id,
        visitor_name=visit.visitor_name,
        visitor_email_masked=mask_email(visit.visitor_email),
        scheduled_start=visit.scheduled_start,
        scheduled_end=visit.scheduled_end,
        notes=visit.notes,
        created_at=visit.created_at,
    )


def to_property_response(prop: Property, agency_name: str) -> PropertyResponse:
    return PropertyResponse(
        id=prop.id,
        agency_id=prop.agency_id,
        agency_name=agency_name,
        title=prop.title,
        city=prop.city,
        price=prop.price,
        bedrooms=prop.bedrooms,
        status=prop.status,
        created_at=prop.created_at,
    )


class EstateRepository:
    """Capa de acceso a datos y reglas de dominio relacionales (SQLModel, starter)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # =========================================================================
    # MÉTODOS DEMO (entregados funcionando como ejemplo resuelto)
    # =========================================================================

    def create_agency(self, payload: AgencyCreate) -> AgencyResponse:
        agency = Agency(
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
        )
        self.session.add(agency)
        self.session.commit()
        self.session.refresh(agency)
        return AgencyResponse(
            id=agency.id,
            name=agency.name,
            email=agency.email,
            phone=agency.phone,
            created_at=agency.created_at,
        )

    def list_agencies(self) -> list[AgencyResponse]:
        statement = select(Agency).order_by(col(Agency.id).asc())
        rows = self.session.exec(statement).all()
        return [
            AgencyResponse(
                id=row.id,
                name=row.name,
                email=row.email,
                phone=row.phone,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_property(self, payload: PropertyCreate) -> PropertyResponse:
        agency = self.session.get(Agency, payload.agency_id)
        if agency is None:
            raise AgencyNotFoundError(payload.agency_id)

        prop = Property(
            agency_id=payload.agency_id,
            title=payload.title,
            city=payload.city,
            city_key=make_city_key(payload.city),
            price=payload.price,
            bedrooms=payload.bedrooms,
            status=payload.status,
        )
        self.session.add(prop)
        self.session.commit()
        self.session.refresh(prop)
        return to_property_response(prop, agency.name)

    def get_property(self, property_id: int) -> PropertyResponse:
        statement = (
            select(Property, Agency.name)
            .join(Agency, col(Property.agency_id) == col(Agency.id))
            .where(col(Property.id) == property_id)
        )
        row = self.session.exec(statement).first()
        if row is None:
            raise PropertyNotFoundError(property_id)
        prop, agency_name = row
        return to_property_response(prop, agency_name)

    def list_visits(self, property_id: int) -> list[VisitResponse]:
        prop = self.session.get(Property, property_id)
        if prop is None:
            raise PropertyNotFoundError(property_id)
        statement = (
            select(Visit)
            .where(col(Visit.property_id) == property_id)
            .order_by(col(Visit.scheduled_start).asc(), col(Visit.id).asc())
        )
        return [to_visit_response(v) for v in self.session.exec(statement).all()]

    def cancel_visit(self, property_id: int, visit_id: int) -> None:
        """Ejemplo resuelto: DELETE con 404 diferenciados y commit explícito."""
        prop = self.session.get(Property, property_id)
        if prop is None:
            raise PropertyNotFoundError(property_id)

        statement = select(Visit).where(
            col(Visit.id) == visit_id,
            col(Visit.property_id) == property_id,
        )
        visit = self.session.exec(statement).first()
        if visit is None:
            raise VisitNotFoundError(visit_id)

        self.session.delete(visit)
        self.session.commit()

    # =========================================================================
    # TALLER GUIADO: filtros dinámicos + agendamiento sin colisiones
    # =========================================================================

    def list_properties(
        self,
        city: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        min_bedrooms: int | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> PaginatedPropertiesResponse:
        """TALLER GUIADO, parte 1 (codelab, paso 4).

        1. Arma una lista `filters` solo con los parámetros presentes: ciudad (compara
           col(Property.city_key) con make_city_key(city)), precio mínimo y máximo,
           habitaciones mínimas y estado.
        2. Cuenta el total con select(func.count()).select_from(Property).where(*filters).
        3. Con offset = (page - 1) * size, consulta Property y Agency.name con un JOIN,
           el mismo .where(*filters), orden determinista por Property.id, offset y limit.
        4. Devuelve PaginatedPropertiesResponse; pages = ceil(total / size), o 0 si total es 0.
        Necesitarás importar `math` y `from sqlalchemy import func`.
        """
        raise NotImplementedError("Taller parte 1: implementa list_properties")

    def schedule_visit(self, property_id: int, payload: VisitCreate) -> VisitResponse:
        """TALLER GUIADO, parte 2 (codelab, paso 5).

        0. La primera línea ya viene: begin_write toma el candado de escritura antes de verificar.
        1. Si la propiedad no existe: PropertyNotFoundError.
           Si está vendida: PropertyUnavailableError.
        2. Busca en SQL una visita de la misma propiedad que se traslape con
           [payload.scheduled_start, payload.scheduled_end); si existe: VisitSlotConflictError.
        3. Crea la fila Visit, haz commit y refresh, y devuelve to_visit_response(visit).
        """
        begin_write(self.session)
        raise NotImplementedError("Taller parte 2: implementa schedule_visit")

    # =========================================================================
    # RETO AUTÓNOMO: reprogramar visitas (PATCH) y agenda de agencia. Contrato en README.md.
    # =========================================================================
