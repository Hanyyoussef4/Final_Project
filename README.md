# Module 14


# Calculations App (FastAPI + PostgreSQL + Playwright)

> CI status: ![CI](https://github.com/<YOUR_USER>/<YOUR_REPO>/actions/workflows/test.yml/badge.svg)

A small web app that demonstrates **BREAD** (Browse, Read, Edit, Add, Delete) with a calculator history, backed by PostgreSQL and exposed via both **HTML pages** and **JSON APIs**. Includes **token-based auth** (register/login/me), **pytest** unit/API tests, and **Playwright** end-to-end tests. CI runs in **GitHub Actions**.

A tiny CRUD-style app to create and review math calculations (addition, etc.). The stack includes **FastAPI**, **SQLAlchemy**, **PostgreSQL**, **Docker Compose**, and **Playwright** for end‑to‑end UI tests.

> ✅ Status: all unit/integration/E2E tests pass .


## Deploy Proof

[![Docker Hub: hany25/module14](docs/screenshots/DockerHub Images.png)](https://hub.docker.com/r/hany25/module14 "Open Docker Hub repo")

[![GitHub Actions: deploy workflow](docs/screenshots/GitHub Actions workflow.png)]"Open deploy workflow")


# BREAD Calculator (FastAPI + Docker + Postgres)
---
## Features

* **BREAD**

  * HTML pages for create/browse/edit/delete
  * JSON API for programmatic access
* **Auth**

  * `/auth/register`, `/auth/login`, `/auth/me`
  * Simple time‑limited token using `itsdangerous`
* **Database**

  * PostgreSQL via SQLAlchemy ORM
* **DX**

  * Docker Compose for dev
  * PyTest (unit + API) and Playwright (UI) tests
  * GitHub Actions CI

---
## Table of contents

* [Prerequisites](#prerequisites)
* [Quick start (Docker Compose)](#quick-start-docker-compose)
* [Environment](#environment)
* [Running tests](#running-tests)
* [E2E traces & artifacts](#e2e-traces--artifacts)
* [Project structure](#project-structure)
* [Common dev tasks](#common-dev-tasks)
* [Publish image to Docker Hub](#publish-image-to-docker-hub)
* [CI/CD (GitHub Actions example)](#cicd-github-actions-example)
* [Troubleshooting](#troubleshooting)

---

## Prerequisites

* Docker + Docker Compose
* Python 3.11+ (project runs on 3.13 in dev)
* (For UI tests) Playwright browsers: `python -m playwright install chromium`

---

## Quick start (Docker Compose)

Start the full stack (Postgres, pgAdmin, app):

```bash
# from repo root
docker compose up -d db pgadmin web

# confirm containers
docker compose ps

# app should now be reachable
open http://127.0.0.1:8000
```

> The UI shows a dashboard where you can enter values like `10.5, 3, 2`, pick an operation, and view details.

---

## Environment

The app and tests work out‑of‑the‑box with the compose defaults. If you prefer an explicit file, create **.env** from this example:

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=module14_is601
PGHOST=127.0.0.1
PGPORT=5432
PGUSER=postgres
PGPASSWORD=postgres
PGDATABASE=module14_is601

# Optional FastAPI settings (if your app reads them)
SECRET_KEY=dev-secret-change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60

# The tests/fixtures fall back to this if DATABASE_URL is not set
DATABASE_URL=postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/module14_is601
```

> **Note**: For Docker Compose, the DB connection is provided via service networking; for local tests we default to the host‑mapped port `5432`.

---

## Running tests

### Unit + Integration (fast)

```bash
# show coverage inline
pytest -q -m "not e2e" --cov=app --cov-report=term-missing
```

### End‑to‑End UI (Playwright)

```bash
# first time only – install browser binaries
python -m playwright install chromium

# headed with trace capture on failure
pytest -q tests/e2e --headed --tracing=retain-on-failure

# single flow (handy while iterating)
pytest -q tests/e2e/test_ui_bread_playwright.py::test_create_read_edit_delete_flow \
  --headed --tracing=retain-on-failure
```

### Full suite

```bash
pytest -q --headed --tracing=retain-on-failure
```

---

## E2E traces & artifacts

UI test artifacts are written to `artifacts/e2e/`:

* `*.png` – full‑page screenshots
* `*.html` – DOM snapshots at failure points
* Playwright trace (if enabled in your local config / CI)

---

## Project structure

Below is a snapshot of the repo layout. Keep this section up to date by regenerating the tree and pasting it here.

```text
<project-root>
├─ app/
│  ├─ auth/
│  ├─ models/
│  ├─ schemas/
│  ├─ operations/
│  ├─ main.py
│  └─ database.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ e2e/
├─ docs/
│  └─ Screenshots/ …
├─ docker-compose.yml
├─ Dockerfile
└─ README.md
```
---

## Troubleshooting

* **Playwright not found**: run `python -m playwright install chromium`.
* **DB connection refused**: wait a few seconds after `docker compose up -d`; Postgres needs time to accept connections.
* **E2E clicks not working**: artifacts are in `artifacts/e2e/` — open the `.html` or `.png` generated at failure points.
* **Port conflict**: adjust exposed ports in `docker-compose.yml` (e.g., use `8001:8000`).

---
## Assignment Reflection

### What I set out to build

A small BREAD/CRUD Calculations app with a clean FastAPI backend, PostgreSQL via SQLAlchemy, and a simple Tailwind/HTMX UI. The goal was to practice proper testing at three layers: unit, integration, and Playwright end‑to‑end.

### What I learned

* **FastAPI + SQLAlchemy + Postgres:** how to run everything locally with Docker Compose and connect via `DATABASE_URL`.
* **Deterministic tests:** using an engine fixture and a `db_session` that wraps each test in a transaction + rollback so the database stays clean between tests.
* **SQLAlchemy sessions:** avoiding `DetachedInstanceError` by keeping objects bound to the same session or returning plain dictionaries from helpers; using `commit()` + `refresh()` when I need generated fields.
* **Uniqueness & transactions:** seeing `IntegrityError` for duplicate email/username, then rolling back and proceeding. I added guard checks in the model and caught errors in tests intentionally.
* **Resilient Playwright tests:** preferring role/label selectors, adding fallbacks, and waiting for UI state (e.g., heading with “Result/Details/Calculation”). The failure artifacts (`.png`/`.html`) were invaluable for debugging.
* **Docker workflow:** verifying services with `docker compose ps`, `curl /health`, and reading logs; tagging and pushing images to Docker Hub.

### Debugging highlights

* Fixed a missing `engine` argument in the test session factory.
* Resolved flaky UI waits by broadening selectors and waiting for new rows/cards or visible headings.
* Addressed transaction issues by rolling back on exceptions in the fixture teardown.

### DevOps & CI

* Wrote a lightweight GitHub Actions example that runs unit/integration tests, then E2E, and on tags builds & pushes the Docker image.
* Practiced tagging (`0.1.0`, `latest`) and verified pulling the image with Compose.

### What I’d improve next

* Add more operations (subtract/multiply/divide) and better validation/pagination on history.
* Introduce Alembic migrations for schema evolution.
* Wire up real auth (JWT/cookies) and protect BREAD routes.
* Expand E2E to cover error states and delete/undo.

### Final status

All tests pass locally (unit, integration, and E2E). Coverage sits around \~73% in my last run. The app runs with `docker compose up` and publishes successfully to Docker Hub.
----
## Commit & branch strategy (suggested)

* Work on short‑lived branches: `feat/…`, `fix/…`, `test/…`.
* Make small, focused commits (one logical change per commit).
* Suggested messages: `feat(ui): add details page`, `test(e2e): robust edit/save selectors`.
* Open a PR early; let CI validate tests and the Docker image build.
----

## Documentation & Evidence

screenshots+notes document to the repo and link it here.

* **DOCX:** [BREAD & UI Test Evidence (DOCX)](docs/BREAD-UI-Tests.docx)

