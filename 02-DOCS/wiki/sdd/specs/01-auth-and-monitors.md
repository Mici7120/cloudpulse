---
type: spec
title: CloudPulse — Milestone 1: Authentication and HTTP Monitors CRUD
description: Base backend foundation with FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, user auth (hashed passwords + JWT), and per-user HTTP monitor CRUD.
tags: [sdd, spec, milestone-1, auth, monitors]
timestamp: 2026-11-23T07:17:00Z
topic: sdd
status: approved
branch: feat/01-auth-and-monitors
---

# Spec: 01-auth-and-monitors — Autenticación y CRUD de monitores HTTP

## Problema & por qué

CloudPulse necesita un núcleo de backend operativo antes de ejecutar chequeos de disponibilidad, registrar despliegues o enviar alertas. Hoy el repositorio solo contiene el harness de gobernanza y documentación, sin aplicación ni persistencia. Sin un sistema de identidad de usuarios y una gestión persistente de monitores HTTP aislados por cuenta, no existe ninguna entidad sobre la que construir el worker de pings, los conectores de alertas ni el frontend.

## Qué pasa si no lo construimos

Si no se construye este hito base, CloudPulse no puede registrar usuarios ni almacenar qué endpoints HTTP deben vigilarse. Cualquier hito posterior (worker de pings, alertas por Telegram, webhooks de despliegue o panel en Next.js) quedaría bloqueado o tendría que operar sobre listas estáticas sin aislamiento entre usuarios ni persistencia real en PostgreSQL.

## La alternativa más barata

La alternativa más barata sería guardar una lista fija de URLs en un archivo YAML o JSON sin usuarios ni base de datos. Eso evitaría implementar autenticación y CRUD, pero no cubre el objetivo de CloudPulse como monitor multiusuario con historial, despliegues y alertas asociadas a cuentas, y obligaría a reescribir la capa de datos y seguridad en cuanto se añadiera el frontend o el segundo usuario.

## Objetivos

1. Establecer la base reproducible de `backend/` con FastAPI, SQLAlchemy 2.x, Alembic y `docker-compose.yml` para levantar PostgreSQL localmente.
2. Permitir que un usuario se registre e inicie sesión de forma segura mediante contraseñas hasheadas y tokens JWT firmados.
3. Permitir a cada usuario autenticado crear, listar, consultar, actualizar y eliminar sus propios monitores HTTP, garantizando aislamiento estricto entre usuarios.
4. Mantener un contrato HTTP tipado, documentado en OpenAPI y con sobre de error estructurado consistente (`detail`, `code`).

## Fuera de alcance

Queda explícitamente excluido de este hito (no implementar ni añadir "por si acaso"):

- Worker o scheduler de pings periódicos, ejecución de peticiones HTTP hacia las URLs monitorizadas y almacenamiento de resultados/incidentes.
- Conectores externos en `01-TOOLS/` (alertas de Telegram, webhooks de despliegues de GitHub u otros proveedores).
- Frontend en Next.js (`frontend/`).
- Refresh tokens, revocación distribuida de sesiones, recuperación de contraseña por email, verificación de correo, OAuth/SSO y roles de administrador.
- Rate limiting avanzado o despliegue en producción (Kubernetes/cloud).

## Usuarios & contexto

- **Usuario autenticado (operador/desarrollador):** gestiona sus propios monitores HTTP a través de la API para registrar los servicios que quiere vigilar en CloudPulse.
- **Cliente no autenticado:** solo puede comprobar la salud del servicio (`GET /health`), registrar una cuenta (`POST /auth/register`) o iniciar sesión (`POST /auth/login`). No puede leer ni modificar ningún monitor.

## Qué podrá hacer el usuario

