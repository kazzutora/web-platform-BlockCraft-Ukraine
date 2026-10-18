# Development commands. Recipes stay compatible with both sh and cmd.exe (make on Windows).
# Frontend commands run in the container; with the frontend on the host use FRONTEND_LOCAL=1,
# e.g. `make lint FRONTEND_LOCAL=1`.

COMPOSE := docker compose
BACK := $(COMPOSE) exec backend
MANAGE := $(BACK) uv run python manage.py

ifeq ($(FRONTEND_LOCAL),1)
FRONT := cd frontend &&
else
FRONT := $(COMPOSE) exec frontend
endif

# Must match .env, used by reset-db
POSTGRES_USER ?= blockcraft
POSTGRES_DB ?= blockcraft

.DEFAULT_GOAL := help

.PHONY: help up up-local down logs ps sh-back sh-front migrate makemigrations createsuperuser \
	test test-back test-front lint fmt typecheck api-types seed sync-mods reset-db

help:
	@echo up               - build and start everything, site at http://localhost:8080
	@echo up-local         - start everything except the frontend, then run pnpm dev in frontend/
	@echo down / logs / ps - stop / follow logs / list containers
	@echo sh-back, sh-front - shell in the backend / frontend container
	@echo migrate, makemigrations, createsuperuser
	@echo test, test-back, test-front
	@echo lint, fmt, typecheck
	@echo api-types        - regenerate API types: schema.d.ts and allauth.d.ts in frontend/src/lib/api
	@echo seed, sync-mods  - demo data / Modrinth sync
	@echo reset-db         - drop and recreate the database, then migrate

.env:
	$(file >$@,$(file <.env.example))
	@echo Created .env from .env.example

up: .env
	$(COMPOSE) up -d --build
	@echo BlockCraft is starting at http://localhost:8080

up-local: export FRONTEND_UPSTREAM = host.docker.internal:3000
up-local: .env
	$(COMPOSE) up -d --build db redis meili backend worker beat nginx
	@echo Backend is up. Now run in frontend/: pnpm install, then pnpm dev

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

sh-back:
	$(BACK) bash

sh-front:
	$(COMPOSE) exec frontend sh

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

createsuperuser:
	$(MANAGE) createsuperuser

test: test-back test-front

test-back:
	$(BACK) uv run pytest --cov

test-front:
	$(FRONT) pnpm test

lint:
	$(BACK) uv run ruff check .
	$(BACK) uv run ruff format --check .
	$(FRONT) pnpm lint
	$(FRONT) pnpm format:check

fmt:
	$(BACK) uv run ruff format .
	$(BACK) uv run ruff check --fix .
	$(FRONT) pnpm format

typecheck:
	$(FRONT) pnpm typecheck

api-types:
	$(COMPOSE) exec -T backend uv run python manage.py spectacular --validate --fail-on-warn > frontend/openapi.yaml
	$(COMPOSE) exec -T backend uv run python manage.py export_allauth_schema > frontend/allauth-openapi.json
	$(FRONT) pnpm api-types

seed:
	@echo make seed arrives in stage 9, task 9.4

sync-mods:
	@echo make sync-mods arrives in stage 3, task 3.3

reset-db:
	$(COMPOSE) stop backend worker beat
	$(COMPOSE) exec db dropdb -U $(POSTGRES_USER) --if-exists --force $(POSTGRES_DB)
	$(COMPOSE) exec db createdb -U $(POSTGRES_USER) $(POSTGRES_DB)
	$(COMPOSE) start backend worker beat
	@echo Database recreated, backend applies migrations on start
