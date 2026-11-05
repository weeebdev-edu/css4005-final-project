.PHONY: venv test lint fmt build up down logs

venv:
	python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

fmt:
	.venv/bin/ruff format . && .venv/bin/ruff check --fix .

build:
	docker build -t campus-app:dev .

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f app
