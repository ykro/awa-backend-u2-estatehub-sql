from __future__ import annotations

import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Path, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.exc import OperationalError
from sqlmodel import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import create_db_and_tables, get_session, seed_demo_data, seed_enabled
from app.repository import DomainError, EstateRepository
from app.schemas import (
    MAX_ID,
    MAX_PAGE,
    MAX_PRICE,
    AgencyCreate,
    AgencyResponse,
    ErrorEnvelope,
    PaginatedPropertiesResponse,
    PropertyCreate,
    PropertyResponse,
    PropertyStatus,
    VisitCreate,
    VisitResponse,
)
from app.ui import render_console_html
from app.validation_es import validation_details


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
    if seed_enabled():
        seed_demo_data()
    yield


app = FastAPI(
    title="EstateHub SQL API",
    version="2.0.0",
    description=(
        "API de gestión inmobiliaria con persistencia relacional (SQLModel), "
        "arquitectura en capas (Router -> Repository), filtros dinámicos paginados "
        "y detección de colisiones de horario. Sin autenticación: se protege en la Unidad 3."
    ),
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# Ids de ruta acotados al rango de un INTEGER de 32 bits: un número gigante responde 422, no 500.
IdPath = Annotated[int, Path(ge=1, le=MAX_ID, description="Identificador entero positivo")]


def get_repository(session: Session = Depends(get_session)) -> EstateRepository:
    """Inyecta un EstateRepository acoplado a la sesión de la petición actual."""
    return EstateRepository(session)


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(OperationalError)
async def database_busy_handler(_request: Request, exc: OperationalError) -> JSONResponse:
    """SQLite ocupado más allá del busy_timeout: 503 con Retry-After, sin detalles internos."""
    if "database is locked" in str(exc.orig):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "DATABASE_BUSY",
                    "message": "La base de datos está ocupada. Intenta de nuevo en un momento.",
                }
            },
            headers={"Retry-After": "1"},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {"code": "INTERNAL_ERROR", "message": "Error interno de la base de datos."}
        },
    )


# Errores que genera Starlette sin pasar por la app (ruta inexistente, método no permitido,
# cuerpo que no es UTF-8): en español y dentro del mismo sobre {"error": {...}}.
_HTTP_ERRORS = {
    404: ("NOT_FOUND", "La ruta solicitada no existe."),
    405: ("METHOD_NOT_ALLOWED", "Método HTTP no permitido en esta ruta."),
}


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 400:
        error = {"loc": ["body"], "msg": "El cuerpo no es JSON válido", "type": "json_invalid"}
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "La petición no cumple el contrato.",
                    "details": [error],
                }
            },
        )
    code, message = _HTTP_ERRORS.get(exc.status_code, ("HTTP_ERROR", "Error HTTP."))
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    details = validation_details(exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "La petición no cumple el contrato.",
                    "details": details,
                }
            }
        ),
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def interactive_console() -> HTMLResponse:
    nonce = secrets.token_urlsafe(16)
    csp = (
        "default-src 'none'; "
        f"script-src 'nonce-{nonce}'; "
        f"style-src 'nonce-{nonce}'; "
        "connect-src 'self'; img-src 'self' data:; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    return HTMLResponse(
        content=render_console_html(nonce),
        headers={"Content-Security-Policy": csp, "Cache-Control": "no-store"},
    )


@app.get("/health", summary="Estado del servicio", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "estatehub-sql-api"}


# =============================================================================
# ENDPOINTS DEMO (entregados funcionando)
# =============================================================================


@app.post(
    "/api/v1/agencies",
    response_model=AgencyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear agencia",
    tags=["agencies"],
)
def create_agency(
    payload: AgencyCreate,
    repo: EstateRepository = Depends(get_repository),
) -> AgencyResponse:
    return repo.create_agency(payload)


@app.get(
    "/api/v1/agencies",
    response_model=list[AgencyResponse],
    summary="Listar agencias",
    tags=["agencies"],
)
def list_agencies(repo: EstateRepository = Depends(get_repository)) -> list[AgencyResponse]:
    return repo.list_agencies()


@app.post(
    "/api/v1/properties",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorEnvelope}},
    summary="Crear propiedad",
    tags=["properties"],
)
def create_property(
    payload: PropertyCreate,
    repo: EstateRepository = Depends(get_repository),
) -> PropertyResponse:
    return repo.create_property(payload)


@app.get(
    "/api/v1/properties/{property_id}",
    response_model=PropertyResponse,
    responses={404: {"model": ErrorEnvelope}},
    summary="Consultar propiedad",
    tags=["properties"],
)
def get_property(
    property_id: IdPath,
    repo: EstateRepository = Depends(get_repository),
) -> PropertyResponse:
    return repo.get_property(property_id)


@app.get(
    "/api/v1/properties/{property_id}/visits",
    response_model=list[VisitResponse],
    responses={404: {"model": ErrorEnvelope}},
    summary="Listar visitas de una propiedad",
    tags=["visits"],
)
def list_property_visits(
    property_id: IdPath,
    repo: EstateRepository = Depends(get_repository),
) -> list[VisitResponse]:
    return repo.list_visits(property_id)


@app.delete(
    "/api/v1/properties/{property_id}/visits/{visit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorEnvelope}},
    summary="Cancelar visita",
    tags=["visits"],
)
def cancel_property_visit(
    property_id: IdPath,
    visit_id: IdPath,
    repo: EstateRepository = Depends(get_repository),
) -> Response:
    repo.cancel_visit(property_id, visit_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# TALLER GUIADO: filtros paginados + agendamiento sin colisión
# =============================================================================


@app.get(
    "/api/v1/properties",
    response_model=PaginatedPropertiesResponse,
    summary="Buscar propiedades con filtros y paginación",
    tags=["properties"],
)
def list_properties(
    city: str | None = Query(
        default=None, max_length=80, description="Ciudad, sin distinguir mayúsculas"
    ),
    min_price: int | None = Query(
        default=None, ge=0, le=MAX_PRICE, description="Precio mínimo en USD"
    ),
    max_price: int | None = Query(
        default=None, ge=0, le=MAX_PRICE, description="Precio máximo en USD"
    ),
    min_bedrooms: int | None = Query(default=None, ge=1, le=20, description="Habitaciones mínimas"),
    status_filter: PropertyStatus | None = Query(
        default=None, alias="status", description="Estado del inmueble"
    ),
    page: int = Query(default=1, ge=1, le=MAX_PAGE, description="Número de página (desde 1)"),
    size: int = Query(default=10, ge=1, le=50, description="Tamaño de página (máximo 50)"),
    repo: EstateRepository = Depends(get_repository),
) -> PaginatedPropertiesResponse:
    return repo.list_properties(
        city=city,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        status=status_filter,
        page=page,
        size=size,
    )


@app.post(
    "/api/v1/properties/{property_id}/visits",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}},
    summary="Agendar visita",
    tags=["visits"],
)
def schedule_property_visit(
    property_id: IdPath,
    payload: VisitCreate,
    repo: EstateRepository = Depends(get_repository),
) -> VisitResponse:
    return repo.schedule_visit(property_id, payload)


# =============================================================================
# RETO AUTÓNOMO: PATCH de visitas y agenda de agencia. El contrato está en README.md.
# Aquí van tus rutas; la lógica y las consultas, en el repositorio.
# =============================================================================
