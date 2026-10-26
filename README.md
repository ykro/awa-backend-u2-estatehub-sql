# EstateHub SQL API: proyecto del estudiante (Unidad 2)

API de gestión inmobiliaria con persistencia relacional en **SQLModel**, arquitectura en capas
(`main.py` -> `EstateRepository` -> `Session`), filtros paginados y agenda de visitas sin colisiones.

Trabaja en la raíz de tu repositorio y sigue el codelab publicado en el material de la unidad. El reto está pensado para 2 a 3 horas, más 45 minutos de tests propios y 45 de documentos.

## Puesta en marcha

```bash
uv sync
uv run pytest -v                 # 2 en verde (demo) y el resto en rojo
uv run ruff check . && uv run ruff format --check .
SEED_DEMO_DATA=true uv run uvicorn app.main:app --reload --port 8000
```

- Consola web: `http://127.0.0.1:8000/` (tres pestañas, modo claro).
- Contrato OpenAPI: `http://127.0.0.1:8000/docs`.
- Los datos de demo solo se siembran con `SEED_DEMO_DATA=true`. Sin esa variable la base empieza vacía.
- Por defecto la base es el archivo `estatehub.db` (ignorado por git). Con `ESTATEHUB_DATABASE_URL=sqlite://` vive solo en memoria.
- Para probar algo suelto en Python usa `uv run python`.

## Estructura de tests

| Archivo | Qué cubre | Estado en el starter |
| :--- | :--- | :--- |
| `tests/conftest.py` | Fixtures oficiales: SQLite en memoria con `StaticPool`, sin sembrado; `file_engine` para los tests de concurrencia (archivo temporal fuera del repo) | No se modifica |
| `tests/test_demo.py` | Agencias, llave foránea, entradas extremas (422), mensajes en español y cabeceras de seguridad | 2 en verde |
| `tests/test_workshop.py` | Taller: `list_properties` (filtros, ciudad con tildes, JOIN, paginación, N+1), `schedule_visit` (409, reservas simultáneas) y lecturas concurrentes sin errores (503 si la base sigue ocupada) | 12 en rojo |
| `tests/test_challenge.py` | Reto, tests **públicos**: `PATCH` (6) y agenda de agencia (3) | 9 en rojo |
| `tests/student/test_my_scenarios.py` | **Tus** tests (2 plantillas con `pytest.fail`) | 2 en rojo |

No modifiques los tests oficiales ni el workflow: el calificador usa siempre su propia copia y reporta cualquier cambio.

## Reglas comunes de la API

- Ids de ruta y de cuerpo: enteros de 1 a 2147483647. `page`: de 1 a 10000. `size`: de 1 a 50. Precios: hasta 50000000. Fuera de rango: **422**, nunca 500.
- Toda fecha se expresa en UTC. Una fecha con zona horaria se convierte (`2027-06-04T10:00:00-06:00` son las `16:00:00Z`); una sin zona se interpreta como UTC; una fecha que no cabe al convertirla a UTC (por ejemplo `0001-01-01T00:00:00+05:00`) es un 422. En una query string, el `+` de la zona horaria se escribe `%2B`.
- Los errores usan el sobre `{"error": {"code": ..., "message": ...}}`. Los de validación (`VALIDATION_ERROR`) traen además `details` con `loc`, `msg` (en español, de `app/validation_es.py`) y `type`.
- **Concurrencia.** Las lecturas no toman candados. Una operación que verifica y luego escribe empieza con `begin_write(self.session)` (de `app/database.py`): en SQLite abre la transacción con `BEGIN IMMEDIATE`, así ninguna otra escritura se intercala entre la verificación y la escritura. Si la base sigue ocupada después de 10 segundos de espera, la API responde **503** `DATABASE_BUSY` con `Retry-After`. `tests/test_workshop.py` lo comprueba con hilos.

## Reto autónomo (2 partes)

`cancel_visit` (DELETE) viene resuelto como ejemplo en `app/repository.py`. El reto complementa el taller: en el taller **creas** visitas y listas propiedades con una consulta guiada; aquí **modificas** una visita existente y diseñas **tu propia consulta** relacional.

