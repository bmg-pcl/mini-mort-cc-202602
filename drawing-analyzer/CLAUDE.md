# Drawing Analyzer

## Commands
- **Install**: `pip install -e .`
- **Install Dev**: `pip install -e .[dev]`
- **Run**: `python -m src.cli` or using the `drawing-analyzer` script
- **Test**: `pytest`
- **Lint**: `ruff check .`
- **Format**: `black .`

## Configuration
- **Skills**: located in `config/skills/`. Supported formats: JSON, YAML, and Markdown.
- **Endpoint/API**: The web interface and configuration both allow the endpoint and API to be specified.

## Structure
- `src/`: Source code
- `config/`: Configuration files and skills definitions
- `tests/`: Unit and integration tests
