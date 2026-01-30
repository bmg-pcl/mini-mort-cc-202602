# Drawing Analyzer

AI-powered technical drawing analysis using a convolutional window approach. Extracts quantities, measurements, notes, and callouts from construction/engineering drawings.

## Features

- **PDF Processing**: Extract images, text, and vector elements from technical drawings
- **Drawing Classification**: Automatically classify drawing type (P&ID, SLD, plan, section, etc.) and discipline (structural, electrical, mechanical, etc.)
- **Convolutional Analysis**: Analyze drawings using a sliding window approach for comprehensive coverage
- **Skills-Based Analysis**: Specialized prompts for different drawing types
- **Quantity Takeoff**: Extract quantities, measurements, notes, and callouts
- **Deduplication**: Smart handling of overlapping analysis windows
- **Multiple Outputs**: JSON, CSV, and Excel formats with formatting
- **Web Interface**: Interactive visualization with PDF preview
- **Caching**: Avoid re-analyzing identical regions
- **Custom Skills**: Define your own analysis prompts via YAML/JSON
- **Drawing Comparison**: Compare quantities between drawing revisions

---

## Table of Contents

1. [Installation](#installation)
   - [Windows](#windows-setup)
   - [Linux/macOS](#linuxmacos-setup)
   - [Docker](#docker-setup)
2. [API Configuration](#api-configuration)
   - [OpenAI](#openai)
   - [Azure OpenAI](#azure-openai)
   - [Anthropic Claude](#anthropic-claude)
   - [GitHub Copilot](#github-copilot)
   - [Databricks](#databricks)
   - [Other OpenAI-Compatible Endpoints](#other-openai-compatible-endpoints)
3. [Usage](#usage)
4. [Deployment](#deployment)
5. [Architecture](#architecture)

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Poppler (for PDF rendering) - see platform-specific instructions below

### Windows Setup

1. **Install Python 3.10+** from [python.org](https://www.python.org/downloads/)

2. **Install Poppler** (required for pdf2image):
   ```powershell
   # Using Chocolatey
   choco install poppler

   # Or download manually from:
   # https://github.com/oschwartz10612/poppler-windows/releases
   # Extract to C:\Program Files\poppler and add bin folder to PATH
   ```

3. **Clone and install**:
   ```powershell
   git clone <repository-url>
   cd drawing-analyzer

   # Create virtual environment
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Install dependencies
   pip install -r requirements.txt

   # Or install as package
   pip install -e .
   ```

4. **Set environment variables**:
   ```powershell
   # PowerShell
   $env:OPENAI_API_KEY = "sk-..."

   # Or create .env file
   copy .env.example .env
   # Edit .env with your keys
   ```

### Linux/macOS Setup

1. **Install system dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install -y python3.10 python3.10-venv python3-pip poppler-utils

   # macOS
   brew install python@3.10 poppler

   # RHEL/CentOS/Fedora
   sudo dnf install python3.10 poppler-utils
   ```

2. **Clone and install**:
   ```bash
   git clone <repository-url>
   cd drawing-analyzer

   # Create virtual environment
   python3.10 -m venv venv
   source venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt

   # Or install as package
   pip install -e .
   ```

3. **Set environment variables**:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export OPENAI_API_KEY="sk-..."

   # Or create .env file
   cp .env.example .env
   # Edit .env with your keys
   ```

### Docker Setup

```bash
# Build the image
docker build -t drawing-analyzer .

# Run with environment variables
docker run -p 5000:5000 \
  -e OPENAI_API_KEY="sk-..." \
  drawing-analyzer

# Run with .env file
docker run -p 5000:5000 \
  --env-file .env \
  drawing-analyzer

# Mount a volume for persistent cache
docker run -p 5000:5000 \
  -e OPENAI_API_KEY="sk-..." \
  -v drawing-cache:/app/cache \
  drawing-analyzer
```

---

## API Configuration

### OpenAI

The default provider. Works with GPT-4o and GPT-4 Vision models.

```bash
# Environment variables
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o"  # or gpt-4-vision-preview
```

```python
from src.analyzer import create_analyzer

analyzer = create_analyzer(
    provider="openai",
    api_key="sk-...",
    model="gpt-4o",
)
```

### Azure OpenAI

Use Azure-hosted OpenAI models by setting the base URL:

```bash
export OPENAI_API_KEY="your-azure-api-key"
export OPENAI_BASE_URL="https://your-resource.openai.azure.com/openai/deployments/your-deployment"
export OPENAI_MODEL="gpt-4o"  # Your deployment name
```

```python
from src.core.models import APIConfig, APIProvider

config = APIConfig(
    provider=APIProvider.OPENAI,
    api_key="your-azure-api-key",
    base_url="https://your-resource.openai.azure.com/openai/deployments/your-deployment",
    model="gpt-4o",
)
```

### Anthropic Claude

Supports Claude 3.5 Sonnet and Claude 3 Opus with vision capabilities.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_MODEL="claude-sonnet-4-20250514"
```

```python
analyzer = create_analyzer(
    provider="anthropic",
    api_key="sk-ant-...",
    model="claude-sonnet-4-20250514",
)
```

### GitHub Copilot

Use Copilot's API through an OpenAI-compatible endpoint:

```bash
# Get your Copilot token (requires GitHub Copilot subscription)
export OPENAI_API_KEY="ghu_..."  # Your GitHub token
export OPENAI_BASE_URL="https://api.githubcopilot.com"
export OPENAI_MODEL="gpt-4o"
```

**Note**: GitHub Copilot API access may require enterprise subscription and specific permissions.

### Databricks

Use Databricks Foundation Model APIs or external model endpoints:

```bash
# For Databricks-hosted models
export OPENAI_API_KEY="your-databricks-token"
export OPENAI_BASE_URL="https://your-workspace.cloud.databricks.com/serving-endpoints/your-endpoint/invocations"
export OPENAI_MODEL="databricks-meta-llama-3-1-70b-instruct"

# For external models via Databricks
export OPENAI_BASE_URL="https://your-workspace.cloud.databricks.com/serving-endpoints/your-openai-endpoint/invocations"
```

```python
from src.core.models import APIConfig, APIProvider

config = APIConfig(
    provider=APIProvider.OPENAI,
    api_key="dapi...",  # Databricks personal access token
    base_url="https://your-workspace.cloud.databricks.com/serving-endpoints/gpt4-endpoint/invocations",
    model="gpt-4o",
)
```

### Other OpenAI-Compatible Endpoints

Any OpenAI-compatible API can be used by setting the base URL:

```bash
# Local LLM (e.g., Ollama, LM Studio, vLLM)
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_API_KEY="not-needed"  # Some local servers don't require keys
export OPENAI_MODEL="llava"  # Must support vision

# Together.ai
export OPENAI_BASE_URL="https://api.together.xyz/v1"
export OPENAI_API_KEY="your-together-key"
export OPENAI_MODEL="meta-llama/Llama-Vision-Free"

# Groq
export OPENAI_BASE_URL="https://api.groq.com/openai/v1"
export OPENAI_API_KEY="your-groq-key"
export OPENAI_MODEL="llava-v1.5-7b-4096-preview"

# Fireworks.ai
export OPENAI_BASE_URL="https://api.fireworks.ai/inference/v1"
export OPENAI_API_KEY="your-fireworks-key"
export OPENAI_MODEL="accounts/fireworks/models/llava-v1.6-34b"

# Perplexity
export OPENAI_BASE_URL="https://api.perplexity.ai"
export OPENAI_API_KEY="your-perplexity-key"
export OPENAI_MODEL="llava-v1.6-34b"
```

**Important**: The model must support vision/image inputs for drawing analysis to work.

---

## Usage

### CLI

```bash
# Analyze a drawing
drawing-analyzer analyze drawing.pdf --provider openai --output result.json

# Analyze with specific model
drawing-analyzer analyze drawing.pdf --provider anthropic --model claude-sonnet-4-20250514

# Classify a drawing (quick, no full analysis)
drawing-analyzer classify drawing.pdf

# Extract elements only (no API calls)
drawing-analyzer extract drawing.pdf --page 1

# List available analysis skills
drawing-analyzer skills

# Start web server
drawing-analyzer serve --port 5000 --host 0.0.0.0
```

### Python API

```python
from src.analyzer import create_analyzer

# Create analyzer with OpenAI
analyzer = create_analyzer(
    provider="openai",
    api_key="sk-...",
    model="gpt-4o",
)

# Analyze a drawing
result = analyzer.analyze("drawing.pdf")

# Access results
print(f"Drawing type: {result.classification.drawing_type}")
print(f"Discipline: {result.classification.discipline}")
print(f"Quantities found: {len(result.quantities)}")

for q in result.quantities:
    print(f"  {q.description}: {q.quantity} {q.unit.value}")

# Export to Excel
from src.core.excel_export import export_to_excel
excel_bytes = export_to_excel(result)
with open("result.xlsx", "wb") as f:
    f.write(excel_bytes)

# Export to table format (for pandas/CSV)
table = result.to_table_format()
```

### Web API

Start the server:

```bash
drawing-analyzer serve --port 5000
```

Access:
- **Web UI**: http://localhost:5000/
- **API Base**: http://localhost:5000/api/

**Endpoints**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Upload and analyze a PDF |
| GET | `/api/analysis/{id}` | Get analysis results |
| GET | `/api/analysis/{id}/progress` | SSE stream of progress |
| GET | `/api/analysis/{id}/excel` | Download Excel report |
| POST | `/api/classify` | Quick classification only |
| GET | `/api/skills` | List available skills |
| GET | `/api/cache/stats` | Cache statistics |
| GET | `/api/health` | Health check |

**Example: Upload and analyze**:

```bash
curl -X POST http://localhost:5000/api/analyze \
  -F "file=@drawing.pdf" \
  -F "provider=openai" \
  -F "api_key=sk-..."
```

### Custom Skills

Create custom analysis skills in YAML or JSON:

```yaml
# my_skills/hvac_skill.yaml
name: custom_hvac
drawing_types:
  - plan
  - layout
  - mechanical
disciplines:
  - HVAC
  - mechanical
description: Custom skill for HVAC equipment analysis
capabilities:
  - quantity_takeoff
  - measurement
  - notes_extraction
priority: 20
analysis_prompt: |
  Analyze this HVAC drawing region.

  Focus on:
  1. EQUIPMENT: AHUs, FCUs, VAV boxes, fans, pumps
  2. DUCTWORK: Sizes, types, insulation requirements
  3. DIFFUSERS: Types and CFM ratings
  4. CONTROLS: Thermostats, sensors, dampers

  Respond with JSON including quantities and specifications.
```

Load custom skills:

```python
from src.skills import register_custom_skills, get_registry

registry = get_registry()
register_custom_skills(registry, "my_skills/")  # Load from directory
```

---

## Deployment

### Docker Compose (Local)

```yaml
# docker-compose.yml
version: '3.8'
services:
  drawing-analyzer:
    build: .
    ports:
      - "5000:5000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - cache-data:/app/cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  cache-data:
```

```bash
docker-compose up -d
```

### Fly.io Deployment

1. **Install Fly CLI**:
   ```bash
   # macOS
   brew install flyctl

   # Linux
   curl -L https://fly.io/install.sh | sh

   # Windows
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

2. **Login and initialize**:
   ```bash
   fly auth login
   fly launch --name drawing-analyzer --region ord
   ```

3. **Create `fly.toml`** (auto-generated, but customize):
   ```toml
   app = "drawing-analyzer"
   primary_region = "ord"

   [build]
     dockerfile = "Dockerfile"

   [env]
     PORT = "5000"

   [http_service]
     internal_port = 5000
     force_https = true
     auto_stop_machines = true
     auto_start_machines = true
     min_machines_running = 0

   [[vm]]
     cpu_kind = "shared"
     cpus = 1
     memory_mb = 512
   ```

4. **Set secrets**:
   ```bash
   fly secrets set OPENAI_API_KEY="sk-..."
   # Or for Anthropic
   fly secrets set ANTHROPIC_API_KEY="sk-ant-..."
   ```

5. **Deploy**:
   ```bash
   fly deploy
   ```

6. **View logs**:
   ```bash
   fly logs
   ```

7. **Open app**:
   ```bash
   fly open
   ```

### Railway Deployment

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Railway auto-detects the Dockerfile

### Render Deployment

1. Create a new Web Service on Render
2. Connect your repository
3. Set environment variables
4. Deploy using the Dockerfile

---

## Architecture

```
drawing-analyzer/
├── src/
│   ├── core/                 # Core models and schemas
│   │   ├── models.py         # Data models (APIConfig, ImageData, etc.)
│   │   ├── schema.py         # Output schema (QuantityItem, etc.)
│   │   ├── ai_client.py      # AI provider abstraction
│   │   ├── cache.py          # Caching layer
│   │   └── excel_export.py   # Excel export with formatting
│   ├── extraction/           # PDF extraction
│   │   ├── pdf_extractor.py  # PDF to images/text
│   │   └── element_extractor.py
│   ├── classification/       # Drawing classification
│   │   └── classifier.py
│   ├── skills/               # Analysis skills library
│   │   ├── skill_registry.py # Built-in skills
│   │   ├── prompts.py        # Skill utilities
│   │   └── custom_skills.py  # YAML/JSON skill loader
│   ├── convolution/          # Convolutional analysis
│   │   ├── analyzer.py       # Sliding window analyzer
│   │   └── deduplication.py  # IoU-based dedup
│   ├── api/                  # Web API
│   │   └── app.py            # Flask application
│   ├── web/                  # Static web interface
│   │   └── index.html        # PDF.js + Pico.css UI
│   ├── analyzer.py           # Main orchestrator
│   └── cli.py                # CLI interface
├── tests/                    # Test suite
├── config/                   # Configuration files
│   └── skills/               # Custom skill definitions
├── Dockerfile
├── docker-compose.yml
├── fly.toml
├── requirements.txt
└── pyproject.toml
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

## Available Skills

| Skill | Drawing Types | Disciplines | Description |
|-------|---------------|-------------|-------------|
| `generic_technical` | All | All | Default fallback for any drawing |
| `structural_framing` | framing_plan, plan | structural | Steel/concrete framing plans |
| `structural_detail` | detail, section | structural | Connection details, sections |
| `architectural_plan` | floor_plan, plan | architectural | Floor plans, layouts |
| `piping_isometric` | isometric | piping, mechanical | Piping isometrics |
| `pid_diagram` | P&ID, schematic | piping, process | P&ID diagrams |
| `electrical_sld` | SLD, schematic | electrical | Single line diagrams |
| `schedule_extraction` | schedule | all | Tabular schedules |
| `civil_site` | site_plan | civil | Site plans, grading |
| `mechanical_equipment` | plan, layout | mechanical | Equipment layouts |
| `fire_protection` | plan | fire_protection | Sprinkler plans |
| `plumbing_riser` | riser, isometric | plumbing | Plumbing risers |

## Output Schema

The output schema supports:
- Multi-segment categorization (CSI MasterFormat, UniFormat)
- Traceability to source documents (bounding boxes, page numbers)
- Verification flags for manual review
- Excel/web app compatibility

See `src/core/schema.py` for the complete schema definition.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Type checking
mypy src/

# Format code
black src/ tests/
ruff check src/ tests/
```

## License

MIT
