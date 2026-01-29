# Drawing Analyzer

AI-powered technical drawing analysis using a convolutional window approach.

## Features

- **PDF Processing**: Extract images, text, and vector elements from technical drawings
- **Drawing Classification**: Automatically classify drawing type (P&ID, SLD, plan, section, etc.) and discipline (structural, electrical, mechanical, etc.)
- **Convolutional Analysis**: Analyze drawings using a sliding window approach for comprehensive coverage
- **Skills-Based Analysis**: Different analysis skills for different drawing types
- **Quantity Takeoff**: Extract quantities, measurements, notes, and callouts
- **Deduplication**: Smart handling of overlapping analysis windows
- **Multiple Outputs**: JSON, CSV, and Excel-compatible formats
- **Web Interface**: Interactive visualization of the analysis process

## Installation

```bash
pip install -e .
```

Or install dependencies directly:

```bash
pip install -r requirements.txt
```

## Usage

### CLI

```bash
# Analyze a drawing
drawing-analyzer analyze drawing.pdf --provider openai --output result.json

# Classify a drawing
drawing-analyzer classify drawing.pdf

# Extract elements only
drawing-analyzer extract drawing.pdf --page 1

# List available skills
drawing-analyzer skills

# Start web server
drawing-analyzer serve --port 5000
```

### Python API

```python
from src.analyzer import create_analyzer

# Create analyzer
analyzer = create_analyzer(
    provider="openai",  # or "anthropic"
    api_key="sk-...",   # or use OPENAI_API_KEY env var
)

# Analyze a drawing
result = analyzer.analyze("drawing.pdf")

# Access results
print(f"Drawing type: {result.classification.drawing_type}")
print(f"Quantities found: {len(result.quantities)}")

for q in result.quantities:
    print(f"  {q.description}: {q.quantity} {q.unit.value}")

# Export to table format
table = result.to_table_format()
```

### Web API

Start the server:

```bash
drawing-analyzer serve
```

Then access:
- Web UI: http://localhost:5000/
- API: http://localhost:5000/api/

API Endpoints:
- `POST /api/analyze` - Upload and analyze a PDF
- `GET /api/analysis/{id}` - Get analysis results
- `GET /api/analysis/{id}/progress` - SSE stream of analysis progress
- `POST /api/classify` - Quick classification without full analysis
- `GET /api/skills` - List available analysis skills

## Configuration

Environment variables:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

## Architecture

```
drawing-analyzer/
├── src/
│   ├── core/           # Core models and schemas
│   │   ├── models.py   # Data models (APIConfig, ImageData, etc.)
│   │   └── schema.py   # Output schema (QuantityItem, etc.)
│   ├── extraction/     # PDF extraction
│   │   ├── pdf_extractor.py
│   │   └── element_extractor.py
│   ├── classification/ # Drawing classification
│   │   └── classifier.py
│   ├── skills/         # Analysis skills library
│   │   ├── skill_registry.py
│   │   └── prompts.py
│   ├── convolution/    # Convolutional analysis
│   │   ├── analyzer.py
│   │   └── deduplication.py
│   ├── api/           # Web API
│   │   └── app.py
│   ├── web/           # Static web interface
│   │   └── index.html
│   ├── analyzer.py    # Main orchestrator
│   └── cli.py         # CLI interface
└── tests/
```

## How It Works

1. **PDF Extraction**: Extract text blocks and vector drawings from the PDF, create a thumbnail
2. **Classification**: Send thumbnail to AI to classify drawing type and discipline
3. **Skill Selection**: Select the appropriate analysis skill based on classification
4. **Convolutional Analysis**:
   - Divide drawing into overlapping kernel windows
   - For each kernel, gather nearby elements as context
   - Send kernel image + thumbnail + context to AI for analysis
   - If complexity is high, subdivide kernel and re-analyze
5. **Deduplication**: Remove duplicate detections from overlapping windows
6. **Output**: Structured JSON with quantities, measurements, notes, callouts

## Output Schema

The output schema is designed for:
- Multi-segment categorization (CSI MasterFormat, UniFormat)
- Traceability to source documents (bounding boxes, page numbers)
- Verification flags for manual review
- Excel/web app compatibility

See `src/core/schema.py` for the complete schema definition.

## License

MIT
