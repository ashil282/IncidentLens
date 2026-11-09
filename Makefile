.PHONY: setup run test lint audit demo
setup:
	./scripts/dev-setup.sh
run:
	uvicorn incidentlens.main:app --reload
test:
	pytest -q
lint:
	ruff check .
audit:
	pip-audit
demo:
	python scripts/send_demo_events.py
