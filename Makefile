.PHONY: install dev backend frontend test test-backend test-frontend lint lint-backend lint-frontend typecheck preflight check clean

PYTHON ?= python3
VENV ?= $(CURDIR)/.venv
PIP=$(VENV)/bin/pip
PY=$(VENV)/bin/python

install: install-backend install-frontend

install-backend:
	[ -d $(VENV) ] || $(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip wheel
	$(PIP) install -e "backend[dev]"

install-frontend:
	cd frontend && npm install

dev:
	$(MAKE) -j 2 backend frontend

backend:
	$(PY) -m uvicorn app.main:app --reload --app-dir backend --port 8000

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

preflight:
	python3 scripts/preflight.py

check: preflight test

test-backend:
	cd backend && $(PY) -m pytest -q

test-frontend:
	cd frontend && npm run test -- --run

typecheck:
	cd frontend && npm run typecheck

lint: lint-backend lint-frontend

lint-backend:
	cd backend && $(PY) -m ruff check app && $(PY) -m mypy app

lint-frontend:
	cd frontend && npm run lint

clean:
	rm -rf $(VENV) frontend/node_modules data
