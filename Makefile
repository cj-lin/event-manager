all: install format test dist
clean: clean-build clean-pyc clean-test

install: clean
	poetry install

format:
	poetry run black .
	poetry run isort .

lint:
	poetry run flake8 --max-line-length 88

mypy:
	poetry run mypy . --ignore-missing-imports

test:
	poetry run pytest --cov=event_manager

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
	poetry build
	poetry run pip download -d ./dist/ .

.PHONY: all clean
