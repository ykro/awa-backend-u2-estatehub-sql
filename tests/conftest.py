"""Fixtures oficiales y herméticos de la Unidad 2.

- Cada test recibe una base SQLite en memoria nueva (StaticPool): no se crea ningún archivo .db.
- No se siembran datos de demo: cada test crea exactamente lo que necesita.
- Este archivo es oficial: el calificador usa siempre la versión oficial.
"""

from __future__ import annotations

import os

# Antes de importar la app: el engine global también queda en memoria y sin sembrado.
os.environ["ESTATEHUB_DATABASE_URL"] = "sqlite://"
os.environ["SEED_DEMO_DATA"] = "false"

from collections.abc import Callable, Generator  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.database import build_engine, get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def engine() -> Generator[Engine]:
    """Engine SQLite en memoria, aislado por test."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


def _client_for(engine: Engine) -> Generator[TestClient]:
    def override_get_session() -> Generator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def client(engine: Engine) -> Generator[TestClient]:
    """TestClient cuya dependencia get_session apunta al engine en memoria del test."""
    yield from _client_for(engine)


@pytest.fixture()
def file_engine(tmp_path: Path) -> Generator[Engine]:
    """Engine de la app (build_engine) sobre un archivo temporal fuera del repo.

    Solo lo usan los tests de concurrencia: varias conexiones reales a la misma base.
    """
    test_engine = build_engine(f"sqlite:///{tmp_path / 'concurrencia.db'}")
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def file_client(file_engine: Engine) -> Generator[TestClient]:
    """TestClient sobre file_engine."""
    yield from _client_for(file_engine)


@pytest.fixture()
def make_agency(client: TestClient) -> Callable[..., dict[str, Any]]:
    """Crea una agencia por HTTP y devuelve el JSON de respuesta."""
    counter = {"n": 0}

    def _make(name: str | None = None) -> dict[str, Any]:
        counter["n"] += 1
        n = counter["n"]
        res = client.post(
            "/api/v1/agencies",
            json={
                "name": name or f"Agencia {n}",
                "email": f"contacto{n}@agencia.example",
                "phone": f"+502 0000-{n:04d}",
            },
        )
        assert res.status_code == 201, res.text
        return res.json()

    return _make


@pytest.fixture()
def make_property(
    client: TestClient, make_agency: Callable[..., dict[str, Any]]
) -> Callable[..., dict[str, Any]]:
    """Crea una propiedad por HTTP (y su agencia si no se indica) y devuelve el JSON."""

    def _make(
        agency_id: int | None = None,
        title: str = "Loft Colonial Santa Catalina",
        city: str = "Antigua",
        price: int = 285000,
        bedrooms: int = 2,
        status: str = "available",
    ) -> dict[str, Any]:
        if agency_id is None:
            agency_id = make_agency()["id"]
        res = client.post(
            "/api/v1/properties",
            json={
                "agency_id": agency_id,
                "title": title,
                "city": city,
                "price": price,
                "bedrooms": bedrooms,
                "status": status,
            },
        )
        assert res.status_code == 201, res.text
        return res.json()

    return _make


@pytest.fixture()
def book_visit(client: TestClient) -> Callable[..., Any]:
    """Agenda una visita por HTTP y devuelve la respuesta completa (no valida el status)."""

    def _book(
        property_id: int,
        start: str,
        end: str,
        name: str = "Valeria Méndez",
        email: str = "valeria@ejemplo.example",
        notes: str = "",
    ) -> Any:
        return client.post(
            f"/api/v1/properties/{property_id}/visits",
            json={
                "visitor_name": name,
                "visitor_email": email,
                "scheduled_start": start,
                "scheduled_end": end,
                "notes": notes,
            },
        )

    return _book
