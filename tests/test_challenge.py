"""Tests oficiales PÚBLICOS del reto: reprogramar una visita con PATCH.

La nota del reto también incluye tests ocultos con más casos borde y datos distintos.
Pasar estos tests no garantiza pasar los ocultos: lee el contrato completo en README.md.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, text


def _url(property_id: int, visit_id: int) -> str:
    return f"/api/v1/properties/{property_id}/visits/{visit_id}"


def test_reschedule_moves_visit_and_persists(
    client: TestClient, make_property: Callable[..., Any], book_visit: Callable[..., Any]
) -> None:
    prop_id = make_property()["id"]
    visit = book_visit(
        prop_id, "2027-06-01T09:00:00Z", "2027-06-01T10:00:00Z", notes="Original"
    ).json()

    res = client.patch(
        _url(prop_id, visit["id"]),
        json={"scheduled_start": "2027-06-01T15:00:00Z", "scheduled_end": "2027-06-01T16:30:00Z"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == visit["id"]
    assert body["scheduled_start"] == "2027-06-01T15:00:00Z"
    assert body["scheduled_end"] == "2027-06-01T16:30:00Z"
    assert body["notes"] == "Original"
    assert body["visitor_email_masked"] == visit["visitor_email_masked"]

    listed = client.get(f"/api/v1/properties/{prop_id}/visits").json()
    assert [(v["id"], v["scheduled_start"]) for v in listed] == [
        (visit["id"], "2027-06-01T15:00:00Z")
    ]


def test_reschedule_excludes_itself_from_overlap(
    client: TestClient, make_property: Callable[..., Any], book_visit: Callable[..., Any]
) -> None:
    prop_id = make_property()["id"]
    visit = book_visit(prop_id, "2027-06-02T10:00:00Z", "2027-06-02T11:00:00Z").json()

    # La nueva ventana se cruza con la ventana anterior de la MISMA visita: debe permitirse.
    res = client.patch(_url(prop_id, visit["id"]), json={"scheduled_end": "2027-06-02T11:30:00Z"})
    assert res.status_code == 200
    assert res.json()["scheduled_start"] == "2027-06-02T10:00:00Z"
    assert res.json()["scheduled_end"] == "2027-06-02T11:30:00Z"


def test_reschedule_conflicts_with_other_visit_but_allows_contiguous(
    client: TestClient, make_property: Callable[..., Any], book_visit: Callable[..., Any]
) -> None:
    prop_id = make_property()["id"]
    morning = book_visit(prop_id, "2027-06-03T09:00:00Z", "2027-06-03T10:00:00Z").json()
    noon = book_visit(prop_id, "2027-06-03T12:00:00Z", "2027-06-03T13:00:00Z").json()

    clash = client.patch(
        _url(prop_id, noon["id"]),
        json={"scheduled_start": "2027-06-03T09:30:00Z", "scheduled_end": "2027-06-03T10:30:00Z"},
    )
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "VISIT_SLOT_CONFLICT"
    unchanged = client.get(f"/api/v1/properties/{prop_id}/visits").json()
    assert [v["scheduled_start"] for v in unchanged] == [
        "2027-06-03T09:00:00Z",
        "2027-06-03T12:00:00Z",
    ]

    contiguous = client.patch(
        _url(prop_id, noon["id"]),
        json={"scheduled_start": "2027-06-03T10:00:00Z", "scheduled_end": "2027-06-03T11:00:00Z"},
    )
    assert contiguous.status_code == 200
    assert morning["id"] != noon["id"]


def test_reschedule_normalizes_offsets_to_utc(
    client: TestClient, make_property: Callable[..., Any], book_visit: Callable[..., Any]
) -> None:
    prop_id = make_property()["id"]
    visit = book_visit(prop_id, "2027-06-04T14:00:00Z", "2027-06-04T15:00:00Z").json()

    # 10:00 en Guatemala (-06:00) son las 16:00 UTC; el fin existente (15:00 UTC) queda antes.
    res = client.patch(
        _url(prop_id, visit["id"]),
        json={
            "scheduled_start": "2027-06-04T10:00:00-06:00",
            "scheduled_end": "2027-06-04T11:00:00-06:00",
        },
    )
    assert res.status_code == 200
    assert res.json()["scheduled_start"] == "2027-06-04T16:00:00Z"
    assert res.json()["scheduled_end"] == "2027-06-04T17:00:00Z"


def test_reschedule_validates_body_and_combined_window(
    client: TestClient, make_property: Callable[..., Any], book_visit: Callable[..., Any]
) -> None:
    prop_id = make_property()["id"]
    visit = book_visit(prop_id, "2027-06-05T10:00:00Z", "2027-06-05T11:00:00Z").json()
    url = _url(prop_id, visit["id"])

    empty = client.patch(url, json={})
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "VALIDATION_ERROR"

    extra = client.patch(url, json={"notes": "ok", "visitor_email": "otro@ejemplo.example"})
    assert extra.status_code == 422
    assert extra.json()["error"]["code"] == "VALIDATION_ERROR"

    # Solo el inicio: combinado con el fin existente (11:00) queda fin <= inicio.
    inverted = client.patch(url, json={"scheduled_start": "2027-06-05T11:00:00Z"})
    assert inverted.status_code == 422
    assert inverted.json()["error"]["code"] == "INVALID_VISIT_WINDOW"


def test_reschedule_not_found_and_sold(
    client: TestClient,
    engine: Engine,
    make_property: Callable[..., Any],
    book_visit: Callable[..., Any],
) -> None:
    prop_id = make_property()["id"]
    other_id = make_property(title="Casa Vecina")["id"]
    visit = book_visit(prop_id, "2027-06-06T10:00:00Z", "2027-06-06T11:00:00Z").json()
    body = {"notes": "Cambio de notas"}

    no_property = client.patch(_url(9999, visit["id"]), json=body)
    assert no_property.status_code == 404
    assert no_property.json()["error"]["code"] == "PROPERTY_NOT_FOUND"

    no_visit = client.patch(_url(prop_id, 9999), json=body)
    assert no_visit.status_code == 404
    assert no_visit.json()["error"]["code"] == "VISIT_NOT_FOUND"

    wrong_property = client.patch(_url(other_id, visit["id"]), json=body)
    assert wrong_property.status_code == 404
    assert wrong_property.json()["error"]["code"] == "VISIT_NOT_FOUND"

    # La propiedad se vende después de agendar la visita (no hay endpoint para eso: SQL directo).
    with engine.begin() as conn:
        conn.execute(text("UPDATE property SET status = 'sold' WHERE id = :id"), {"id": prop_id})
    sold = client.patch(_url(prop_id, visit["id"]), json=body)
    assert sold.status_code == 409
    assert sold.json()["error"]["code"] == "PROPERTY_UNAVAILABLE"


# =============================================================================
# Parte 2 del reto: agenda de una agencia (consulta propia, paginada y acotada)
# =============================================================================


def _agenda(client: TestClient, agency_id: int, **params: Any) -> Any:
    return client.get(f"/api/v1/agencies/{agency_id}/visits", params=params)


def test_agency_agenda_lists_visits_of_all_its_properties(
    client: TestClient,
    make_agency: Callable[..., Any],
    make_property: Callable[..., Any],
    book_visit: Callable[..., Any],
) -> None:
    agency_id = make_agency("Agencia Norte")["id"]
    north = make_property(agency_id, title="Casa Norte")["id"]
    south = make_property(agency_id, title="Casa Sur")["id"]
    other = make_property(title="Casa Ajena")["id"]
    book_visit(north, "2027-10-05T10:00:00Z", "2027-10-05T11:00:00Z", email="luis@ejemplo.example")
    book_visit(south, "2027-10-05T09:00:00Z", "2027-10-05T09:30:00Z")
    book_visit(north, "2027-10-05T14:00:00Z", "2027-10-05T15:00:00Z")
    book_visit(other, "2027-10-05T10:00:00Z", "2027-10-05T11:00:00Z")

    day = {"from": "2027-10-05T00:00:00Z", "to": "2027-10-06T00:00:00Z"}
    res = _agenda(client, agency_id, **day)
    assert res.status_code == 200
    body = res.json()
    assert [(v["property_title"], v["scheduled_start"]) for v in body] == [
        ("Casa Sur", "2027-10-05T09:00:00Z"),
        ("Casa Norte", "2027-10-05T10:00:00Z"),
        ("Casa Norte", "2027-10-05T14:00:00Z"),
    ]
    assert body[1]["visitor_email_masked"] == "l***@ejemplo.example"
    assert "visitor_email" not in body[1]


def test_agency_agenda_validates_range_and_agency(
    client: TestClient, make_agency: Callable[..., Any]
) -> None:
    agency_id = make_agency("Agencia Validada")["id"]
    week = {"from": "2027-10-04T00:00:00Z", "to": "2027-10-11T00:00:00Z"}

    empty = _agenda(client, agency_id, **week)
    assert (empty.status_code, empty.json()) == (200, [])

    missing = _agenda(client, 9999, **week)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "AGENCY_NOT_FOUND"

    inverted = _agenda(client, agency_id, **{"from": week["to"], "to": week["from"]})
    assert inverted.status_code == 422
    assert inverted.json()["error"]["code"] == "INVALID_DATE_RANGE"

    no_from = _agenda(client, agency_id, to=week["to"])
    assert no_from.status_code == 422
    assert no_from.json()["error"]["code"] == "VALIDATION_ERROR"


def test_agency_agenda_runs_bounded_queries(
    client: TestClient,
    engine: Engine,
    make_agency: Callable[..., Any],
    make_property: Callable[..., Any],
    book_visit: Callable[..., Any],
) -> None:
    agency_id = make_agency("Agencia Grande")["id"]
    for i in range(4):
        prop_id = make_property(agency_id, title=f"Casa {i}")["id"]
        book_visit(prop_id, "2027-10-08T09:00:00Z", "2027-10-08T10:00:00Z")
        book_visit(prop_id, "2027-10-08T11:00:00Z", "2027-10-08T12:00:00Z")

    statements: list[str] = []

    def record(_conn: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        res = _agenda(
            client, agency_id, **{"from": "2027-10-08T00:00:00Z", "to": "2027-10-09T00:00:00Z"}
        )
    finally:
        event.remove(engine, "before_cursor_execute", record)

    assert res.status_code == 200
    assert len(res.json()) == 8
    assert len({v["property_title"] for v in res.json()}) == 4
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(selects) <= 2, f"Se ejecutaron {len(selects)} SELECT: la agenda no debe crecer con N"
