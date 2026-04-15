VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

.PHONY: venv install dev run worker test create_db create_test_db drop_db migrate migrate-create rollback seed setup_db run_create_invoices_job lint

venv:
	python -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install ".[dev]"

install:
	$(PIP) install .

dev:
	$(PIP) install ".[dev]"

run:
	$(VENV)/bin/flask --app app.flask_app:create_app run --reload

worker:
	$(PYTHON) -m huey.bin.huey_consumer app.huey_app.huey

test: create_test_db
	$(VENV)/bin/pytest -v --cov=app --cov-report=term-missing

create_db:
	$(PYTHON) -m app.cli.create_db

create_test_db:
	$(PYTHON) -m app.cli.create_test_db

drop_db:
	$(PYTHON) -m app.cli.drop_db

migrate:
	$(PYTHON) -m app.cli.migrate

migrate-create:
	$(VENV)/bin/pw_migrate create --auto --auto-source app.models --database $(DATABASE_URL) --directory migrations $(name)

rollback:
	$(VENV)/bin/pw_migrate rollback --database $(DATABASE_URL) --directory migrations

seed:
	$(PYTHON) -m app.cli.seed

setup_db:
	$(PYTHON) -m app.cli.setup_db

run_create_invoices_job:
	$(PYTHON) -m app.cli.run_create_invoices_job

lint:
	$(VENV)/bin/ruff check app tests
