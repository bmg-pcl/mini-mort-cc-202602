"""
Flask Web API for Drawing Analyzer

Provides REST endpoints for:
- Uploading and analyzing PDFs
- Retrieving analysis results
- Viewing convolution progress
"""
import os
import uuid
import json
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

# Analysis storage (in-memory for simplicity)
analyses: dict[str, dict] = {}
analysis_progress: dict[str, list] = {}


def create_app(config: Optional[dict] = None) -> Flask:
    """Create and configure the Flask application"""
    app = Flask(__name__, static_folder="../web", static_url_path="")
    CORS(app)

    if config:
        app.config.update(config)

    # Ensure web folder exists
    web_folder = Path(__file__).parent.parent / "web"
    web_folder.mkdir(exist_ok=True)

    @app.route("/")
    def index():
        """Serve the web interface"""
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/health")
    def health():
        """Health check endpoint"""
        return jsonify({"status": "ok", "version": "0.1.0"})

    @app.route("/api/analyze", methods=["POST"])
    def analyze():
        """
        Analyze a PDF drawing.

        Accepts multipart/form-data with:
        - file: PDF file to analyze
        - provider: API provider (openai/anthropic)
        - model: Model to use (optional)
        - page: Specific page number (optional)
        """
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "File must be a PDF"}), 400

        # Get options
        provider = request.form.get("provider", "openai")
        model = request.form.get("model")
        page = request.form.get("page")
        api_key = request.form.get("api_key") or os.environ.get(
            "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        )

        if not api_key:
            return jsonify({"error": "No API key provided"}), 400

        # Generate analysis ID
        analysis_id = str(uuid.uuid4())[:8]

        # Save file temporarily
        temp_dir = tempfile.mkdtemp()
        pdf_path = Path(temp_dir) / file.filename
        file.save(pdf_path)

        # Initialize progress tracking
        analysis_progress[analysis_id] = []

        # Start analysis in background
        thread = threading.Thread(
            target=_run_analysis,
            args=(analysis_id, pdf_path, provider, api_key, model, page),
        )
        thread.start()

        return jsonify({
            "analysis_id": analysis_id,
            "status": "started",
            "message": "Analysis started. Poll /api/analysis/{id} for results.",
        })

    @app.route("/api/analysis/<analysis_id>")
    def get_analysis(analysis_id: str):
        """Get analysis results"""
        if analysis_id not in analyses:
            if analysis_id in analysis_progress:
                return jsonify({
                    "analysis_id": analysis_id,
                    "status": "in_progress",
                    "progress": analysis_progress[analysis_id],
                })
            return jsonify({"error": "Analysis not found"}), 404

        return jsonify(analyses[analysis_id])

    @app.route("/api/analysis/<analysis_id>/progress")
    def get_progress(analysis_id: str):
        """Get analysis progress (SSE stream)"""
        def generate():
            last_idx = 0
            while analysis_id not in analyses:
                if analysis_id in analysis_progress:
                    progress = analysis_progress[analysis_id]
                    while last_idx < len(progress):
                        yield f"data: {json.dumps(progress[last_idx])}\n\n"
                        last_idx += 1
                import time
                time.sleep(0.5)

            # Send completion
            yield f"data: {json.dumps({'type': 'complete', 'analysis_id': analysis_id})}\n\n"

        return Response(generate(), mimetype="text/event-stream")

    @app.route("/api/analysis/<analysis_id>/table")
    def get_analysis_table(analysis_id: str):
        """Get analysis results in table format"""
        if analysis_id not in analyses:
            return jsonify({"error": "Analysis not found"}), 404

        result = analyses[analysis_id]
        if "error" in result:
            return jsonify(result), 500

        # Convert to table format
        quantities = result.get("quantities", [])
        table_data = []
        for q in quantities:
            row = {
                "ID": q.get("id", ""),
                "Description": q.get("description", ""),
                "Quantity": q.get("quantity", 0),
                "Unit": q.get("unit", ""),
                "Category": q.get("category", {}).get("level1", ""),
                "Confidence": q.get("confidence", 0),
            }
            table_data.append(row)

        return jsonify({"table": table_data})

    @app.route("/api/analysis/<analysis_id>/excel")
    def get_analysis_excel(analysis_id: str):
        """Get analysis results as Excel file"""
        if analysis_id not in analyses:
            return jsonify({"error": "Analysis not found"}), 404

        result_data = analyses[analysis_id]
        if "error" in result_data:
            return jsonify(result_data), 500

        try:
            from ..core.excel_export import export_to_excel
            from ..core.schema import AnalysisResult

            # Reconstruct the AnalysisResult from stored data
            result = AnalysisResult.model_validate(result_data.get("result", {}))

            excel_bytes = export_to_excel(result)

            return Response(
                excel_bytes,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=analysis-{analysis_id}.xlsx"
                },
            )
        except Exception as e:
            return jsonify({"error": f"Excel export failed: {str(e)}"}), 500

    @app.route("/api/cache/stats")
    def cache_stats():
        """Get cache statistics"""
        from ..core.cache import get_cache
        cache = get_cache()
        return jsonify(cache.stats())

    @app.route("/api/skills")
    def list_skills():
        """List available analysis skills"""
        from ..skills import list_available_skills
        return jsonify({"skills": list_available_skills()})

    @app.route("/api/classify", methods=["POST"])
    def classify():
        """Classify a drawing without full analysis"""
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        provider = request.form.get("provider", "openai")
        api_key = request.form.get("api_key") or os.environ.get(
            "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        )

        if not api_key:
            return jsonify({"error": "No API key provided"}), 400

        try:
            from ..core.models import APIConfig, APIProvider
            from ..extraction import PDFExtractor
            from ..classification import DrawingClassifier

            # Save file temporarily
            temp_dir = tempfile.mkdtemp()
            pdf_path = Path(temp_dir) / file.filename
            file.save(pdf_path)

            # Extract thumbnail
            extractor = PDFExtractor()
            pages = list(extractor.extract(pdf_path))
            if not pages:
                return jsonify({"error": "No pages in PDF"}), 400

            thumbnail = pages[0].thumbnail

            # Classify
            api_provider = APIProvider.OPENAI if provider == "openai" else APIProvider.ANTHROPIC
            config = APIConfig(
                provider=api_provider,
                api_key=api_key,
                model="gpt-4o" if provider == "openai" else "claude-sonnet-4-20250514",
            )

            classifier = DrawingClassifier(config)
            result = classifier.classify(thumbnail)

            return jsonify({
                "drawing_type": result.drawing_type,
                "discipline": result.discipline,
                "sub_type": result.sub_type,
                "confidence": result.confidence,
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def _run_analysis(
    analysis_id: str,
    pdf_path: Path,
    provider: str,
    api_key: str,
    model: Optional[str],
    page: Optional[str],
):
    """Run analysis in background thread"""
    try:
        from ..analyzer import create_analyzer

        # Progress callback
        def on_progress(event_type: str, data: dict):
            analysis_progress[analysis_id].append({
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                **data,
            })

        on_progress("started", {"file": pdf_path.name})

        # Create analyzer
        analyzer = create_analyzer(
            provider=provider,
            api_key=api_key,
            model=model,
        )

        on_progress("initialized", {"provider": provider})

        # Run analysis
        page_num = int(page) if page else None
        result = analyzer.analyze(pdf_path, page_number=page_num)

        on_progress("completed", {"total_quantities": len(result.quantities)})

        # Store result
        analyses[analysis_id] = {
            "analysis_id": analysis_id,
            "status": "completed",
            "result": json.loads(result.model_dump_json()),
            # Flatten some fields for convenience
            "classification": {
                "drawing_type": result.classification.drawing_type,
                "discipline": result.classification.discipline,
                "confidence": result.classification.confidence,
            },
            "quantities": [q.model_dump() for q in result.quantities],
            "measurements": [m.model_dump() for m in result.measurements],
            "notes": [n.model_dump() for n in result.notes],
            "callouts": [c.model_dump() for c in result.callouts],
            "summary": {
                "total_elements": result.total_elements,
                "total_quantities": result.total_quantities,
                "average_confidence": result.average_confidence,
                "kernels_analyzed": len(result.kernels_analyzed),
            },
        }

    except Exception as e:
        analyses[analysis_id] = {
            "analysis_id": analysis_id,
            "status": "error",
            "error": str(e),
        }

    finally:
        # Cleanup temp file
        try:
            pdf_path.unlink()
            pdf_path.parent.rmdir()
        except Exception:
            pass
