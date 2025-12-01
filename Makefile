all: install format test dist
clean: clean-build clean-pyc clean-test

install: clean
	uv sync --all-extras

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .

mypy:
	uv run mypy . --ignore-missing-imports

test:
	uv run pytest --cov=event_manager

clean-build:
	rm -rf dist/

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -rf .coverage .pytest_cache/

dist: clean
	uv build

.PHONY: all clean
