"""Tests oficiales del taller guiado: list_properties y schedule_visit (rojo en el starter)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, create_engine

from app.database import build_engine, get_session
from app.main import app


def test_list_properties_filters_joins_and_paginates(
    client: TestClient, make_agency: Callable[..., Any], make_property: Callable[..., Any]
) -> None:
    agency_id = make_agency("Altamira Patrimonial")["id"]
    make_property(agency_id, title="Estudio Centro", city="Antigua", price=180000, bedrooms=1)
    make_property(agency_id, title="Loft Santa Catalina", city="Antigua", price=285000, bedrooms=2)
    make_property(agency_id, title="Penthouse Volcán", city="Antigua", price=390000, bedrooms=3)
    make_property(agency_id, title="Villa Cayalá", city="Guatemala", price=460000, bedrooms=4)

    params = {"city": "  ANTIGUA ", "min_price": 250000, "max_price": 420000, "min_bedrooms": 2}
    first = client.get("/api/v1/properties", params={**params, "page": 1, "size": 1})
    assert first.status_code == 200
    body = first.json()
    assert (body["total"], body["page"], body["size"], body["pages"]) == (2, 1, 1, 2)
    assert [p["title"] for p in body["items"]] == ["Loft Santa Catalina"]
    assert body["items"][0]["agency_name"] == "Altamira Patrimonial"

    second = client.get("/api/v1/properties", params={**params, "page": 2, "size": 1}).json()
    assert [p["title"] for p in second["items"]] == ["Penthouse Volcán"]


def test_list_properties_city_filter_ignores_case_beyond_ascii(
    client: TestClient, make_property: Callable[..., Any]
) -> None:
    make_property(title="Casa Andaluza", city="Écija")
    make_property(title="Casa Chapina", city="Guatemala")

    for query in ("écija", "ÉCIJA", "  Écija "):
        body = client.get("/api/v1/properties", params={"city": query}).json()
        assert [p["title"] for p in body["items"]] == ["Casa Andaluza"], query


def test_list_properties_without_filters_and_by_status(
    client: TestClient, make_property: Callable[..., Any]
) -> None:
    make_property(title="Casa Uno", status="available")
    make_property(title="Casa Dos", status="sold")
    make_property(title="Casa Tres", status="reserved")

    everything = client.get("/api/v1/properties").json()
    assert everything["total"] == 3
    assert [p["title"] for p in everything["items"]] == ["Casa Uno", "Casa Dos", "Casa Tres"]

    sold = client.get("/api/v1/properties", params={"status": "sold"}).json()
    assert sold["total"] == 1
    assert sold["items"][0]["title"] == "Casa Dos"

    bad_size = client.get("/api/v1/properties", params={"size": 51})
    assert bad_size.status_code == 422


def test_list_properties_empty_and_out_of_range_pages(
    client: TestClient, make_property: Callable[..., Any]
) -> None:
    empty = client.get("/api/v1/properties", params={"city": "Cobán"}).json()
    assert (empty["total"], empty["pages"], empty["items"]) == (0, 0, [])

    for i in range(3):
        make_property(title=f"Casa {i}", city="Xela")
    beyond = client.get("/api/v1/properties", params={"page": 5, "size": 2}).json()
    assert beyond["total"] == 3
    assert beyond["pages"] == 2
    assert beyond["items"] == []


def test_list_properties_runs_bounded_queries(
    client: TestClient,
    engine: Engine,
    make_agency: Callable[..., Any],
    make_property: Callable[..., Any],
) -> None:
    """Vigila el problema N+1: listar con el nombre de la agencia no puede crecer con N."""
    for i in range(6):
        agency_id = make_agency(f"Agencia Distinta {i}")["id"]
        make_property(agency_id, title=f"Propiedad {i}")

    statements: list[str] = []

    def record(_conn: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        response = client.get("/api/v1/properties", params={"size": 10})
    finally:
        event.remove(engine, "before_cursor_execute", record)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 6
    assert {p["agency_name"] for p in items} == {f"Agencia Distinta {i}" for i in range(6)}
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(selects) <= 3, f"Se ejecutaron {len(selects)} SELECT: revisa el problema N+1"


def test_schedule_visit_persists_and_masks_email(
    client: TestClient, make_property: Callable[..., Any], book_visit: Callable[..., Any]
) -> None:
    prop_id = make_property()["id"]
    created = book_visit(
        prop_id,
        "2027-05-15T10:00:00Z",
        "2027-05-15T11:00:00Z",
        email="valeria.mendez@ejemplo.example",
        notes="Primera visita técnica",
    )
    assert created.status_code == 201
    visit = created.json()
    assert visit["property_id"] == prop_id
    assert visit["visitor_email_masked"] == "v***@ejemplo.example"
    assert "visitor_email" not in visit
    assert "valeria.mendez" not in created.text

    listed = client.get(f"/api/v1/properties/{prop_id}/visits")
    assert listed.status_code == 200
    assert [v["id"] for v in listed.json()] == [visit["id"]]
    assert listed.json()[0]["scheduled_start"] == "2027-05-15T10:00:00Z"


def test_schedule_visit_rejects_overlap_and_allows_contiguous(
    make_property: Callable[..., Any], book_visit: Callable[..., Any]
) -> None:
    prop_id = make_property()["id"]
    other_prop_id = make_property(title="Casa Vecina")["id"]
    assert book_visit(prop_id, "2027-05-15T10:00:00Z", "2027-05-15T11:00:00Z").status_code == 201

    overlap = book_visit(prop_id, "2027-05-15T10:30:00Z", "2027-05-15T11:30:00Z")
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "VISIT_SLOT_CONFLICT"

    # [11:00, 12:00) solo toca el borde de [10:00, 11:00): no hay traslape.
    assert book_visit(prop_id, "2027-05-15T11:00:00Z", "2027-05-15T12:00:00Z").status_code == 201
    # La misma hora en otra propiedad no choca.
    assert (
        book_visit(other_prop_id, "2027-05-15T10:00:00Z", "2027-05-15T11:00:00Z").status_code == 201
    )


def test_schedule_visit_rejects_sold_and_missing_property(
    make_property: Callable[..., Any], book_visit: Callable[..., Any]
) -> None:
    sold_id = make_property(status="sold")["id"]
    sold = book_visit(sold_id, "2027-05-16T09:00:00Z", "2027-05-16T10:00:00Z")
    assert sold.status_code == 409
    assert sold.json()["error"]["code"] == "PROPERTY_UNAVAILABLE"

    missing = book_visit(9999, "2027-05-16T09:00:00Z", "2027-05-16T10:00:00Z")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "PROPERTY_NOT_FOUND"


def test_cancel_visit_frees_slot(
    client: TestClient, make_property: Callable[..., Any], book_visit: Callable[..., Any]
) -> None:
    prop_id = make_property()["id"]
    visit_id = book_visit(prop_id, "2027-05-15T10:00:00Z", "2027-05-15T11:00:00Z").json()["id"]

    deleted = client.delete(f"/api/v1/properties/{prop_id}/visits/{visit_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""

    again = client.delete(f"/api/v1/properties/{prop_id}/visits/{visit_id}")
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "VISIT_NOT_FOUND"

    assert book_visit(prop_id, "2027-05-15T10:00:00Z", "2027-05-15T11:00:00Z").status_code == 201


def test_schedule_visit_is_atomic_under_concurrency(
    file_client: TestClient, file_engine: Engine
) -> None:
    """10 reservas simultáneas al mismo horario: exactamente una gana, las demás reciben 409."""
    agency = file_client.post(
        "/api/v1/agencies",
        json={
            "name": "Agencia Concurrente",
            "email": "c@agencia.example",
            "phone": "+502 0000-0099",
        },
    ).json()
    prop = file_client.post(
        "/api/v1/properties",
        json={
            "agency_id": agency["id"],
            "title": "Casa Disputada",
            "city": "Xela",
            "price": 1000,
            "bedrooms": 2,
        },
    ).json()

    def widen_race_window(_conn: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        # Ensancha la ventana entre "verificar traslape" e "insertar": la carrera se vuelve visible.
        if statement.lstrip().upper().startswith("SELECT") and "visit" in statement.lower():
            time.sleep(0.05)

    event.listen(file_engine, "after_cursor_execute", widen_race_window)
    barrier = threading.Barrier(10)
    statuses: list[int] = []

    def book(i: int) -> None:
        barrier.wait()
        res = file_client.post(
            f"/api/v1/properties/{prop['id']}/visits",
            json={
                "visitor_name": f"Visitante {i}",
                "visitor_email": f"v{i}@ejemplo.example",
                "scheduled_start": "2027-09-01T10:00:00Z",
                "scheduled_end": "2027-09-01T11:00:00Z",
            },
        )
        statuses.append(res.status_code)

    threads = [threading.Thread(target=book, args=(i,)) for i in range(10)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        event.remove(file_engine, "after_cursor_execute", widen_race_window)

    assert sorted(statuses) == [201] + [409] * 9
    assert len(file_client.get(f"/api/v1/properties/{prop['id']}/visits").json()) == 1


def test_concurrent_reads_and_writes_never_fail(
    file_client: TestClient, file_engine: Engine
) -> None:
    """Lecturas y reservas simultáneas: las lecturas no toman candado y nadie recibe un 500."""
    agency = file_client.post(
        "/api/v1/agencies",
        json={"name": "Agencia Lectora", "email": "l@agencia.example", "phone": "+502 0000-0098"},
    ).json()
    prop = file_client.post(
        "/api/v1/properties",
        json={
            "agency_id": agency["id"],
            "title": "Casa Consultada",
            "city": "Xela",
            "price": 1000,
            "bedrooms": 2,
        },
    ).json()
    barrier = threading.Barrier(30)
    statuses: list[int] = []

    def worker(i: int) -> None:
        barrier.wait()
        if i % 6 == 0:
            res = file_client.post(
                f"/api/v1/properties/{prop['id']}/visits",
                json={
                    "visitor_name": f"Visitante {i}",
                    "visitor_email": f"r{i}@ejemplo.example",
                    "scheduled_start": f"2027-09-03T{8 + i // 6:02d}:00:00Z",
                    "scheduled_end": f"2027-09-03T{8 + i // 6:02d}:30:00Z",
                },
            )
        else:
            res = file_client.get("/api/v1/properties", params={"city": "xela"})
        statuses.append(res.status_code)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(statuses) == 30
    assert all(code in (200, 201) for code in statuses), statuses


def test_locked_database_answers_503_with_retry_after(tmp_path: Path) -> None:
    """Si el candado no se libera a tiempo, la API responde 503 DATABASE_BUSY, no 500."""
    db_url = f"sqlite:///{tmp_path / 'ocupada.db'}"
    impatient = build_engine(db_url, busy_timeout=0.2)
    SQLModel.metadata.create_all(impatient)
    holder = create_engine(db_url)  # engine simple: solo sostiene el candado

    def override_get_session() -> Generator[Session]:
        with Session(impatient) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as busy_client, holder.connect() as conn:
            conn.exec_driver_sql("BEGIN EXCLUSIVE")
            res = busy_client.get("/api/v1/properties")
            conn.exec_driver_sql("ROLLBACK")
    finally:
        app.dependency_overrides.clear()
        impatient.dispose()
        holder.dispose()

    assert res.status_code == 503
    assert res.headers["retry-after"] == "1"
    assert res.json()["error"]["code"] == "DATABASE_BUSY"
