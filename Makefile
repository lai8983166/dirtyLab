.PHONY: install dev backend frontend test test-backend test-frontend lint lint-backend lint-frontend typecheck preflight check clean

install: install-backend install-frontend

install-backend:
	cd backend && uv sync

install-frontend:
	pnpm install --dir frontend

dev:
	$(MAKE) -j 2 backend frontend

backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:
	pnpm --dir frontend run dev

test: test-backend test-frontend

preflight:
	uv run --project backend python scripts/preflight.py

check: preflight test

test-backend:
	cd backend && uv run pytest -q

test-frontend:
	pnpm --dir frontend run test --run

typecheck:
	pnpm --dir frontend run typecheck

lint: lint-backend lint-frontend

lint-backend:
	cd backend && uv run ruff check app && uv run mypy app

lint-frontend:
	pnpm --dir frontend run lint

clean:
	rm -rf backend/.venv frontend/node_modules data
