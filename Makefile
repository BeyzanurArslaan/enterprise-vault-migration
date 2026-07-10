.PHONY: install lint format typecheck test check coverage docker docs clean

install:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

lint:
	ruff check .

format:
	black .
	ruff format .

typecheck:
	mypy src tests

test:
	pytest

check:
	ruff check .
	black --check .
	mypy src tests
	pytest

coverage:
	pytest --cov=src --cov-report=term-missing

docker:
	docker compose up --build

docs:
	@echo "Documentation is maintained in docs/ and docs/adr/."

clean:
	find . -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.mypy_cache' -o -name '.ruff_cache' \) -prune -exec rm -rf {} +