1. **Comprobar salud del servicio (`GET /health`)** — Cualquier cliente (sin autenticación) puede verificar que la API está activa y conectada a PostgreSQL.
2. **Registrarse (`POST /auth/register`)** — Un cliente no autenticado puede crear una cuenta nueva con `email` único y `password`.
3. **Iniciar sesión (`POST /auth/login`)** — Un usuario registrado puede autenticarse con `email` y `password` válidos para obtener un `access_token` JWT de tipo `bearer`.
4. **Crear un monitor (`POST /monitors`)** — Un usuario autenticado con JWT válido puede crear un monitor HTTP con `name`, `url`, `interval_seconds`, `expected_status` e `is_active` asociado a su propia cuenta.
5. **Listar sus monitores (`GET /monitors`)** — Un usuario autenticado puede listar exclusivamente los monitores que le pertenecen.
6. **Consultar un monitor (`GET /monitors/{monitor_id}`)** — Un usuario autenticado puede ver el detalle de uno de sus monitores; nunca puede ver los de otro usuario.
7. **Actualizar un monitor (`PATCH /monitors/{monitor_id}`)** — Un usuario autenticado puede modificar parcialmente uno o más campos (`name`, `url`, `interval_seconds`, `expected_status`, `is_active`) de uno de sus monitores.
8. **Eliminar un monitor (`DELETE /monitors/{monitor_id}`)** — Un usuario autenticado puede eliminar uno de sus monitores.

## Qué resultado obtiene

Todas las respuestas exitosas y de error siguen esquemas Pydantic tipados y el sobre de error estructurado `{"detail": "<mensaje>", "code": "<CODIGO_ESTABLE>"}`.

### 1. `GET /health` — `200 OK`

```json
{
  "status": "ok",
  "database": "ok"
}
```

Si la base de datos no responde: `503 Service Unavailable`

```json
{
  "detail": "Database connection unavailable",
  "code": "DATABASE_UNAVAILABLE"
}
```

### 2. `POST /auth/register` — `201 Created`

Entrada: `{"email": "alice@example.com", "password": "strong-password-123"}`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alice@example.com",
  "created_at": "2026-11-23T07:17:00Z"
}
```

- Nunca devuelve `password` ni `password_hash`.
- Si el `email` ya existe: `409 Conflict` con `{"detail": "Email already registered", "code": "EMAIL_ALREADY_EXISTS"}`.

### 3. `POST /auth/login` — `200 OK`

Entrada: `{"email": "alice@example.com", "password": "strong-password-123"}`

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

- Si el email no existe o la contraseña no coincide: `401 Unauthorized` con `{"detail": "Invalid email or password", "code": "INVALID_CREDENTIALS"}` (mismo mensaje y código en ambos casos para evitar enumeración de cuentas).

### 4. `POST /monitors` — `201 Created` (requiere `Authorization: Bearer <jwt>`)

Entrada:

```json
{
  "name": "API Production",
  "url": "https://api.example.com/health",
  "interval_seconds": 60,
  "expected_status": 200,
  "is_active": true
}
```

Respuesta:

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "API Production",
  "url": "https://api.example.com/health",
  "interval_seconds": 60,
  "expected_status": 200,
  "is_active": true,
  "created_at": "2026-11-23T07:18:00Z",
  "updated_at": "2026-11-23T07:18:00Z"
}
```

### 5. `GET /monitors` — `200 OK` (requiere `Authorization: Bearer <jwt>`)

```json
{
  "items": [
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "name": "API Production",
      "url": "https://api.example.com/health",
      "interval_seconds": 60,
      "expected_status": 200,
      "is_active": true,
      "created_at": "2026-11-23T07:18:00Z",
      "updated_at": "2026-11-23T07:18:00Z"
    }
  ],
  "total": 1
}
```

Si el usuario no tiene monitores, devuelve `{"items": [], "total": 0}`.

### 6. `GET /monitors/{monitor_id}` — `200 OK` (requiere `Authorization: Bearer <jwt>`)

Devuelve el mismo objeto monitor que `POST /monitors`. Si no existe o pertenece a otro usuario: `404 Not Found` con `{"detail": "Monitor not found", "code": "MONITOR_NOT_FOUND"}`.

### 7. `PATCH /monitors/{monitor_id}` — `200 OK` (requiere `Authorization: Bearer <jwt>`)

