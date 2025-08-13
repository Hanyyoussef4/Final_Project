# Final Project – Calculator App with JWT Authentication & Dashboard Stats
![CI/CD Status](https://github.com/Hanyyoussef4/Final_Project/actions/workflows/ci.yml/badge.svg)

## ✨ Feature Added

For this final project, we extended the existing calculator application by:

* **Implementing a JWT-secured `/reports/summary` endpoint** – Only authenticated users can access calculation history summaries via Swagger UI or API calls.
* **Enhancing the dashboard UI** – Added real-time calculation statistics display, integrating the backend data with the frontend view.

## 📊 New Feature – Stats UI Integration

Below is a preview of the enhanced dashboard UI with the new real-time stats section:

![Stats UI Integration](docs/Screenshots/1-stats%20UI%20Integration.png)


These changes improved both the **security** and **usability** of the application.

---

## 📦 Tech Stack

* **Backend:** FastAPI, SQLAlchemy, PostgreSQL
* **Frontend:** HTML, JavaScript (dashboard integration)
* **Authentication:** JWT-based secure login
* **Containerization:** Docker & Docker Compose
* **Testing:** pytest, Playwright (E2E)

---


## Calculations App – JWT-Secured CRUD + Reporting

A FastAPI + PostgreSQL application where authenticated users perform math calculations (add, subtract, multiply, divide), manage their history (BREAD/CRUD), and view personal stats via a JWT-secured **/reports/summary** endpoint. A lightweight HTML dashboard (Jinja + Tailwind) provides a polished UI. Swagger UI documents and exercises the API with OAuth2 Password Flow (Bearer tokens).

## ✨ Key features

* User auth with JWT (access/refresh), password hashing
* Create/List/View/Edit/Delete **Calculations**
* **Reports Summary**: total calculations, counts by operation, average operands, recent items
* Swagger UI with OAuth2 password flow
* Modern dashboard UI powered by fetch() calls to the API
* Unit + integration tests (pytest) including reports service and endpoint

## 🏰 Tech

FastAPI • SQLAlchemy • Alembic (optional) • PostgreSQL • Jinja2 • TailwindCSS • Pytest • Uvicorn

---

## 1) Quick start

### A. Local (Python venv)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` in project root:

```
# app/core/config.py reads this
DATABASE_URL=postgresql+psycopg2://app:app@127.0.0.1:5432/app
JWT_SECRET=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ENV=dev
```

Run PostgreSQL (Docker) if you don’t already have a local DB:

```bash
docker compose up -d db
# if needed, create role/db:
docker exec -it final_project-db-1 psql -U postgres -c "CREATE ROLE app LOGIN PASSWORD 'app';"
docker exec -it final_project-db-1 psql -U postgres -c "CREATE DATABASE app OWNER app;"
```
### Database migrations

Set the DB URL (example: local SQLite) and upgrade:

```bash
export DATABASE_URL="sqlite:///$PWD/dev.db"
alembic upgrade head

Start the API:

```bash
uvicorn app.main:app --reload --port 8001
```

Open:

* UI:            [http://127.0.0.1:8001/dashboard](http://127.0.0.1:8001/dashboard)
* Swagger (API): [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

### B. With Docker Compose (app + db)

> (optional if you already run locally)

```bash
docker compose up --build
# API on http://127.0.0.1:8001
```

---

## 2) Using the app

### Register & login

* POST `/auth/register` in Swagger or use the **Register** page
* POST `/auth/login` to get `access_token` (and refresh token)
* The dashboard stores `access_token` in localStorage and attaches it via `Authorization: Bearer <token>`.

### CRUD

* **Create**: POST `/calculations` (body: `{"type":"addition","inputs":[5,7,3,10]}`)
* **List**: GET `/calculations`
* **Read**: GET `/calculations/{id}`
* **Update**: PUT `/calculations/{id}` (body with new `inputs`)
* **Delete**: DELETE `/calculations/{id}`

### Reports

* **GET `/reports/summary`** →

  ```json
  {
    "total_calculations": 8,
    "counts_by_operation": {"addition": 2, "subtraction": 2, "multiplication":1, "division":3},
    "average_operands": 3.00,
    "recent_calculations": [
      {"id":"…","type":"addition","inputs":[5,7,3,10],"result":25,"created_at":"2025-08-13T…Z"}
    ]
  }
  ```

### Swagger OAuth2 password flow

1. Click **Authorize** in `/docs`
2. Enter username/password (created at registration)
3. Swagger obtains JWT and automatically adds `Authorization: Bearer …` to calls
4. Confirm in Browser DevTools → Network → request headers

---

## 3) Project structure (high-level)

```
app/
  api/routers/reports.py         # /reports/summary
  auth/                          # jwt, dependencies
  models/                        # SQLAlchemy models (User, Calculation)
  schemas/                       # Pydantic schemas
  reports/service.py             # build_report_summary()
  templates/                     # Jinja templates (dashboard.html, etc.)
  main.py                        # FastAPI app + routers + web routes
tests/
  unit/test_reports_service.py
  integration/test_reports_endpoint.py
```

---

## 4) Development scripts

Run tests:

```bash
pytest -q
# or with coverage
pytest --maxfail=1 --disable-warnings -q --cov=app
```

Useful curls:

```bash
# Login
curl -X POST http://127.0.0.1:8001/auth/login \
  -H "content-type: application/json" \
  -d '{"username":"hy326","password":"<pwd>"}'

# Create calculation
curl -X POST http://127.0.0.1:8001/calculations \
  -H "authorization: Bearer <ACCESS_TOKEN>" \
  -H "content-type: application/json" \
  -d '{"type":"addition","inputs":[5,6]}'

# Reports summary
curl -H "authorization: Bearer <ACCESS_TOKEN>" \
  http://127.0.0.1:8001/reports/summary
```

---

## 5) Troubleshooting

* **401 Unauthorized in UI**: token expired → login again (localStorage cleared automatically).
* **DB “connection refused”**: ensure Docker is running and the `db` container is healthy; confirm `DATABASE_URL`.
* **JWT not attached in Swagger**: click **Authorize** again; confirm the lock icon shows as “Authorized”.
* **Numbers don’t appear in history**: check Browser DevTools → Network → `POST /calculations` is 201 and payload is correct.

---


