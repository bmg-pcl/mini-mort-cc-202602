"""
Element Extractor

Converts raw PDF extractions into standardized DrawingElement objects.
Creates the data list L as specified in the requirements.
"""
import uuid
from typing import Iterator

from ..core.schema import (
    DrawingElement,
    ElementType,
    BoundingBox,
)
from .pdf_extractor import PDFPage


class ElementExtractor:
    """
    Extracts and normalizes elements from PDF pages into a standardized format.

    Creates data list L by extracting all text, annotation, and vector elements
    from the PDF into a list of:
    [Item | Type | Content | bbox x1 y1 x2 y2 | centroid]
    """

    def __init__(self):
        self._id_counter = 0

    def _generate_id(self, prefix: str = "elem") -> str:
        """Generate a unique element ID"""
        self._id_counter += 1
        return f"{prefix}_{self._id_counter:06d}"

    def extract_elements(self, page: PDFPage) -> list[DrawingElement]:
        """
        Extract all elements from a PDF page into standardized format.

        Returns list of DrawingElement objects representing:
        - Text content
        - Annotations
        - Vector drawing instructions
        """
        elements = []

        # Extract text elements
        for text_block in page.text_blocks:
            element = self._convert_text_block(text_block, page.page_number)
            if element:
                elements.append(element)

        # Extract drawing elements
        for drawing in page.drawings:
            element = self._convert_drawing(drawing, page.page_number)
            if element:
                elements.append(element)

        return elements

    def _convert_text_block(self, block: dict, page_num: int) -> DrawingElement | None:
        """Convert a text block to a DrawingElement"""
        content = block.get("content", "").strip()
        if not content:
            return None

        bbox_data = block.get("bbox", {})
        bbox = BoundingBox(
            x1=bbox_data.get("x1", 0),
            y1=bbox_data.get("y1", 0),
            x2=bbox_data.get("x2", 0),
            y2=bbox_data.get("y2", 0),
        )

        # Classify text type based on content and position
        element_type = self._classify_text_type(content, bbox, block)

        return DrawingElement(
            id=self._generate_id("txt"),
            type=element_type,
            content=content,
            bbox=bbox,
            confidence=0.9,  # PDF extraction is generally reliable
            page=page_num,
            metadata={
                "font_size": block.get("font_size", 12),
                "source": "pdf_text",
            },
        )

    def _classify_text_type(
        self, content: str, bbox: BoundingBox, block: dict
    ) -> ElementType:
        """
        Classify the type of text element based on content and context.
        """
        content_lower = content.lower()
        font_size = block.get("font_size", 12)

        # Check for dimensions (numbers with units)
        if self._is_dimension(content):
            return ElementType.DIMENSION

        # Check for notes (typically start with numbers or specific words)
        if self._is_note(content):
            return ElementType.NOTE

        # Check for callouts (short alphanumeric identifiers)
        if self._is_callout(content):
            return ElementType.CALLOUT

        # Check for revision markers
        if self._is_revision(content):
            return ElementType.REVISION

        # Check for references (drawing numbers, detail references)
        if self._is_reference(content):
            return ElementType.REFERENCE

        # Check for title block content (typically in corners, larger font)
        if bbox.y2 > 0.85 or bbox.y1 < 0.15:  # Top or bottom 15%
            if font_size > 10:
                return ElementType.TITLEBLOCK

        # Check for annotations (typically shorter text near drawings)
        if len(content) < 50 and bbox.width < 0.3:
            return ElementType.ANNOTATION

        return ElementType.TEXT

    def _is_dimension(self, content: str) -> bool:
        """Check if content looks like a dimension"""
        import re

        # Common dimension patterns
        patterns = [
            r"^\d+[\'\"]\s*-?\s*\d*[\'\"]*$",  # 10'-6", 12', etc.
            r"^\d+\.?\d*\s*(mm|cm|m|in|ft|\'|\")",  # 100mm, 2.5m, etc.
            r"^\d+\s*x\s*\d+",  # 10 x 20
            r"^\d+\'-\d+\"$",  # 10'-6"
            r"^[0-9]+\.[0-9]+$",  # Decimal numbers
        ]

        for pattern in patterns:
            if re.match(pattern, content.strip(), re.IGNORECASE):
                return True

        return False

    def _is_note(self, content: str) -> bool:
        """Check if content looks like a note"""
        import re

        # Notes often start with numbers followed by periods or parentheses
        if re.match(r"^\d+[\.\)]\s+", content):
            return True

        # Or start with specific keywords
        note_starters = ["note:", "notes:", "see ", "ref.", "typ.", "typical"]
        content_lower = content.lower()
        for starter in note_starters:
            if content_lower.startswith(starter):
                return True

        return False

    def _is_callout(self, content: str) -> bool:
        """Check if content looks like a callout"""
        import re

        # Callouts are typically short (1-4 characters)
        content = content.strip()
        if len(content) > 10:
            return False

        # Single letters or numbers
        if re.match(r"^[A-Z]$|^\d{1,2}$|^[A-Z]-\d+$|^DET-\d+$", content, re.IGNORECASE):
            return True

        return False

    def _is_revision(self, content: str) -> bool:
        """Check if content looks like a revision marker"""
        import re

        content = content.strip().upper()

        # Revision patterns
        if re.match(r"^REV\.?\s*[A-Z0-9]", content):
            return True
        if re.match(r"^R\d+$", content):
            return True

        return False

    def _is_reference(self, content: str) -> bool:
        """Check if content looks like a drawing reference"""
        import re

        # Drawing number patterns
        patterns = [
            r"^[A-Z]{1,3}-\d{2,4}",  # S-101, M-201, etc.
            r"^\d+/[A-Z]-\d+",  # 1/S-101 (detail reference)
            r"^DWG\.?\s*[A-Z0-9-]+",  # DWG. S-101
        ]

        for pattern in patterns:
            if re.match(pattern, content.strip(), re.IGNORECASE):
                return True

        return False

    def _convert_drawing(self, drawing: dict, page_num: int) -> DrawingElement | None:
        """Convert a vector drawing to a DrawingElement"""
        content = drawing.get("content", "")
        if not content:
            return None

        bbox_data = drawing.get("bbox", {})
        bbox = BoundingBox(
            x1=bbox_data.get("x1", 0),
            y1=bbox_data.get("y1", 0),
            x2=bbox_data.get("x2", 0),
            y2=bbox_data.get("y2", 0),
        )

        # Skip very small drawings (likely noise)
        if bbox.width < 0.001 and bbox.height < 0.001:
            return None

        draw_type = drawing.get("type", "path")
        element_type = self._classify_drawing_type(draw_type, bbox)

        return DrawingElement(
            id=self._generate_id("drw"),
            type=element_type,
            content=content,
            bbox=bbox,
            confidence=0.8,
            page=page_num,
            metadata={
                "draw_type": draw_type,
                "color": drawing.get("color"),
                "fill": drawing.get("fill"),
                "width": drawing.get("width"),
                "source": "pdf_drawing",
            },
        )

    def _classify_drawing_type(self, draw_type: str, bbox: BoundingBox) -> ElementType:
        """Classify the element type of a drawing"""
        # Lines could be leaders or just lines
        if draw_type == "line":
            # Long thin lines are likely leaders
            if bbox.width > 0.1 or bbox.height > 0.1:
                return ElementType.LEADER
            return ElementType.LINE

        if draw_type == "rect":
            return ElementType.SHAPE

        return ElementType.LINE

    def elements_to_list_format(self, elements: list[DrawingElement]) -> list[dict]:
        """
        Convert elements to the specified list format:
        [Item | Type | Content | bbox x1 y1 x2 y2 | centroid]
        """
        result = []
        for elem in elements:
            result.append({
                "item": elem.id,
                "type": elem.type.value,
                "content": elem.content,
                "bbox": {
                    "x1": elem.bbox.x1,
                    "y1": elem.bbox.y1,
                    "x2": elem.bbox.x2,
                    "y2": elem.bbox.y2,
                },
                "centroid": elem.bbox.centroid,
            })
        return result
