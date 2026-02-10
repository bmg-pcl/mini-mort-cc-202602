"""
Main Drawing Analyzer

Orchestrates the complete drawing analysis workflow.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .core.models import APIConfig, APIProvider, AnalysisConfig, Thumbnail
from .core.schema import (
    AnalysisResult,
    DrawingClassification,
    DrawingMetadata,
    DrawingElement,
)
from .extraction import PDFExtractor, ElementExtractor
from .classification import DrawingClassifier
from .convolution import ConvolutionalAnalyzer


class DrawingAnalyzer:
    """
    Main orchestrator for technical drawing analysis.

    Workflow:
    1. Extract PDF content (images, text, vectors)
    2. Create thumbnail
    3. Classify drawing type and discipline
    4. Select appropriate analysis skill
    5. Analyze using convolutional approach
    6. Output structured results
    """

    def __init__(
        self,
        api_config: APIConfig,
        analysis_config: Optional[AnalysisConfig] = None,
    ):
        self.api_config = api_config
        self.analysis_config = analysis_config or AnalysisConfig()

        # Initialize components
        self.pdf_extractor = PDFExtractor(
            dpi=150,
            thumbnail_size=self.analysis_config.thumbnail_max_size,
        )
        self.element_extractor = ElementExtractor()
        self.classifier = DrawingClassifier(api_config)
        self.conv_analyzer = ConvolutionalAnalyzer(api_config, self.analysis_config)

    def analyze(
        self,
        pdf_path: Path,
        page_number: Optional[int] = None,
    ) -> AnalysisResult:
        """
        Analyze a technical drawing PDF.

        Args:
            pdf_path: Path to the PDF file
            page_number: Specific page to analyze (None = all pages)

        Returns:
            Complete AnalysisResult with quantities, measurements, notes, etc.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Get file hash for traceability
        file_hash = self.pdf_extractor.get_file_hash(pdf_path)

        # Initialize result
        result = AnalysisResult(
            source_file=str(pdf_path),
            source_hash=file_hash,
            analysis_timestamp=datetime.utcnow(),
            classification=DrawingClassification(
                drawing_type="unknown",
                discipline="unknown",
                confidence=0.0,
            ),
            metadata=DrawingMetadata(),
        )

        # Process pages
        all_elements = []
        for page in self.pdf_extractor.extract(pdf_path):
            if page_number is not None and page.page_number != page_number:
                continue

            # Extract elements
            elements = self.element_extractor.extract_elements(page)
            all_elements.extend(elements)

            # Classify drawing (use first page for classification)
            if result.classification.drawing_type == "unknown":
                result.classification = self.classifier.classify(page.thumbnail)

            # Extract metadata from elements
            self._extract_metadata(elements, result.metadata)

            # Analyze with convolutional approach
            quantities, measurements, notes, callouts, kernels = self.conv_analyzer.analyze(
                image=page.image,
                thumbnail=page.thumbnail,
                elements=elements,
                drawing_type=result.classification.drawing_type,
                discipline=result.classification.discipline,
            )

            # Update source drawing reference
            for q in quantities:
                q.source_drawing = str(pdf_path.name)
                q.source_page = page.page_number

            # Accumulate results
            result.quantities.extend(quantities)
            result.measurements.extend(measurements)
            result.notes.extend(notes)
            result.callouts.extend(callouts)
            result.kernels_analyzed.extend(kernels)

        # Store all elements
        result.elements = all_elements

        # Calculate summary statistics
        result.total_elements = len(all_elements)
        result.total_quantities = len(result.quantities)
        if result.quantities:
            result.average_confidence = sum(
                q.confidence for q in result.quantities
            ) / len(result.quantities)
        result.requires_review_count = sum(
            1 for q in result.quantities if q.confidence < 0.7
        )

        return result

    def _extract_metadata(
        self, elements: list[DrawingElement], metadata: DrawingMetadata
    ):
        """Extract drawing metadata from elements"""
        import re

        for elem in elements:
            content = elem.content.strip()

            # Look for drawing number patterns
            if not metadata.drawing_number:
                match = re.match(r"^([A-Z]{1,3}-\d{2,4})", content)
                if match:
                    metadata.drawing_number = match.group(1)

            # Look for revision
            if not metadata.revision:
                match = re.search(r"REV\.?\s*([A-Z0-9]+)", content, re.IGNORECASE)
                if match:
                    metadata.revision = match.group(1)

            # Look for scale
            if not metadata.scale:
                match = re.search(
                    r"SCALE[:\s]*([0-9/\"\'=\s]+)", content, re.IGNORECASE
                )
                if match:
                    metadata.scale = match.group(1).strip()

            # Look for project name (typically in title block area)
            if not metadata.project_name and elem.bbox.y2 > 0.85:
                if len(content) > 10 and content.isupper():
                    metadata.project_name = content

    def analyze_to_json(self, pdf_path: Path, **kwargs) -> str:
        """Analyze and return JSON string"""
        result = self.analyze(pdf_path, **kwargs)
        return result.model_dump_json(indent=2)

    def analyze_to_table(self, pdf_path: Path, **kwargs) -> list[dict]:
        """Analyze and return table format (for Excel)"""
        result = self.analyze(pdf_path, **kwargs)
        return result.to_table_format()


def create_analyzer(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> DrawingAnalyzer:
    """
    Factory function to create a DrawingAnalyzer.

    Args:
        provider: API provider ("openai" or "anthropic")
        api_key: API key (or use environment variable)
        model: Model to use (or use default for provider)
        **kwargs: Additional AnalysisConfig options

    Returns:
        Configured DrawingAnalyzer instance
    """
    import os

    # Determine provider
    if provider.lower() == "openai":
        api_provider = APIProvider.OPENAI
        default_model = "gpt-4o"
        env_key = "OPENAI_API_KEY"
    elif provider.lower() == "anthropic":
        api_provider = APIProvider.ANTHROPIC
        default_model = "claude-sonnet-4-20250514"
        env_key = "ANTHROPIC_API_KEY"
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Get API key
    key = api_key or os.environ.get(env_key)
    if not key:
        raise ValueError(f"No API key provided. Set {env_key} environment variable or pass api_key parameter.")

    # Create config
    api_config = APIConfig(
        provider=api_provider,
        api_key=key,
        model=model or default_model,
    )

    # Create analysis config with any extra options
    analysis_config = AnalysisConfig(**kwargs)

    return DrawingAnalyzer(api_config, analysis_config)