Dónde va cada pieza (la estructura interna es tuya, el contrato HTTP no): DTO en `app/schemas.py`, lógica y consultas SQL en `app/repository.py` (el router no importa `select`), rutas en `app/main.py`.

### Parte 1. Reprogramar una visita

```text
PATCH /api/v1/properties/{property_id}/visits/{visit_id}
Content-Type: application/json
```

**Cuerpo** (actualización parcial; todos los campos son opcionales):

| Campo | Tipo | Regla |
| :--- | :--- | :--- |
| `scheduled_start` | fecha ISO 8601 | Nuevo inicio |
| `scheduled_end` | fecha ISO 8601 | Nuevo fin |
| `notes` | texto | Máximo 280 caracteres; `""` borra las notas |

- Debe venir **al menos un** campo. Ningún campo puede ser `null`.
- Cualquier otro campo (por ejemplo `visitor_email`, `property_id` o `id`) se rechaza.

**Ventana resultante.** Se calcula combinando los campos enviados con los valores guardados de la visita (si solo envías `scheduled_start`, el fin es el que ya tenía). Esa ventana debe cumplir lo mismo que al agendar: fin estrictamente posterior al inicio y duración entre 15 y 240 minutos, ambos extremos incluidos.

**Traslape.** La ventana resultante no puede traslaparse con **otra** visita de la misma propiedad. Los intervalos son semiabiertos `[inicio, fin)`: tocar el borde de otra visita está permitido. La ventana anterior de la propia visita no cuenta como traslape. Es una operación de verificar y luego escribir: dos `PATCH` simultáneos que mueven visitas distintas al mismo horario terminan con uno en 200 y el otro en 409.

**Respuesta exitosa:** `200 OK` con `VisitResponse` (correo enmascarado en `visitor_email_masked`, fechas en UTC con sufijo `Z`). El cambio queda persistido.

**Errores, en este orden de evaluación** (se devuelve el primero que aplique):

| Orden | Situación | HTTP | `error.code` |
| :---: | :--- | :---: | :--- |
| 1 | Cuerpo o ruta inválidos: vacío, campo desconocido, `null`, tipo o formato incorrecto, `notes` de más de 280 caracteres, id fuera de rango | 422 | `VALIDATION_ERROR` |
| 2 | La propiedad no existe | 404 | `PROPERTY_NOT_FOUND` |
| 3 | La visita no existe **o** pertenece a otra propiedad | 404 | `VISIT_NOT_FOUND` |
| 4 | La propiedad tiene estado `sold` (las `reserved` sí admiten cambios) | 409 | `PROPERTY_UNAVAILABLE` |
| 5 | La ventana resultante no cumple fin > inicio o la duración de 15 a 240 minutos | 422 | `INVALID_VISIT_WINDOW` |
| 6 | La ventana resultante se traslapa con otra visita de la misma propiedad | 409 | `VISIT_SLOT_CONFLICT` |

El paso 1 lo hace FastAPI antes de llamar a tu código. Cuando una petición falla, la visita no cambia en nada, tampoco sus notas.

### Parte 2. Agenda de una agencia (consulta propia)

```text
GET /api/v1/agencies/{agency_id}/visits?from=<fecha>&to=<fecha>
```

Devuelve las visitas de **todas** las propiedades de la agencia (cualquier estado) que se traslapan con el rango semiabierto `[from, to)`: una visita entra si `scheduled_start < to` y `scheduled_end > from`. Una visita que termina exactamente en `from` o empieza exactamente en `to` no entra; una que empezó antes de `from` y sigue en curso, sí. `from` y `to` son obligatorios, en ISO 8601, normalizados a UTC como el resto de la API.

**Respuesta exitosa:** `200 OK` con una lista JSON (vacía si no hay visitas), ordenada por `scheduled_start` ascendente y, en empate, por `id` ascendente:

```json
[
  {"id": 7, "property_id": 3, "property_title": "Casa Norte", "visitor_name": "Luis Pérez",
   "visitor_email_masked": "l***@ejemplo.com", "scheduled_start": "2027-10-05T10:00:00Z",
   "scheduled_end": "2027-10-05T11:00:00Z", "notes": ""}
]
```

