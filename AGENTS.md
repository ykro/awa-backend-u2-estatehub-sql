# AGENTS.md: reglas para asistentes de IA (EstateHub SQL)

Este archivo describe las invariantes que cualquier asistente de IA (Copilot, Cursor, Claude Code, Antigravity, Gemini) y cualquier persona deben respetar al modificar este proyecto. Es una **base**: como parte de la entrega se amplía con al menos una regla propia (ver la pregunta 7 de `ARCHITECTURE_DECISIONS.md`).

## 1. Capas

- `app/main.py` solo declara rutas, códigos HTTP y parámetros. Nunca importa `select`, `func` ni las tablas de `app/models.py`.
- Toda consulta SQL y toda regla de dominio vive en `EstateRepository` (`app/repository.py`), inyectado con `Depends(get_repository)`.
- La sesión se obtiene por petición con `get_session()` (generador con `yield`). Prohibido crear una `Session` global.

## 2. Tablas y contratos

- Las clases con `table=True` viven en `app/models.py`; los DTO de entrada y salida, en `app/schemas.py`.
- Todo DTO de entrada usa `ConfigDict(extra="forbid")`.
- Las respuestas públicas nunca exponen el correo completo del visitante (`visitor_email_masked`).

## 3. Consultas

- Listados con datos relacionados usan un `JOIN` explícito, nunca consultas dentro de un `for` (N+1). Un test lo vigila.
- La paginación usa `offset = (page - 1) * size`, `limit(size)` y un `ORDER BY` determinista.
- El filtro por ciudad compara `Property.city_key` (normalizada con `make_city_key`, casefold) porque `lower()` de SQLite solo baja ASCII.
- Las operaciones "verificar y luego escribir" empiezan con `begin_write(self.session)` (`BEGIN IMMEDIATE` en SQLite) y no hacen `commit` entre la verificación y la escritura. Las lecturas no toman el candado.
- Ids, `page` y montos llevan límites (`le=`): una entrada extrema responde 422, nunca 500.
- Ningún SQL se arma concatenando texto: se usan expresiones de SQLModel/SQLAlchemy (consultas parametrizadas).

## 4. Fechas e intervalos

- Toda fecha que llega del cliente se normaliza a UTC en la frontera (DTO): una fecha sin zona horaria se interpreta como UTC y una con zona se convierte con `astimezone`, nunca con `replace`. Las columnas `UTCDateTime` de SQLModel rechazan fechas sin zona.
- Las visitas son intervalos semiabiertos `[inicio, fin)`: dos visitas se traslapan si `inicio_A < fin_B` y `fin_A > inicio_B`. Tocar el borde no es traslape.

## 5. Tests y calidad

- Los tests oficiales (`tests/conftest.py`, `tests/test_demo.py`, `tests/test_workshop.py`, `tests/test_challenge.py`) y `.github/workflows/ci.yml` no se modifican.
- Los tests propios viven en `tests/student/` y no usan `conftest.py` propio.
- Antes de cada commit: `uv run ruff check .`, `uv run ruff format --check .` y `uv run pytest -v`.
- El código de `app/` nunca consulta si se está ejecutando bajo pytest ni lee archivos de `tests/`.

## 6. Reglas propias del equipo

<!-- Agrega aquí al menos una regla tuya, concreta y verificable. -->
