.PHONY: dev migrate test lint typecheck fmt clean seed

# ── Local dev ─────────────────────────────────────────────────────────────────
dev:
	docker compose up api worker web postgres redis

dev-build:
	docker compose build

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	docker compose run --rm migrate

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(msg)"

migrate-rollback:
	cd backend && alembic downgrade -1

# ── Backend ───────────────────────────────────────────────────────────────────
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

test:
	cd backend && pytest

test-safety:
	cd backend && pytest -m safety_critical -v

test-integration:
	cd backend && pytest -m integration -v

test-cov:
	cd backend && pytest --cov=beacon --cov-report=html

lint:
	cd backend && ruff check .

fmt:
	cd backend && ruff format .

typecheck:
	cd backend && mypy beacon/

# ── Frontend ──────────────────────────────────────────────────────────────────
fe-dev:
	cd frontend && npm run dev

fe-build:
	cd frontend && npm run build

fe-test:
	cd frontend && npm run test

fe-e2e:
	cd frontend && npm run test:e2e

# ── Seed data ─────────────────────────────────────────────────────────────────
seed:
	cd backend && python -m beacon.scripts.seed_dev_data

# ── Utilities ─────────────────────────────────────────────────────────────────
logs:
	docker compose logs -f api worker

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