**Consultas acotadas:** la respuesta se arma con **como máximo 2 SELECT** (la agencia y las visitas con el título de su propiedad), sin importar cuántas propiedades o visitas tenga la agencia; un test lo mide con `before_cursor_execute`. Nada de consultas dentro de un ciclo. El límite de 31 días acota el tamaño de la respuesta.

**Errores, en este orden:**

| Orden | Situación | HTTP | `error.code` |
| :---: | :--- | :---: | :--- |
| 1 | Falta `from` o `to`, formato inválido, fecha fuera de rango o id fuera de rango | 422 | `VALIDATION_ERROR` |
| 2 | `to` no es posterior a `from`, o el rango supera 31 días (31 días exactos sí se aceptan) | 422 | `INVALID_DATE_RANGE` |
| 3 | La agencia no existe | 404 | `AGENCY_NOT_FOUND` |

### Tests ocultos

Los tests públicos de `tests/test_challenge.py` no cubren todos los bordes del contrato. La nota del reto incluye **tests ocultos** con más casos y datos distintos, escritos solo a partir de este contrato. Te lo decimos de antemano: no sirve programar contra los tests públicos; sirve cumplir el contrato.

## Tus tests propios

Reemplaza las 2 plantillas de `tests/student/test_my_scenarios.py` por al menos 2 escenarios del reto. Tus tests propios suman si pasan contra la solución de referencia y detectan mutantes que la suite pública no detecta (errores sembrados en el reto). Reescribir un test público no suma. Los mutantes que prueban el mismo concepto cuentan como uno solo: 2 conceptos distintos detectados valen el puntaje completo; 1, la mitad. No agregues `conftest.py` dentro de `tests/student/`.

## Rúbrica (100 puntos)

| Componente | Puntos | Cómo se mide |
| :--- | ---: | :--- |
| Taller guiado | 20 | `tests/test_workshop.py`, proporcional |
| Reto, tests públicos | 10 | `tests/test_challenge.py`, proporcional |
| Reto, tests ocultos | 30 | Tests ocultos, proporcional |
| Tests propios | 15 | Pasan contra la solución de referencia y detectan mutantes que la suite pública no detecta (los errores sembrados se agrupan por concepto: 2 conceptos distintos = completo, 1 = mitad) |
| ADR y checklist | 15 | revisión manual: ADR 10, checklist 2, sección propia de `AGENTS.md` 2 y declaración de uso de IA 1 |
| Calidad e integridad | 10 | `ruff check` y `ruff format --check` limpios (5) + sin sospechas de integridad (5) |
| **Total** | **100** | |

Los quizzes de la unidad se responden en la plataforma del curso y no forman parte de los 100 puntos del laboratorio.

El CI de GitHub (`.github/workflows/ci.yml`) es retroalimentación, no la nota. La nota oficial la calcula el calificador del curso con tests ocultos, mutantes y una revisión de integridad. Se reporta como sospecha: cambiar tests oficiales o el workflow, un `conftest.py` dentro de `tests/student/`, y en `app/` o `tests/student/` cualquier import fuera de lo habitual del proyecto (FastAPI, SQLModel, SQLAlchemy, Pydantic y la biblioteca estándar de datos y fechas), usar `os` para algo distinto de leer variables de entorno, abrir archivos, `pathlib`, `sys`, `eval`/`exec` o mencionar `pytest` dentro de `app/`.

<!-- texto-escaner:inicio (generado por scripts/texto_escaner.py; no editar a mano) -->

### Qué marca el escáner del calificador

El calificador revisa tu código y tus tests antes de correrlos. Si encuentra algo de esta lista, tu nota queda **retenida** hasta que el docente la revise: no pierdes puntos automáticamente, pero tampoco se publica. Nada de esto hace falta para resolver los retos.

**Por qué existe.** Tus tests corren en la misma máquina que los tests ocultos. Lo que se marca es lo que permitiría leer esos tests, cambiar el resultado de las pruebas o salir a internet desde el calificador.

**En este proyecto (Python).**

