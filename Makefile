COMPOSE := docker compose -f infra/docker-compose.dev.yml
# Headless Chrome already downloaded by Playwright (override with PLAYWRIGHT_CHROME_PATH=...).
PLAYWRIGHT_CHROME_PATH ?= $(lastword $(wildcard $(HOME)/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell))
RUN_API := $(COMPOSE) run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test api
EXEC_FRONT := $(COMPOSE) run --rm --no-deps frontend

.PHONY: help env dev up down logs ps migrate makemigrations seed shell test test-back test-front e2e lint format typecheck graph

help: ## List available commands
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-16s %s\n", $$1, $$2}'

env:
	@test -f .env || (cp .env.example .env && echo ".env created from .env.example")

dev: env ## Build and start the whole platform on http://localhost:8090
	$(COMPOSE) up --build -d
	@echo "Wedivo: http://localhost:8090  ·  API docs: http://localhost:8090/api/docs  ·  MinIO: http://localhost:9101"

up: env ## Start without rebuilding
	$(COMPOSE) up -d

down: ## Stop every service
	$(COMPOSE) down

logs: ## Follow logs
	$(COMPOSE) logs -f --tail=100

ps: ## Service status
	$(COMPOSE) ps

migrate: ## Apply database migrations
	$(COMPOSE) exec api python manage.py migrate

makemigrations: ## Create migrations
	$(COMPOSE) exec api python manage.py makemigrations

seed: ## Load demo data (Maison Élégance Events, 4 demo accounts)
	$(COMPOSE) exec api python manage.py seed_demo

demo-reset: ## Rebuild the dev database with fresh demo data (a dump is saved in backups/ first)
	mkdir -p backups
	$(COMPOSE) exec -T db pg_dump -U postgres -Fc wedivo > backups/db-avant-demo-reset-$$(date +%Y%m%d-%H%M%S).dump
	$(COMPOSE) stop api worker beat
	$(COMPOSE) exec -T db dropdb -U postgres --if-exists wedivo
	$(COMPOSE) exec -T db createdb -U postgres -O wedivo wedivo
	$(COMPOSE) exec -T redis redis-cli FLUSHALL
	$(COMPOSE) run --rm --no-deps api python manage.py migrate
	$(COMPOSE) run --rm --no-deps api python manage.py seed_demo
	$(COMPOSE) run --rm --no-deps api python manage.py seed_e2e
	$(COMPOSE) start api worker beat

shell: ## Django shell
	$(COMPOSE) exec api python manage.py shell

test: test-back test-front ## Run every test suite

test-back:
	$(COMPOSE) up -d db redis
	$(RUN_API) pytest

test-front:
	$(EXEC_FRONT) npm test

e2e: ## Browser journeys (Playwright, local Chrome) against the running platform
	$(COMPOSE) exec -T api python manage.py seed_e2e
	cd frontend && PLAYWRIGHT_CHROME_PATH="$(PLAYWRIGHT_CHROME_PATH)" npx playwright test

lint: ## Lint backend and frontend
	$(RUN_API) sh -c "ruff check . && black --check . && mypy ."
	$(EXEC_FRONT) sh -c "npm run lint && npm run typecheck"

format: ## Auto-format backend and frontend
	$(RUN_API) sh -c "ruff check --fix . && black ."
	$(EXEC_FRONT) npm run format

graph: ## Update the code knowledge graph (graphify, local AST, no LLM)
	graphify update .
