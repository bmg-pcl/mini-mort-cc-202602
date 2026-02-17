.PHONY: install test lint api web cli clean docker-build docker-run

PYTHON ?= python3
PIP ?= pip
PORT_API ?= 8000
PORT_WEB ?= 8501

# ── Setup ──────────────────────────────────────────────────────────
install:
	$(PIP) install -r requirements.txt

venv:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@echo "Activate with: source .venv/bin/activate"

# ── Testing ────────────────────────────────────────────────────────
test:
	$(PYTHON) -m pytest tests/ -v

test-cov:
	$(PYTHON) -m pytest tests/ -v --cov=. --cov-report=term-missing

# ── Lint ───────────────────────────────────────────────────────────
lint:
	$(PYTHON) -m py_compile api/server.py
	$(PYTHON) -m py_compile cli/chat.py
	$(PYTHON) -m py_compile web/app.py
	$(PYTHON) -m py_compile forms/__init__.py
	@echo "All files compile OK"

# ── Run Services ───────────────────────────────────────────────────
api:
	uvicorn api.server:app --host 0.0.0.0 --port $(PORT_API) --reload

web:
	streamlit run web/app.py --server.port $(PORT_WEB)

cli:
	$(PYTHON) cli/chat.py

cli-chat:
	$(PYTHON) cli/chat.py --chat --api-url http://localhost:$(PORT_API)

# ── Deploy (Docker) ───────────────────────────────────────────────
docker-build:
	docker build -t form-renderer .

docker-run:
	docker run --rm -p $(PORT_API):$(PORT_API) -p $(PORT_WEB):$(PORT_WEB) form-renderer

# ── Cleanup ────────────────────────────────────────────────────────
clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache submissions/*.json
	rm -rf .venv