- En `app/` puedes importar: `__future__`, `abc`, `app`, `base64`, `bisect`, `collections`, `contextlib`, `copy`, `dataclasses`, `datetime`, `decimal`, `enum`, `fastapi`, `functools`, `google.genai`, `hashlib`, `heapq`, `hmac`, `html`, `itertools`, `json`, `jwt`, `logging`, `math`, `operator`, `os` (solo `os.environ` y `os.getenv`), `pydantic`, `pydantic_settings`, `re`, `secrets`, `sqlalchemy`, `sqlmodel`, `starlette`, `statistics`, `string`, `textwrap`, `threading`, `time`, `typing`, `typing_extensions`, `unicodedata`, `uuid` y `zoneinfo`.
- En `tests/student/` puedes importar: `__future__`, `abc`, `app`, `asyncio`, `base64`, `collections`, `concurrent.futures`, `contextlib`, `copy`, `dataclasses`, `datetime`, `decimal`, `enum`, `fastapi`, `functools`, `hashlib`, `hmac`, `itertools`, `json`, `jwt`, `math`, `operator`, `pydantic`, `pytest`, `random`, `re`, `sqlalchemy`, `sqlmodel`, `starlette`, `statistics`, `string`, `tests`, `textwrap`, `threading`, `time`, `typing`, `unicodedata`, `unittest` (incluido `unittest.mock`), `uuid` y `zoneinfo`.
- Sí puedes: `chr(0x200B)` y cualquier `chr`, unir textos (`"a" + "b"`, f-strings), `vars(objeto)` para comparar (`assert vars(x) == {...}`), `mock.patch("app.…")`, `mock.patch.dict("os.environ", {...})`, `monkeypatch.setenv`, `random` y `functools.singledispatch`.
- Se marca: `eval`, `exec`, `compile`, `open`, `input`, `breakpoint`, `globals`, `locals`, `__import__`, `memoryview`; `vars()` sin argumentos o usado para indexar, recorrer o guardar; `getattr`/`setattr`/`hasattr`/`delattr` con un nombre que no es un texto fijo (salvo sobre `self` o `cls`) o con un nombre prohibido; `operator.attrgetter`/`methodcaller` con nombres calculados o prohibidos; atributos mágicos (`__dict__`, `__globals__`, `__subclasses__`…, salvo `__name__`, `__init__`, `__class__` y `__all__`); acceso a módulos del sistema a través de otro objeto (`.sys`, `.builtins`, `.subprocess`, `.inspect`, `.io`, `.os` fuera de `environ`/`getenv`…); frames (`_getframe`, `f_back`…); procesos y archivos (`system`, `popen`, `fork`, `exec*`, `create_subprocess_exec`, `read_text`, `write_text`, `listdir`, `chdir`, `unlink`…); variables de entorno leídas con un nombre calculado o recorridas (en `app/`); textos, aunque estén armados por partes, que mencionen `pytest`, `junit`, `AWA_`, `site-packages`, `builtins` o atributos mágicos (en `app/`). En tests, además: rutas de módulos no permitidos escritas como texto (`mock.patch("subprocess.run")`, `"_pytest…"`), hooks de pytest (`def pytest_…`), `pytest_plugins`, `request.config.pluginmanager`/`hook`, y los internos de `mock.patch` y `monkeypatch` (`temp_original`, `getter`, `_setattr`); un `conftest.py` propio.

**En todos los proyectos** se marca además: modificar o borrar archivos oficiales, agregar archivos fuera de tus carpetas, enlaces simbólicos, y archivos como `sitecustomize.py`, `pytest.ini`, `init.gradle` o `.npmrc`. Y tus tests deben dar siempre el mismo resultado: un test que falla al azar no cuenta.

<!-- texto-escaner:fin -->

## Antes de entregar

- [ ] `uv run pytest -v` en verde, incluidos tus tests.
- [ ] `uv run ruff check .` y `uv run ruff format --check .` limpios.
- [ ] `ARCHITECTURE_DECISIONS.md` y `SECURITY_AND_QUALITY.md` respondidos con tus palabras.
- [ ] `AGENTS.md` ampliado con una regla tuya y la declaración de uso de IA en el ADR.

## Seguridad: lo que esta unidad todavía no protege

La API no tiene autenticación: cualquiera puede listar, mover o cancelar visitas. Por eso las respuestas públicas nunca exponen el correo completo del visitante (`visitor_email_masked`). La autenticación con JWT y el control de dueño llegan en la Unidad 3.
