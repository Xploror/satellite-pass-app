PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
VENV ?= .venv
PYTHON_VENV := $(VENV)/bin/python
ARGS ?=

.PHONY: install test run docker-build docker-run clean

install:
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt

test:
	. $(VENV)/bin/activate && pytest -q

run:
	. $(VENV)/bin/activate && $(PYTHON) main.py $(ARGS)

docker-build:
	docker build -t satellite-pass-app .

docker-test:
    docker build -t satellite-pass-app .
    docker run --rm -it satellite-pass-app pytest -q

docker-run:
	docker run --rm -it satellite-pass-app

clean:
	rm -rf $(VENV) .pytest_cache tests/__pycache__ lib/__pycache__
