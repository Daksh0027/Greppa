# Makefile for Greppa Backend Development

.PHONY: help install lint format test clean run migrate

help:
	@echo "Greppa Backend - Available Commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make lint          - Run Ruff linter"
	@echo "  make format        - Format code with Ruff"
	@echo "  make test          - Run pytest tests"
	@echo "  make clean         - Remove cache files"
	@echo "  make run           - Start development server"
	@echo "  make migrate       - Run database migrations"
	@echo "  make pre-commit    - Install pre-commit hooks"

install:
	pip install -r requirements.txt
	pip install pre-commit mypy

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

test:
	PYTHONPATH=. pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

run:
	PYTHONPATH=. python app/main.py

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Migration message: " msg; \
	PYTHONPATH=. alembic revision --autogenerate -m "$$msg"

pre-commit:
	pre-commit install
	@echo "Pre-commit hooks installed successfully!"

check-all: lint test
	@echo "All checks passed!"
