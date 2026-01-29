"""
Drawing Classifier

Classifies technical drawings by type and discipline using AI vision.
"""
import json
from typing import Optional

from ..core.models import APIConfig, APIProvider, Thumbnail
from ..core.schema import DrawingClassification


CLASSIFICATION_PROMPT = """Analyze this technical/construction drawing and classify it.

Determine:
1. Drawing Type - What type of technical drawing is this?
   Options: layout, general_arrangement, plan, elevation, section, detail,
   isometric, P&ID (piping and instrumentation), SLD (single line diagram),
   schematic, schedule, legend, title_sheet, cover, site_plan, floor_plan,
   reflected_ceiling_plan, roof_plan, foundation_plan, framing_plan,
   demolition_plan, finish_plan, equipment_layout, other

2. Discipline - What engineering/construction discipline does this drawing belong to?
   Options: architectural, structural, civil, mechanical, electrical, plumbing,
   fire_protection, HVAC, piping, instrumentation, process, landscape,
   interior_design, telecommunications, other

3. Sub-type (optional) - Any more specific classification

Respond with JSON only in this exact format:
{
    "drawing_type": "<type>",
    "discipline": "<discipline>",
    "sub_type": "<sub_type or null>",
    "confidence": <0.0 to 1.0>,
    "reasoning": "<brief explanation>"
}"""


class DrawingClassifier:
    """
    Classifies technical drawings using AI vision.

    Provides the thumbnail to the API and prompts for the type of drawing
    from typical construction drawings - layout/GA, P&ID, SLD, isometric,
    sectional, etc. - and classifies the discipline as well.
    """

    def __init__(self, api_config: APIConfig):
        self.api_config = api_config
        self._client = None

    @property
    def client(self):
        """Lazy-load the API client"""
        if self._client is None:
            if self.api_config.provider == APIProvider.OPENAI:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self.api_config.api_key,
                    base_url=self.api_config.base_url,
                )
            elif self.api_config.provider == APIProvider.ANTHROPIC:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self.api_config.api_key)
        return self._client

    def classify(self, thumbnail: Thumbnail) -> DrawingClassification:
        """
        Classify a drawing based on its thumbnail.

        Args:
            thumbnail: Low-resolution thumbnail of the drawing

        Returns:
            DrawingClassification with type, discipline, and confidence
        """
        if self.api_config.provider == APIProvider.OPENAI:
            return self._classify_openai(thumbnail)
        elif self.api_config.provider == APIProvider.ANTHROPIC:
            return self._classify_anthropic(thumbnail)
        else:
            raise ValueError(f"Unsupported provider: {self.api_config.provider}")

    def _classify_openai(self, thumbnail: Thumbnail) -> DrawingClassification:
        """Classify using OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.api_config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": CLASSIFICATION_PROMPT,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": thumbnail.image.data_url,
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=self.api_config.max_tokens,
            temperature=self.api_config.temperature,
        )

        return self._parse_response(response.choices[0].message.content)

    def _classify_anthropic(self, thumbnail: Thumbnail) -> DrawingClassification:
        """Classify using Anthropic API"""
        response = self.client.messages.create(
            model=self.api_config.model,
            max_tokens=self.api_config.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": f"image/{thumbnail.image.format}",
                                "data": thumbnail.image.base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": CLASSIFICATION_PROMPT,
                        },
                    ],
                }
            ],
        )

        return self._parse_response(response.content[0].text)

    def _parse_response(self, response_text: str) -> DrawingClassification:
        """Parse the API response into a DrawingClassification"""
        try:
            # Try to extract JSON from the response
            text = response_text.strip()

            # Handle markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text)

            return DrawingClassification(
                drawing_type=data.get("drawing_type", "unknown"),
                discipline=data.get("discipline", "unknown"),
                sub_type=data.get("sub_type"),
                confidence=float(data.get("confidence", 0.5)),
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # Return a default classification if parsing fails
            return DrawingClassification(
                drawing_type="unknown",
                discipline="unknown",
                sub_type=None,
                confidence=0.0,
            )


# Mapping of drawing types to their typical characteristics
DRAWING_TYPE_INFO = {
    "layout": {
        "description": "Overall arrangement showing equipment, rooms, or spaces",
        "typical_elements": ["equipment", "rooms", "dimensions", "grids"],
    },
    "general_arrangement": {
        "description": "GA drawing showing overall layout and arrangement",
        "typical_elements": ["equipment", "structures", "dimensions", "grids"],
    },
    "plan": {
        "description": "Top-down view of a level or area",
        "typical_elements": ["walls", "doors", "windows", "dimensions"],
    },
    "elevation": {
        "description": "Vertical view of a building face or element",
        "typical_elements": ["heights", "levels", "finishes", "dimensions"],
    },
    "section": {
        "description": "Cut-through view showing internal construction",
        "typical_elements": ["materials", "construction_details", "dimensions"],
    },
    "detail": {
        "description": "Enlarged view of specific construction detail",
        "typical_elements": ["materials", "fasteners", "dimensions", "notes"],
    },
    "isometric": {
        "description": "3D representation of piping or systems",
        "typical_elements": ["pipes", "fittings", "valves", "dimensions"],
    },
    "P&ID": {
        "description": "Piping and Instrumentation Diagram",
        "typical_elements": ["pipes", "instruments", "valves", "equipment"],
    },
    "SLD": {
        "description": "Single Line Diagram for electrical systems",
        "typical_elements": ["equipment", "connections", "ratings", "protection"],
    },
    "schematic": {
        "description": "Simplified diagram showing system relationships",
        "typical_elements": ["symbols", "connections", "labels"],
    },
    "schedule": {
        "description": "Tabular information about elements",
        "typical_elements": ["tables", "specifications", "quantities"],
    },
}

DISCIPLINE_INFO = {
    "architectural": {
        "prefix": ["A-"],
        "typical_drawings": ["plans", "elevations", "sections", "details"],
    },
    "structural": {
        "prefix": ["S-"],
        "typical_drawings": ["framing_plans", "sections", "details", "schedules"],
    },
    "civil": {
        "prefix": ["C-"],
        "typical_drawings": ["site_plans", "grading", "utilities"],
    },
    "mechanical": {
        "prefix": ["M-"],
        "typical_drawings": ["equipment_layouts", "piping", "ductwork"],
    },
    "electrical": {
        "prefix": ["E-"],
        "typical_drawings": ["power_plans", "lighting", "SLD"],
    },
    "plumbing": {
        "prefix": ["P-"],
        "typical_drawings": ["risers", "plans", "details"],
    },
    "fire_protection": {
        "prefix": ["FP-"],
        "typical_drawings": ["sprinkler_plans", "risers", "details"],
    },
    "HVAC": {
        "prefix": ["H-", "HVAC-"],
        "typical_drawings": ["duct_plans", "equipment", "controls"],
    },
    "piping": {
        "prefix": ["PI-"],
        "typical_drawings": ["isometrics", "P&ID", "plans"],
    },
    "instrumentation": {
        "prefix": ["I-"],
        "typical_drawings": ["P&ID", "loop_diagrams", "details"],
    },
}
