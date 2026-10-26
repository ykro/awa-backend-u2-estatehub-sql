# ARCHITECTURE_DECISIONS.md (Unidad 2)

Responde con tus palabras y con referencias concretas a tu código (archivo y función). Respuestas genéricas o copiadas de la documentación no suman puntos. Extensión sugerida: 4 a 8 líneas por pregunta.

## 1. Capas

¿Por qué `app/main.py` no importa `select()` ni las tablas? Describe un cambio concreto (por ejemplo, migrar de SQLite a PostgreSQL) y qué archivos tocaría con y sin esta separación.

> Tu respuesta:

## 2. Problema N+1

¿Cuántas consultas ejecuta tu `list_properties` para una página de 10 propiedades de 10 agencias distintas? ¿Cuántas ejecutaría una versión que lee `prop.agency.name` dentro de un ciclo? ¿Cuántas ejecuta tu agenda de agencia (parte 2 del reto) y por qué ese número no crece con la cantidad de propiedades?

> Tu respuesta:

## 3. Reprogramar sin chocar consigo misma

Explica cómo tu `PATCH` evita reportar traslape con la ventana anterior de la misma visita y cómo combina los campos enviados con los guardados. Incluye un ejemplo de horario que tus tests verifican.

> Tu respuesta:

## 4. Fechas y zonas horarias

¿Qué pasa con `2027-06-04T10:00:00-06:00` desde que llega en el JSON hasta que se guarda y se compara en SQL? ¿Qué ocurre si llega `2027-06-04T10:00:00` (sin zona) y no la normalizas? ¿Por qué `replace(tzinfo=UTC)` no es lo mismo que `astimezone(UTC)`?

> Tu respuesta:

## 5. Concurrencia

Diez personas intentan reservar el mismo horario al mismo tiempo. ¿Por qué "consultar si hay traslape y luego insertar" puede dejar dos reservas con SQLite si no se hace nada especial? ¿Qué hace `begin_write` (`BEGIN IMMEDIATE`) y por qué se usa solo en las operaciones que verifican y luego escriben, y no en todas las transacciones? ¿Qué costo tiene y qué usarías en PostgreSQL?

> Tu respuesta:

## 6. Persistencia y varios procesos

Explica qué pasa con los datos al reiniciar la API con `ESTATEHUB_DATABASE_URL=sqlite://` y con un archivo, qué pasaría con 3 procesos que tuvieran cada uno su propia base, y qué cambiarías en este proyecto para usar un servidor de base de datos como PostgreSQL (archivos y variables concretos).

> Tu respuesta:

## 7. Tu regla en AGENTS.md

Copia la regla que agregaste en la sección 6 de `AGENTS.md`. Explica qué error de un asistente de IA previene y describe una ocasión concreta en que la regla cambió (o habría cambiado) lo que el asistente te propuso.

> Tu respuesta:

## 8. Declaración de uso de IA

Marca y completa lo que aplique. Usar IA está permitido; ocultarlo no.

- [ ] No usé asistentes de IA en esta unidad.
- [ ] Usé asistentes de IA. Herramientas: ____________________
- [ ] Partes donde la usé (código, tests, documentación): ____________________
- [ ] Una sugerencia de la IA que rechacé o corregí y por qué: ____________________
