.PHONY: test lint run pre-commit install help

# Default target
help:
	@echo "Available targets:"
	@echo "  test       - Run tests with pytest"
	@echo "  lint       - Run ruff check for linting"
	@echo "  run        - Start the FastAPI server with reload"
	@echo "  pre-commit - Run pre-commit hooks on all files"
	@echo "  install    - Install dependencies with poetry"

test:
	poetry run pytest

lint:
	poetry run ruff check

lint-fix:
	poetry run ruff check --fix

run:
	poetry run python -m uvicorn app.main:app --reload

pre-commit:
	poetry run pre-commit run --all-files

install:
	poetry install
