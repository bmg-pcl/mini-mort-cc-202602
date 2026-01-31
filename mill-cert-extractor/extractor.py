"""
Mill Certificate Extractor using Azure Document Intelligence

This module extracts data from Mill Test Reports (MTR) / Mill Certificates
using Azure AI Document Intelligence.
"""

import os
import json
from typing import Optional
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential


class MillCertExtractor:
    """Extract data from Mill Test Reports using Azure Document Intelligence."""

    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the extractor with Azure credentials.

        Args:
            endpoint: Azure Document Intelligence endpoint URL
            api_key: Azure Document Intelligence API key
        """
        self.endpoint = endpoint or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not self.endpoint or not self.api_key:
            raise ValueError(
                "Azure Document Intelligence credentials required. "
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY "
                "environment variables or pass them to the constructor."
            )

        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.api_key)
        )

    def extract_from_file(self, file_path: str) -> dict:
        """
        Extract mill certificate data from a local file.

        Args:
            file_path: Path to the mill certificate file (PDF, image, etc.)

        Returns:
            Dictionary containing extracted mill certificate data
        """
        with open(file_path, "rb") as f:
            file_content = f.read()
        return self.extract_from_bytes(file_content)

    def extract_from_bytes(self, file_content: bytes) -> dict:
        """
        Extract mill certificate data from file bytes.

        Args:
            file_content: Raw bytes of the mill certificate file

        Returns:
            Dictionary containing extracted mill certificate data
        """
        # Use prebuilt-layout for general document extraction
        # This extracts tables, key-value pairs, and text
        poller = self.client.begin_analyze_document(
            model_id="prebuilt-layout",
            analyze_request=file_content,
            content_type="application/octet-stream"
        )
        result: AnalyzeResult = poller.result()
        return self._process_result(result)

    def extract_from_url(self, document_url: str) -> dict:
        """
        Extract mill certificate data from a URL.

        Args:
            document_url: URL to the mill certificate document

        Returns:
            Dictionary containing extracted mill certificate data
        """
        poller = self.client.begin_analyze_document(
            model_id="prebuilt-layout",
            analyze_request=AnalyzeDocumentRequest(url_source=document_url)
        )
        result: AnalyzeResult = poller.result()
        return self._process_result(result)

    def _process_result(self, result: AnalyzeResult) -> dict:
        """
        Process the Azure Document Intelligence result into structured mill cert data.

        Args:
            result: The AnalyzeResult from Azure Document Intelligence

        Returns:
            Structured dictionary with mill certificate information
        """
        extracted_data = {
            "raw_text": "",
            "pages": [],
            "tables": [],
            "key_value_pairs": [],
            "mill_cert_fields": self._extract_mill_cert_fields(result)
        }

        # Extract full text content
        if result.content:
            extracted_data["raw_text"] = result.content

        # Extract page information
        if result.pages:
            for page in result.pages:
                page_info = {
                    "page_number": page.page_number,
                    "width": page.width,
                    "height": page.height,
                    "unit": page.unit,
                    "lines": []
                }
                if page.lines:
                    for line in page.lines:
                        page_info["lines"].append({
                            "content": line.content,
                            "polygon": line.polygon if line.polygon else None
                        })
                extracted_data["pages"].append(page_info)

        # Extract tables (crucial for mill cert data)
        if result.tables:
            for table in result.tables:
                table_data = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": []
                }
                if table.cells:
                    for cell in table.cells:
                        table_data["cells"].append({
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "content": cell.content,
                            "row_span": cell.row_span if cell.row_span else 1,
                            "column_span": cell.column_span if cell.column_span else 1
                        })
                extracted_data["tables"].append(table_data)

        # Extract key-value pairs
        if result.key_value_pairs:
            for kv in result.key_value_pairs:
                key_content = kv.key.content if kv.key else ""
                value_content = kv.value.content if kv.value else ""
                extracted_data["key_value_pairs"].append({
                    "key": key_content,
                    "value": value_content,
                    "confidence": kv.confidence if kv.confidence else None
                })

        return extracted_data

    def _extract_mill_cert_fields(self, result: AnalyzeResult) -> dict:
        """
        Extract common mill certificate fields from the document.

        This method looks for typical MTR fields like:
        - Material grade/specification
        - Heat number
        - Chemical composition
        - Mechanical properties
        - Dimensions
        - Manufacturer info

        Args:
            result: The AnalyzeResult from Azure Document Intelligence

        Returns:
            Dictionary with extracted mill certificate specific fields
        """
        fields = {
            "material_info": {},
            "chemical_composition": {},
            "mechanical_properties": {},
            "dimensions": {},
            "manufacturer": {},
            "certifications": []
        }

        # Common mill cert field patterns
        material_keywords = [
            "grade", "specification", "spec", "material", "alloy",
            "heat no", "heat number", "lot no", "lot number",
            "po", "purchase order", "customer", "part no"
        ]
        chemical_keywords = [
            "c", "carbon", "mn", "manganese", "p", "phosphorus",
            "s", "sulfur", "si", "silicon", "cr", "chromium",
            "ni", "nickel", "mo", "molybdenum", "cu", "copper",
            "v", "vanadium", "n", "nitrogen", "al", "aluminum",
            "ti", "titanium", "nb", "niobium", "b", "boron"
        ]
        mechanical_keywords = [
            "tensile", "yield", "elongation", "reduction",
            "hardness", "hrc", "hrb", "brinell", "charpy",
            "impact", "ultimate", "strength", "uts"
        ]
        dimension_keywords = [
            "thickness", "width", "length", "diameter", "od", "id",
            "wall", "size", "weight", "area"
        ]

        # Process key-value pairs
        if result.key_value_pairs:
            for kv in result.key_value_pairs:
                if not kv.key or not kv.value:
                    continue
                key = kv.key.content.lower().strip()
                value = kv.value.content.strip()

                # Categorize the field
                if any(k in key for k in material_keywords):
                    fields["material_info"][kv.key.content] = value
                elif any(k in key for k in chemical_keywords):
                    fields["chemical_composition"][kv.key.content] = value
                elif any(k in key for k in mechanical_keywords):
                    fields["mechanical_properties"][kv.key.content] = value
                elif any(k in key for k in dimension_keywords):
                    fields["dimensions"][kv.key.content] = value

        # Look for standards/certifications in text
        if result.content:
            content_lower = result.content.lower()
            standards = [
                "ASTM", "ASME", "AMS", "SAE", "MIL-SPEC", "ISO",
                "EN", "DIN", "JIS", "AWS", "AISI", "API"
            ]
            for std in standards:
                if std.lower() in content_lower:
                    # Find the full specification reference
                    import re
                    pattern = rf"{std}[\s-]?[A-Z]?[\d]+[-\w]*"
                    matches = re.findall(pattern, result.content, re.IGNORECASE)
                    fields["certifications"].extend(matches)

            # Remove duplicates
            fields["certifications"] = list(set(fields["certifications"]))

        return fields

    def to_json(self, data: dict, indent: int = 2) -> str:
        """Convert extracted data to JSON string."""
        return json.dumps(data, indent=indent, default=str)


def main():
    """CLI entry point for the mill cert extractor."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract data from Mill Test Reports using Azure Document Intelligence"
    )
    parser.add_argument(
        "file",
        help="Path to the mill certificate file (PDF, image, etc.)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--endpoint",
        help="Azure Document Intelligence endpoint (or set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT)"
    )
    parser.add_argument(
        "--key",
        help="Azure Document Intelligence API key (or set AZURE_DOCUMENT_INTELLIGENCE_KEY)"
    )

    args = parser.parse_args()

    try:
        extractor = MillCertExtractor(
            endpoint=args.endpoint,
            api_key=args.key
        )
        result = extractor.extract_from_file(args.file)
        json_output = extractor.to_json(result)

        if args.output:
            with open(args.output, "w") as f:
                f.write(json_output)
            print(f"Results written to {args.output}")
        else:
            print(json_output)

    except Exception as e:
        print(f"Error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