Actualiza solo los campos enviados y devuelve el objeto monitor actualizado con `updated_at` refrescado. Si no existe o pertenece a otro usuario: `404 Not Found` con `{"detail": "Monitor not found", "code": "MONITOR_NOT_FOUND"}`.

### 8. `DELETE /monitors/{monitor_id}` — `204 No Content` (requiere `Authorization: Bearer <jwt>`)

Elimina el monitor y responde sin cuerpo. Si no existe o pertenece a otro usuario: `404 Not Found` con `{"detail": "Monitor not found", "code": "MONITOR_NOT_FOUND"}`.

### 9. Errores comunes de autenticación y validación

- Sin token, token malformado o token expirado en cualquier ruta `/monitors*`: `401 Unauthorized` con `{"detail": "Not authenticated", "code": "UNAUTHORIZED"}` o `{"detail": "Invalid or expired token", "code": "INVALID_TOKEN"}`.
- Payload inválido (email inválido, contraseña demasiado corta, URL sin esquema `http`/`https`, `interval_seconds` o `expected_status` fuera de rango): `422 Unprocessable Entity` con sobre estructurado `{"detail": "...", "code": "VALIDATION_ERROR"}`.

## Qué debe respetar

Según `02-DOCS/wiki/sdd/constitution.md` (v1.0.0), `02-DOCS/wiki/sdd/REVIEW.md` y `.rsc-risk.json`:

