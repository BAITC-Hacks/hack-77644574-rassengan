.PHONY: setup run test smoke

setup:
	python3 -m pip install -r requirements.txt

run:
	python3 -m uvicorn app.main:app --port 8000

test:
	python3 -m pytest -q

smoke:
	python scripts/smoke.py
