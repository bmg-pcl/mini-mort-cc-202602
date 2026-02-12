"""
Prompt utilities for drawing analysis skills.
"""
from typing import Optional
from .skill_registry import SkillRegistry, DrawingSkill


# Global skill registry instance
_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """Get the global skill registry instance"""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry


def get_skill_for_drawing(drawing_type: str, discipline: str) -> DrawingSkill:
    """
    Get the appropriate skill for a drawing type and discipline.

    Args:
        drawing_type: Type of drawing (plan, section, P&ID, etc.)
        discipline: Engineering discipline (structural, electrical, etc.)

    Returns:
        The best matching DrawingSkill
    """
    registry = get_registry()
    return registry.find_skill(drawing_type, discipline)


def register_custom_skill(skill: DrawingSkill):
    """Register a custom skill"""
    registry = get_registry()
    registry.register(skill)


def list_available_skills() -> list[dict]:
    """List all available skills with their info"""
    registry = get_registry()
    return [
        {
            "name": skill.name,
            "drawing_types": skill.drawing_types,
            "disciplines": skill.disciplines,
            "description": skill.description,
            "capabilities": [c.value for c in skill.capabilities],
        }
        for skill in registry.list_skills()
    ]


# Standard JSON output schema that all skills should follow
STANDARD_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Overall confidence in the analysis (0-1)",
        },
        "complexity": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Complexity rating of this region (0-1). Higher = more complex.",
        },
        "quantities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit": {"type": "string"},
                    "category": {
                        "type": "object",
                        "properties": {
                            "level1": {"type": "string"},
                            "level2": {"type": "string"},
                            "level3": {"type": "string"},
                            "csi_division": {"type": "string"},
                        },
                    },
                    "location": {
                        "type": "object",
                        "properties": {
                            "x1": {"type": "number"},
                            "y1": {"type": "number"},
                            "x2": {"type": "number"},
                            "y2": {"type": "number"},
                        },
                    },
                    "confidence": {"type": "number"},
                },
                "required": ["description", "quantity", "unit"],
            },
        },
        "measurements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                    "label": {"type": "string"},
                    "location": {"type": "object"},
                    "confidence": {"type": "number"},
                },
                "required": ["value", "unit"],
            },
        },
        "notes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["general", "specification", "instruction", "warning", "reference"],
                    },
                    "location": {"type": "object"},
                },
                "required": ["content", "type"],
            },
        },
        "callouts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "target": {"type": "string"},
                    "location": {"type": "object"},
                },
                "required": ["id"],
            },
        },
        "metadata": {
            "type": "object",
            "additionalProperties": True,
        },
    },
    "required": ["confidence", "complexity"],
}