1. **Stack canon (Principios 1, 2, 4, 5):** Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL y `docker-compose.yml`; lockfile de dependencias commiteado en Git.
2. **Migraciones reversibles (Principio 2, REVIEW.md #1):** Toda tabla (`users`, `monitors`) y relación/índice nace en una migración Alembic con `upgrade()` y `downgrade()` funcionales y probados.
3. **Calidad y tipado estricto (Principios 6, 7, 10):** Ruff format + lint con 0 errores y 0 warnings; mypy/pyright con 0 errores; endpoints tipados con Pydantic y sobre de error consistente (`detail`, `code`, HTTP status) expuesto en OpenAPI.
4. **TDD estricto y cobertura (Principio 8):** Ciclo red -> green -> refactor con `pytest` y cobertura de líneas >= 80% sobre el código nuevo/modificado.
5. **Fronteras del repositorio (Principio 9):** Código backend únicamente en `backend/` y orquestación local en `docker-compose.yml`; sin crear archivos en `frontend/` ni conectores en `01-TOOLS/`.
6. **Seguridad y secretos (Principio 14, REVIEW.md #2 y #3):** Contraseñas hasheadas con algoritmo resistente (argon2 o bcrypt), nunca almacenadas ni logueadas en claro; `JWT_SECRET_KEY` y credenciales de PostgreSQL cargadas por variables de entorno (solo `.env.example` en Git, nunca `.env`).
7. **Riesgo Tier 2 y gobernanza (Principios 11, 12, 13, 16):** Al tocar `^backend/.*auth` y `^backend/alembic/`, esta rama es Tier 2 y requiere spec aprobada, panel de revisión de 3 lentes (correctness, security, tests) y aprobación humana explícita antes de merge; commits y PR en inglés con Conventional Commits, sin emojis y con autoría humana únicamente.

## Cómo lo demuestra

El hito solo se considera demostrado cuando toda la siguiente evidencia queda ejecutada y verificada en CI y/o entorno local:

1. **Suite de tests automatizados (`pytest`)**: pruebas de integración y unidad que cubren `GET /health`, registro exitoso y duplicado, login exitoso y fallido, rechazo de `/monitors` sin token o con token inválido/expirado, CRUD completo de `/monitors`, validaciones de entrada y aislamiento estricto entre Usuario A y Usuario B, con cobertura >= 80% (`pytest --cov`).
2. **Reversibilidad de migraciones**: ejecución limpia contra PostgreSQL de `alembic upgrade head`, `alembic downgrade base` y nuevamente `alembic upgrade head` sin errores.
3. **Calidad estática**: salida limpia (código 0, cero warnings) de `ruff check`, `ruff format --check` y `mypy` sobre `backend/`.
4. **Arraque con Docker Compose**: `docker compose up -d` levanta PostgreSQL y `GET /health` responde `200 OK` con `{"status": "ok", "database": "ok"}`.
5. **Puertas de gobernanza**: `npx --yes @ericrisco/rsc@4.1.8 spec gate 02-DOCS/wiki/sdd/specs/01-auth-and-monitors.md` en `PASS`, panel de revisión de 3 lentes registrado en el ledger y check `CI Spec Gate` en verde en el PR.

## Comportamiento

- **Normalización de email:** el `email` se normaliza (espacios recortados y minúsculas) antes de validar unicidad, guardar y autenticar, de modo que `Alice@Example.com` y `alice@example.com` se tratan como la misma cuenta.
- **Hashing de contraseñas:** las contraseñas se hashean con sal aleatoria por usuario al registrarse y se verifican en tiempo constante al hacer login.
- **Emisión y validación JWT:** el login firma un token con `sub` (ID del usuario), `iat` y `exp`. Cualquier petición a `/monitors*` extrae el Bearer token, valida firma y expiración, y resuelve el usuario propietario en base de datos.
- **Aislamiento de monitores:** toda consulta, actualización o borrado en `/monitors` filtra siempre por `owner_id == current_user.id`. Un usuario nunca puede leer, modificar ni eliminar un monitor perteneciente a otro usuario.
- **Valores por defecto en creación de monitor:** si no se especifican en `POST /monitors`, `interval_seconds` toma `60`, `expected_status` toma `200` e `is_active` toma `true`.
- **Actualización parcial (`PATCH`):** solo se actualizan los campos explícitamente incluidos en el JSON; enviar un cuerpo vacío `{}` devuelve `200 OK` sin alterar el monitor.

## Criterios de aceptación

1. **Health check operativo**
   - Given PostgreSQL está levantado y accesible desde el backend
   - When un cliente sin token envía `GET /health`
   - Then recibe `200 OK` con `{"status": "ok", "database": "ok"}`.

2. **Registro de usuario válido**
   - Given no existe un usuario con `email` `alice@example.com`
   - When un cliente envía `POST /auth/register` con `email` y `password` válida
   - Then recibe `201 Created` con `id`, `email` normalizado y `created_at`, sin contraseña ni hash en la respuesta, y la contraseña se almacena hasheada en PostgreSQL.

3. **Registro con email duplicado**
   - Given ya existe un usuario con `email` `alice@example.com`
   - When un cliente envía `POST /auth/register` con `ALICE@example.com`
   - Then recibe `409 Conflict` con `{"detail": "Email already registered", "code": "EMAIL_ALREADY_EXISTS"}`.

4. **Login exitoso y login fallido**
   - Given un usuario registrado con credenciales conocidas
   - When envía `POST /auth/login` con credenciales correctas
   - Then recibe `200 OK` con `access_token`, `token_type: "bearer"` y `expires_in`.
   - When envía `POST /auth/login` con contraseña incorrecta o email inexistente
   - Then recibe `401 Unauthorized` con `{"detail": "Invalid email or password", "code": "INVALID_CREDENTIALS"}`.

5. **Protección JWT en `/monitors`**
   - Given una petición a cualquier endpoint `/monitors` o `/monitors/{id}`
   - When no incluye cabecera `Authorization: Bearer <token>` o el token es inválido/expirado
   - Then recibe `401 Unauthorized` con sobre de error estructurado.

6. **CRUD completo de monitores del usuario**
   - Given un usuario autenticado con JWT válido
   - When crea un monitor vía `POST /monitors`, lo lista con `GET /monitors`, lo consulta con `GET /monitors/{id}`, actualiza `interval_seconds` o `is_active` con `PATCH /monitors/{id}` y lo elimina con `DELETE /monitors/{id}`
   - Then cada operación devuelve el código HTTP esperado (`201`, `200`, `200`, `200`, `204`), persiste el estado en PostgreSQL y tras `DELETE` una consulta posterior devuelve `404 Not Found`.

7. **Aislamiento estricto entre usuarios**
   - Given el Usuario A crea un monitor `M1` y el Usuario B tiene un JWT válido propio
   - When el Usuario B ejecuta `GET /monitors`, `GET /monitors/M1`, `PATCH /monitors/M1` o `DELETE /monitors/M1`
   - Then `GET /monitors` no incluye `M1`, y `GET/PATCH/DELETE /monitors/M1` devuelven `404 Not Found` sin modificar `M1`.

8. **Validación de campos de monitor**
   - Given un usuario autenticado
   - When envía `POST /monitors` o `PATCH /monitors/{id}` con `url` sin esquema `http`/`https`, `interval_seconds` fuera de rango o `expected_status` fuera de `100..599`
   - Then recibe `422 Unprocessable Entity` con sobre de error estructurado.

9. **Reversibilidad de migraciones y calidad**
   - Given una base de datos PostgreSQL limpia
   - When se ejecutan `alembic upgrade head`, `alembic downgrade base`, `alembic upgrade head`, `ruff check`, `ruff format --check`, `mypy` y `pytest --cov`
   - Then todos terminan con código de salida `0` y la cobertura en código cambiado es >= 80%.

## Puntos a clarificar

- **suposición tomada** — Aislamiento en `GET/PATCH/DELETE /monitors/{monitor_id}` devuelve `404 Not Found` cuando el monitor pertenece a otro usuario (aprobado por el owner; evita enumeración de IDs).
- **suposición tomada** — Validación de monitores: solo URLs `http://` o `https://`, `interval_seconds` en `[30, 86400]` (default `60`) y `expected_status` en `[100, 599]` (default `200`) (aprobado por el owner).
- **suposición tomada** — Contraseña mínima de `8` caracteres hasheada con `argon2` y JWT stateless con expiración configurable vía `JWT_EXPIRE_MINUTES` (default `60` minutos) (aprobado por el owner).
- **suposición tomada** — `DELETE /monitors/{monitor_id}` realiza borrado físico con `204 No Content` (aprobado por el owner; `is_active` vía `PATCH` cubre pausar/reactivar).
- **suposición tomada** — Los identificadores (`id`) de `users` y `monitors` son UUID v4 serializados como string. *Base:* evita IDs secuenciales predecibles en endpoints multiusuario. *Estado:* validada al aprobar la spec.
- **suposición tomada** — El sobre de error estructurado sigue exactamente `{"detail": "...", "code": "..."}` (Principio 10 de `constitution.md`), incluyendo errores de validación `422` mediante un manejador global de FastAPI. *Base:* mantiene un único formato predecible para todos los consumidores. *Estado:* validada al aprobar la spec.
- **decisión diferida** — Paginación con `limit`/`offset` en `GET /monitors`, historial de checks, worker periódico, conectores en `01-TOOLS/` y frontend Next.js quedan para hitos posteriores.

## Clarifications

- `2026-11-23` — **Q1 (Aislamiento en `/monitors/{id}`):** `404 Not Found` vs `403 Forbidden` -> **Decisión:** `404 Not Found` (`MONITOR_NOT_FOUND`). **Por qué:** evita confirmar existencia de IDs de otros usuarios.
- `2026-11-23` — **Q2 (Validaciones de monitor):** Esquema URL y rangos -> **Decisión:** `http://` o `https://`, `interval_seconds` `[30, 86400]` (default `60`), `expected_status` `[100, 599]` (default `200`). **Por qué:** acota entradas inválidas antes de persistir y protege el futuro worker.
- `2026-11-23` — **Q3 (Contraseña y JWT):** Algoritmo y expiración -> **Decisión:** mínimo 8 caracteres, hashing `argon2`, JWT stateless con `JWT_EXPIRE_MINUTES` (default `60`). **Por qué:** estándar seguro y simple para Hito 1 sin complejidad de refresh tokens.
- `2026-11-23` — **Q4 (`DELETE /monitors/{id}`):** Borrado físico vs lógico -> **Decisión:** borrado físico con `204 No Content`. **Por qué:** `is_active` vía `PATCH` ya cubre pausar/reactivar sin ambigüedad.

