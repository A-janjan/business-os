.PHONY: help install dev api web test test-api test-web migrate seed docker-up docker-down

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## install all dependencies
	pip install -r apps/api/requirements.txt alembic
	cd apps/web && npm install

dev: ## run api + web together (two terminals)
	@echo "Run: make api   in one terminal"
	@echo "Run: make web   in another"

api: ## start the backend on :8000
	cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

web: ## start the frontend on :5173
	cd apps/web && npm run dev

migrate: ## run database migrations
	cd apps/api && alembic upgrade head

seed: ## seed the knowledge vault structure
	python3 infrastructure/scripts/seed_vault.py

test: test-api test-web ## run all tests

test-api: ## backend tests
	cd apps/api && python3 -m pytest tests/ -q

test-web: ## frontend tests
	cd apps/web && npx vitest run

docker-up: ## start the full stack (requires Docker)
	docker compose up --build

docker-down: ## stop the stack
	docker compose down
