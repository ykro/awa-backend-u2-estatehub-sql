# SECURITY_AND_QUALITY.md (Unidad 2)

Marca cada casilla solo si lo verificaste en tu código, y escribe al lado **dónde** (archivo y función o test). Una casilla marcada sin evidencia no cuenta.

## 1. Datos y contratos

- [ ] Ninguna consulta SQL concatena texto del usuario; todas usan expresiones parametrizadas. Evidencia:
- [ ] Todos los DTO de entrada (incluido `VisitUpdate`) rechazan campos extra con 422. Evidencia:
- [ ] Ningún campo `null` ni cuerpo vacío llega al repositorio en el `PATCH`. Evidencia:
- [ ] Las respuestas públicas no exponen el correo completo del visitante. Evidencia:
- [ ] Los errores de validación no devuelven `input` ni `ctx`. Evidencia:

## 2. Consultas y transacciones

- [ ] `size` tiene un máximo (anti abuso) y la paginación tiene `ORDER BY` determinista. Evidencia:
- [ ] El listado no tiene N+1 y el test de consultas acotadas pasa. Evidencia:
- [ ] Un `PATCH` rechazado (404, 409 o 422) no deja cambios a medias en la visita. Evidencia:
- [ ] Una visita no se puede modificar a través de otra propiedad. Evidencia:
- [ ] Ids, `page`, precios y fechas extremas responden 422, nunca 500. Evidencia:
- [ ] Dos reservas simultáneas al mismo horario no producen dos visitas. Evidencia:
- [ ] La agenda de agencia usa un número de consultas que no crece con los datos. Evidencia:

## 3. Tests y calidad

- [ ] Los tests corren sobre SQLite en memoria y no crean archivos `.db`. Evidencia:
- [ ] Mis tests propios fallarían si alguien cambia `<` por `<=` en el traslape u olvida excluir la propia visita. Evidencia:
- [ ] `ruff check` y `ruff format --check` limpios. Evidencia:

## 4. Riesgos conocidos (no se resuelven en esta unidad)

Describe en 2 o 3 líneas qué puede hacer hoy un usuario anónimo con esta API y qué tendría que cambiar en la Unidad 3.

> Tu respuesta:
