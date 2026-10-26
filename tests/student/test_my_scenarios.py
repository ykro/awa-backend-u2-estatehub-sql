"""Tus tests propios.

Tus tests propios suman si pasan contra la solución de referencia y detectan mutantes que
la suite pública no detecta (errores sembrados en el reto). Reescribir un
test público no suma.

Reglas:
- Usa los fixtures de tests/conftest.py (client, engine, make_agency, make_property, book_visit).
- No crees conftest.py en esta carpeta.
- Cada test debe describir un escenario distinto a los tests públicos, con datos propios
  y aserciones concretas sobre códigos HTTP y cuerpos JSON.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_student_scenario_1(client: TestClient) -> None:
    """Escribe aquí un escenario del reto (por ejemplo, un borde de la ventana o del traslape)."""
    pytest.fail("Pendiente: escribe tu primer test propio")


def test_student_scenario_2(client: TestClient) -> None:
    """Escribe aquí un segundo escenario, distinto del primero."""
    pytest.fail("Pendiente: escribe tu segundo test propio")
