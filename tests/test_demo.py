"""Tests oficiales de la demo: pasan desde el starter."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_demo_agencies_and_error_contract(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agencies",
        json={
            "name": "  Veranda Real Estate  ",
            "email": "VENTAS@VERANDA.EXAMPLE",
            "phone": "+502 0000-0002",
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Veranda Real Estate"
    assert created["email"] == "ventas@veranda.example"

    listed = client.get("/api/v1/agencies")
    assert listed.status_code == 200
    assert [a["id"] for a in listed.json()] == [created["id"]]

    # Un campo extra se rechaza con el sobre de error uniforme, sin reflejar la entrada.
    invalid = client.post(
        "/api/v1/agencies",
        json={"name": "X", "email": "sin-arroba", "phone": "1", "id": 99},
    )
    assert invalid.status_code == 422
    error = invalid.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]
    for detail in error["details"]:
        assert set(detail) == {"loc", "msg", "type"}
    messages = {detail["msg"] for detail in error["details"]}
    assert "Campo no permitido" in messages
    assert "Debe tener al menos 2 caracteres" in messages

    # Errores que genera el framework (ruta inexistente, método, cuerpo no UTF-8): mismo sobre.
    missing = client.get("/api/v1/no-existe")
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {"code": "NOT_FOUND", "message": "La ruta solicitada no existe."}
    }

    wrong_method = client.put("/health")
    assert wrong_method.status_code == 405
    assert wrong_method.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in wrong_method.headers["allow"]

    not_utf8 = client.post(
        "/api/v1/agencies",
        content=b"\xff\xfe",
        headers={"Content-Type": "application/json"},
    )
    assert not_utf8.status_code == 422
    assert not_utf8.json()["error"]["code"] == "VALIDATION_ERROR"


def test_demo_property_fk_extreme_inputs_and_headers(client: TestClient) -> None:
    agency = client.post(
        "/api/v1/agencies",
        json={
            "name": "Altamira Patrimonial",
            "email": "contacto@altamira.example",
            "phone": "+502 0000-0001",
        },
    ).json()
    created = client.post(
        "/api/v1/properties",
        json={
            "agency_id": agency["id"],
            "title": "Loft Colonial Santa Catalina",
            "city": "Antigua",
            "price": 285000,
            "bedrooms": 2,
        },
    )
    assert created.status_code == 201
    assert created.json()["agency_name"] == "Altamira Patrimonial"

    missing_fk = client.post(
        "/api/v1/properties",
        json={
            "agency_id": 999,
            "title": "Casa Fantasma",
            "city": "Guatemala",
            "price": 150000,
            "bedrooms": 2,
        },
    )
    assert missing_fk.status_code == 404
    assert missing_fk.json()["error"]["code"] == "AGENCY_NOT_FOUND"

    # Entradas extremas: 422 con el sobre de error, nunca 500.
    huge = 10**20
    extreme_requests = [
        client.get(f"/api/v1/properties/{huge}"),
        client.get("/api/v1/properties", params={"page": 999999999999999999}),
        client.get("/api/v1/properties", params={"min_price": 99999999999999999999}),
        client.post(
            "/api/v1/properties",
            json={"agency_id": huge, "title": "Casa", "city": "Xela", "price": 1, "bedrooms": 1},
        ),
        client.post(
            f"/api/v1/properties/{created.json()['id']}/visits",
            json={
                "visitor_name": "Ana",
                "visitor_email": "ana@ejemplo.example",
                "scheduled_start": "0001-01-01T00:00:00+05:00",
                "scheduled_end": "0001-01-01T01:00:00+05:00",
            },
        ),
    ]
    for res in extreme_requests:
        assert res.status_code == 422, res.text
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"

    console = client.get("/")
    assert console.status_code == 200
    csp = console.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "script-src 'nonce-" in csp
    assert "frame-ancestors 'none'" in csp
    assert console.headers["x-content-type-options"] == "nosniff"
    assert console.headers["referrer-policy"] == "no-referrer"
    assert "cdn.tailwindcss.com" not in console.text
