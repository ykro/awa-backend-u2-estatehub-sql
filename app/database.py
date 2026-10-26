from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime

from sqlalchemy import Engine, event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Agency, Property, Visit, make_city_key

DATABASE_URL = os.getenv("ESTATEHUB_DATABASE_URL", "sqlite:///./estatehub.db")


WRITE_LOCK_OPTION = "sqlite_write_lock"
SQLITE_BUSY_TIMEOUT_SECONDS = 10.0


def build_engine(url: str, busy_timeout: float = SQLITE_BUSY_TIMEOUT_SECONDS) -> Engine:
    """Crea el engine.

    - SQLite en memoria necesita StaticPool para no perder las tablas.
    - pysqlite no abre transacción antes de un SELECT. Aquí cada transacción empieza con un
      BEGIN explícito: DEFERRED (lecturas concurrentes, sin candado) salvo que la operación
      pida el candado de escritura con begin_write(); entonces es BEGIN IMMEDIATE.
    - busy_timeout: cuánto espera una conexión por el candado antes de fallar con
      "database is locked" (la API lo traduce a 503 con Retry-After).
    """
    if not url.startswith("sqlite"):
        return create_engine(url, echo=False)
    connect_args = {"check_same_thread": False, "timeout": busy_timeout}
    if url in ("sqlite://", "sqlite:///:memory:"):
        new_engine = create_engine(url, echo=False, connect_args=connect_args, poolclass=StaticPool)
    else:
        new_engine = create_engine(url, echo=False, connect_args=connect_args)

    @event.listens_for(new_engine, "connect")
    def _disable_pysqlite_transactions(dbapi_connection, _record) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(new_engine, "begin")
    def _begin(connection) -> None:
        wants_lock = connection.get_execution_options().get(WRITE_LOCK_OPTION, False)
        connection.exec_driver_sql("BEGIN IMMEDIATE" if wants_lock else "BEGIN")

    return new_engine


def begin_write(session: Session) -> None:
    """Abre la transacción de la sesión tomando el candado de escritura (SQLite: BEGIN IMMEDIATE).

    Debe ser lo primero que hace una operación que verifica y luego escribe: así ninguna otra
    escritura se intercala entre la verificación y la escritura. Las lecturas no lo usan.
    En PostgreSQL esta opción no hace nada (allí se usa EXCLUDE o SELECT ... FOR UPDATE).
    """
    session.connection(execution_options={WRITE_LOCK_OPTION: True})


engine = build_engine(DATABASE_URL)


def create_db_and_tables() -> None:
    """Crea las tablas relacionales en la base de datos activa."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session]:
    """Abre una sesión por petición HTTP y la cierra al terminar, incluso si hay error."""
    with Session(engine) as session:
        yield session


def seed_enabled() -> bool:
    """El sembrado de datos de demo solo ocurre si SEED_DEMO_DATA=true."""
    return os.getenv("SEED_DEMO_DATA", "false").strip().lower() == "true"


def seed_demo_data() -> None:
    """Puebla datos ficticios para la consola web si la base de datos está vacía."""
    with Session(engine) as session:
        existing_agency = session.exec(select(Agency)).first()
        if existing_agency is not None:
            return

        a1 = Agency(
            name="Altamira Patrimonial",
            email="contacto@altamira.example",
            phone="+502 0000-0001",
        )
        a2 = Agency(
            name="Veranda Real Estate",
            email="ventas@veranda.example",
            phone="+502 0000-0002",
        )
        session.add(a1)
        session.add(a2)
        session.commit()
        session.refresh(a1)
        session.refresh(a2)

        p1 = Property(
            agency_id=a1.id,
            title="Loft Colonial Santa Catalina",
            city="Antigua",
            city_key=make_city_key("Antigua"),
            price=285000,
            bedrooms=2,
            status="available",
        )
        p2 = Property(
            agency_id=a1.id,
            title="Residencia Bosque de Cayalá",
            city="Guatemala",
            city_key=make_city_key("Guatemala"),
            price=460000,
            bedrooms=4,
            status="available",
        )
        p3 = Property(
            agency_id=a2.id,
            title="Penthouse Vista Volcán de Agua",
            city="Antigua",
            city_key=make_city_key("Antigua"),
            price=390000,
            bedrooms=3,
            status="available",
        )
        p4 = Property(
            agency_id=a2.id,
            title="Villa Lago Panajachel",
            city="Atitlán",
            city_key=make_city_key("Atitlán"),
            price=520000,
            bedrooms=4,
            status="sold",
        )
        session.add_all([p1, p2, p3, p4])
        session.commit()
        session.refresh(p1)

        v1 = Visit(
            property_id=p1.id,
            visitor_name="Valeria Méndez",
            visitor_email="valeria@ejemplo.example",
            scheduled_start=datetime(2027, 5, 15, 10, 0, 0, tzinfo=UTC),
            scheduled_end=datetime(2027, 5, 15, 11, 0, 0, tzinfo=UTC),
            notes="Interesada en financiamiento bancario y terraza.",
        )
        session.add(v1)
        session.commit()
