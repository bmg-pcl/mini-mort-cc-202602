# Drawing Analyzer

AI-powered technical drawing analysis using a **convolutional window approach**. This tool extracts quantities, measurements, notes, and callouts from construction and engineering drawings (PDFs) with high precision and traceability.

## The Method: Convolutional Window Analysis

Drawing Analyzer doesn't just look at a drawing as a single image. Construction drawings are often extremely high-resolution and dense with information that an LLM might miss in a single pass. 

Our core methodology uses a **Convolutional Window Approach**:
1. **Multi-Scale PDF Extraction**: We extract both text/vector elements and high-resolution images.
2. **Contextual Classification**: A global view of the drawing (thumbnail) is analyzed first to identify the drawing type (e.g., P&ID, Structural Plan) and discipline.
3. **Skill Routing**: Based on the classification, the system selects a specialized "Skill" — a curated set of prompts and domain knowledge.
4. **Sliding Window Analysis**: The drawing is divided into overlapping "kernels" (windows). Each window is analyzed by the AI, which is provided with:
    - The high-res window crop.
    - Nearby text/vector context.
    - The global thumbnail for orientation.
5. **Deduplication**: Detections from overlapping windows are merged using smart geometric deduplication (Intersection over Union).

This approach ensures that even small labels on large E-size drawings are captured accurately.

## Features

- **PDF Processing**: Extract images, text, and vector elements from technical drawings
- **Drawing Classification**: Automatically classify drawing type (P&ID, SLD, plan, section, etc.) and discipline
- **Convolutional Analysis**: Sliding window approach for comprehensive coverage and small object detection
- **Skills-Based Analysis**: Specialized prompts for architectural, structural, mechanical, and more
- **Quantity Takeoff**: Extract quantities, measurements, notes, and callouts
- **Deduplication**: Smart handling of overlapping analysis windows
- **Multiple Outputs**: JSON, CSV, and Excel formats with formatting
- **Web Interface**: Interactive visualization with real-time kernel tracking
- **Caching**: Avoid re-analyzing identical regions to save on API costs
- **Custom Skills**: Define your own analysis prompts via Markdown/YAML/JSON

---

## Technical Details

### Architecture

The system is built as a modular pipeline:
- `src/core/`: Data models and AI client abstractions.
- `src/extraction/`: PDF to image and metadata extraction logic.
- `src/convolution/`: The sliding window engine and deduplication logic.
- `src/skills/`: The domain knowledge library (prompts and schemas).
- `src/api/`: Simple Flask backend for processing requests.
- `src/web/`: A single-file, local-first web interface.

### Installation & Prerequisites

- Python 3.10+
- **Poppler**: Required for PDF rendering (`pdf2image`).
    - **Windows**: `choco install poppler` or [manual download](https://github.com/oschwartz10612/poppler-windows/releases).
    - **Linux**: `sudo apt-get install poppler-utils`.
    - **macOS**: `brew install poppler`.

```bash
git clone <repository-url>
cd drawing-analyzer
pip install -e .
```

### API Configuration

Drawing Analyzer supports any OpenAI-compatible endpoint. This can be configured via environment variables or directly in the Web UI:

- **OpenAI**: `export OPENAI_API_KEY="sk-..."`
- **Anthropic**: `export ANTHROPIC_API_KEY="sk-ant-..."`
- **Custom Endpoints**: Use `OPENAI_BASE_URL` to point to Azure, Local LLMs (Ollama), or other providers.

### CLI Usage

```bash
# Analyze a drawing
drawing-analyzer analyze drawing.pdf --output result.json

# Start the web interface
drawing-analyzer serve --port 5000
```

### Advanced Customization: Skills

Skills are defined in `config/skills/`. You can now use **Markdown files with YAML frontmatter** to define new skills. The body of the markdown file becomes the analysis prompt:

```markdown
---
name: my_new_skill
disciplines: [mechanical]
capabilities: [quantity_takeoff]
priority: 25
---
Analyze this mechanical drawing for...
```

---

## License

MIT
