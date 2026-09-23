.PHONY: setup run test smoke

PYTHON ?= python3
VENV := .venv
PY := $(VENV)/bin/python

setup:
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

run:
	$(PY) -m uvicorn app.main:app --port 8000

test:
	$(PY) -m pytest -q

smoke:
	$(PY) scripts/smoke.py

.PHONY: demo eval

demo:
	$(PY) scripts/demo.py

eval:
	$(PY) scripts/eval.py
