"""
PDF Extraction Module

Extracts images and raw elements from PDF files.
Creates thumbnails and full-resolution images for analysis.
"""
import io
import hashlib
from pathlib import Path
from typing import Iterator, Optional
from dataclasses import dataclass

import fitz  # PyMuPDF
from PIL import Image

from ..core.models import ImageData, Thumbnail


@dataclass
class PDFPage:
    """Represents a single page from a PDF"""
    page_number: int
    width: float  # in points
    height: float  # in points
    image: ImageData
    thumbnail: Thumbnail
    text_blocks: list[dict]
    drawings: list[dict]  # Vector drawing elements


class PDFExtractor:
    """Extracts content from PDF files"""

    def __init__(self, dpi: int = 150, thumbnail_size: int = 1024):
        self.dpi = dpi
        self.thumbnail_size = thumbnail_size

    def extract(self, pdf_path: Path) -> Iterator[PDFPage]:
        """
        Extract pages from a PDF file.

        Yields PDFPage objects containing:
        - Full resolution image
        - Thumbnail
        - Text blocks with positions
        - Vector drawing elements
        """
        doc = fitz.open(pdf_path)

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                yield self._extract_page(page, page_num + 1)
        finally:
            doc.close()

    def _extract_page(self, page: fitz.Page, page_number: int) -> PDFPage:
        """Extract content from a single page"""
        # Get page dimensions
        rect = page.rect
        width, height = rect.width, rect.height

        # Render to image
        image_data = self._render_page_to_image(page)

        # Create thumbnail
        thumbnail = Thumbnail.create(image_data, max_size=self.thumbnail_size)

        # Extract text blocks
        text_blocks = self._extract_text_blocks(page)

        # Extract vector drawings
        drawings = self._extract_drawings(page)

        return PDFPage(
            page_number=page_number,
            width=width,
            height=height,
            image=image_data,
            thumbnail=thumbnail,
            text_blocks=text_blocks,
            drawings=drawings,
        )

    def _render_page_to_image(self, page: fitz.Page) -> ImageData:
        """Render a PDF page to an image"""
        # Calculate zoom for desired DPI
        zoom = self.dpi / 72  # PDF uses 72 DPI base
        matrix = fitz.Matrix(zoom, zoom)

        # Render to pixmap
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        # Convert to PIL Image then to bytes
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()

        return ImageData(
            data=data,
            width=pix.width,
            height=pix.height,
            format="png",
            page=page.number + 1,
        )

    def _extract_text_blocks(self, page: fitz.Page) -> list[dict]:
        """
        Extract text blocks with bounding boxes.

        Returns list of dicts with:
        - content: text content
        - bbox: (x1, y1, x2, y2) normalized to 0-1
        - type: 'text'
        """
        blocks = []
        page_rect = page.rect
        page_width, page_height = page_rect.width, page_rect.height

        # Get text blocks
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                bbox = block.get("bbox", (0, 0, 0, 0))

                # Extract text from lines and spans
                text_content = []
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_content.append(span.get("text", ""))

                content = " ".join(text_content).strip()
                if not content:
                    continue

                # Normalize bbox to 0-1 range
                norm_bbox = (
                    bbox[0] / page_width,
                    bbox[1] / page_height,
                    bbox[2] / page_width,
                    bbox[3] / page_height,
                )

                blocks.append({
                    "content": content,
                    "bbox": {
                        "x1": norm_bbox[0],
                        "y1": norm_bbox[1],
                        "x2": norm_bbox[2],
                        "y2": norm_bbox[3],
                    },
                    "type": "text",
                    "font_size": block.get("lines", [{}])[0].get("spans", [{}])[0].get("size", 12) if block.get("lines") else 12,
                })

        return blocks

    def _extract_drawings(self, page: fitz.Page) -> list[dict]:
        """
        Extract vector drawing elements.

        Returns list of dicts with:
        - type: 'line', 'rect', 'curve', etc.
        - bbox: normalized bounding box
        - content: drawing instruction/description
        """
        drawings = []
        page_rect = page.rect
        page_width, page_height = page_rect.width, page_rect.height

        # Get drawing paths
        paths = page.get_drawings()

        for path in paths:
            rect = path.get("rect")
            if not rect:
                continue

            # Normalize bbox
            norm_bbox = (
                rect.x0 / page_width,
                rect.y0 / page_height,
                rect.x1 / page_width,
                rect.y1 / page_height,
            )

            # Determine drawing type from items
            items = path.get("items", [])
            draw_type = self._classify_drawing_type(items)

            # Create content description
            content = self._describe_drawing(path)

            drawings.append({
                "type": draw_type,
                "bbox": {
                    "x1": norm_bbox[0],
                    "y1": norm_bbox[1],
                    "x2": norm_bbox[2],
                    "y2": norm_bbox[3],
                },
                "content": content,
                "color": path.get("color"),
                "fill": path.get("fill"),
                "width": path.get("width", 1),
            })

        return drawings

    def _classify_drawing_type(self, items: list) -> str:
        """Classify the type of drawing from its items"""
        if not items:
            return "unknown"

        # Check first item type
        first_item = items[0]
        if isinstance(first_item, tuple) and len(first_item) > 0:
            item_type = first_item[0]
            type_map = {
                "l": "line",
                "re": "rect",
                "c": "curve",
                "qu": "quad",
            }
            return type_map.get(item_type, "path")

        return "path"

    def _describe_drawing(self, path: dict) -> str:
        """Create a text description of a drawing path"""
        items = path.get("items", [])
        if not items:
            return "empty path"

        descriptions = []
        for item in items[:5]:  # Limit to first 5 items
            if isinstance(item, tuple) and len(item) > 0:
                item_type = item[0]
                if item_type == "l":
                    descriptions.append(f"line to ({item[1].x:.1f}, {item[1].y:.1f})")
                elif item_type == "re":
                    descriptions.append(f"rectangle")
                elif item_type == "c":
                    descriptions.append(f"curve")

        return "; ".join(descriptions) if descriptions else "drawing element"

    def get_file_hash(self, pdf_path: Path) -> str:
        """Calculate SHA-256 hash of the PDF file"""
        sha256 = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_page_count(self, pdf_path: Path) -> int:
        """Get the number of pages in a PDF"""
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
