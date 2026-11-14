# POLIS development commands
# Requires Python 3.12+, Node.js 20+/22, and npm.

.PHONY: help setup backend-install frontend-install dev-backend dev-frontend test test-backend test-frontend e2e build migrate docker-up docker-down

help:
	@echo "POLIS — common commands"
	@echo "  make setup            Create Python venv, install backend + frontend deps"
	@echo "  make dev-backend      Run FastAPI on http://127.0.0.1:8000"
	@echo "  make dev-frontend     Run Next.js on http://127.0.0.1:3000"
	@echo "  make test             Run backend and frontend test suites"
	@echo "  make e2e              Run Playwright user-journey tests (servers auto-start)"
	@echo "  make build            Build the production frontend"
	@echo "  make migrate          Apply Alembic migrations"
	@echo "  make docker-up        Build and start PostgreSQL + API + web"

setup: backend-install frontend-install

backend-install:
	python3 -m venv .venv
	.venv/bin/pip install -r backend/requirements-dev.txt

frontend-install:
	cd frontend && npm install

dev-backend:
	cd backend && ../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	cd backend && ../.venv/bin/python -m pytest

test-frontend:
	cd frontend && npm test

e2e:
	cd frontend && npx playwright install chromium && npm run e2e

build:
	cd frontend && npm run build

migrate:
	cd backend && ../.venv/bin/alembic upgrade head

docker-up:
	docker compose up --build

docker-down:
	docker compose down
