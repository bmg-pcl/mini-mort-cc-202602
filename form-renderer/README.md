# Form Renderer

Renders [survey.js](https://surveyjs.io/) form definitions as:

- **Streamlit web app** — native web controls + in-browser WebGPU LLM chat
- **CLI** — terminal-based form filling with chat mode
- **FastAPI backend** — receives and stores form submissions

## Quick Start

```bash
cd form-renderer
make install   # install dependencies
make test      # run tests
make api       # start API on :8000
make web       # start Streamlit on :8501 (separate terminal)
make cli-chat  # interactive CLI chat mode
```

## Project Structure

```
form-renderer/
├── api/server.py          # FastAPI submission backend
├── cli/chat.py            # CLI form renderer + chat mode
├── web/app.py             # Streamlit app (form + WebGPU chat)
├── forms/
│   ├── __init__.py        # Form loading/validation utilities
│   └── sample_survey.json # Example survey.js form
├── tests/                 # pytest test suite
├── Makefile               # Setup, test, run, deploy targets
├── Dockerfile             # Container deployment
└── requirements.txt
```

## Usage

### Save form responses as JSON

```bash
python cli/chat.py --form forms/sample_survey.json --save output.json
```

### Submit to API

```bash
# Terminal 1: start the API
make api

# Terminal 2: fill form and submit
python cli/chat.py --chat --api-url http://localhost:8000 --submit
```

### Web app

```bash
make web
# Open http://localhost:8501
# Use sidebar to switch between Form mode and WebGPU Chat mode
```
