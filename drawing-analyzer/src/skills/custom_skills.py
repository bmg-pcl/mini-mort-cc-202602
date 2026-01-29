"""
Custom Skills Loader

Allows loading user-defined analysis skills from YAML or JSON files.
"""
import json
from pathlib import Path
from typing import Any, Optional

from .skill_registry import DrawingSkill, AnalysisCapability, SkillRegistry


def load_skill_from_dict(data: dict) -> DrawingSkill:
    """
    Load a skill from a dictionary.

    Expected format:
    {
        "name": "my_custom_skill",
        "drawing_types": ["plan", "section"],
        "disciplines": ["structural"],
        "description": "Custom skill for structural analysis",
        "capabilities": ["quantity_takeoff", "measurement"],
        "priority": 10,
        "analysis_prompt": "Analyze this structural drawing..."
    }
    """
    # Map capability strings to enum values
    capability_map = {
        "quantity_takeoff": AnalysisCapability.QUANTITY_TAKEOFF,
        "factoring": AnalysisCapability.FACTORING,
        "measurement": AnalysisCapability.MEASUREMENT,
        "notes_extraction": AnalysisCapability.NOTES_EXTRACTION,
        "metadata_extraction": AnalysisCapability.METADATA_EXTRACTION,
        "finding_references": AnalysisCapability.FINDING_REFERENCES,
        "symbol_recognition": AnalysisCapability.SYMBOL_RECOGNITION,
        "schedule_extraction": AnalysisCapability.SCHEDULE_EXTRACTION,
    }

    capabilities = []
    for cap_str in data.get("capabilities", []):
        if cap_str.lower() in capability_map:
            capabilities.append(capability_map[cap_str.lower()])

    return DrawingSkill(
        name=data["name"],
        drawing_types=data.get("drawing_types", ["*"]),
        disciplines=data.get("disciplines", []),
        description=data.get("description", ""),
        capabilities=capabilities,
        analysis_prompt=data.get("analysis_prompt", ""),
        output_schema=data.get("output_schema", {}),
        priority=data.get("priority", 0),
    )


def load_skills_from_json(path: Path) -> list[DrawingSkill]:
    """
    Load skills from a JSON file.

    The file can contain either:
    - A single skill object
    - An array of skill objects
    - An object with a "skills" key containing an array
    """
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        return [load_skill_from_dict(item) for item in data]
    elif isinstance(data, dict):
        if "skills" in data:
            return [load_skill_from_dict(item) for item in data["skills"]]
        else:
            return [load_skill_from_dict(data)]

    raise ValueError(f"Invalid skills file format: {path}")


def load_skills_from_yaml(path: Path) -> list[DrawingSkill]:
    """
    Load skills from a YAML file.

    Requires PyYAML to be installed.
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML is required to load YAML skills files. Install with: pip install pyyaml")

    with open(path) as f:
        data = yaml.safe_load(f)

    if isinstance(data, list):
        return [load_skill_from_dict(item) for item in data]
    elif isinstance(data, dict):
        if "skills" in data:
            return [load_skill_from_dict(item) for item in data["skills"]]
        else:
            return [load_skill_from_dict(data)]

    raise ValueError(f"Invalid skills file format: {path}")


def load_skills_from_file(path: Path) -> list[DrawingSkill]:
    """
    Load skills from a file (auto-detect format by extension).
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".json":
        return load_skills_from_json(path)
    elif suffix in (".yaml", ".yml"):
        return load_skills_from_yaml(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def load_skills_from_directory(directory: Path) -> list[DrawingSkill]:
    """
    Load all skills from a directory.

    Scans for .json, .yaml, and .yml files.
    """
    directory = Path(directory)
    skills = []

    for pattern in ("*.json", "*.yaml", "*.yml"):
        for path in directory.glob(pattern):
            try:
                skills.extend(load_skills_from_file(path))
            except Exception as e:
                print(f"Warning: Failed to load skills from {path}: {e}")

    return skills


def register_custom_skills(
    registry: SkillRegistry,
    source: Path | str | list[dict],
) -> int:
    """
    Register custom skills to a registry.

    Args:
        registry: The skill registry to add skills to
        source: Can be:
            - Path to a file (.json, .yaml, .yml)
            - Path to a directory containing skill files
            - List of skill dictionaries

    Returns:
        Number of skills registered
    """
    skills = []

    if isinstance(source, list):
        skills = [load_skill_from_dict(item) for item in source]
    elif isinstance(source, (str, Path)):
        path = Path(source)
        if path.is_file():
            skills = load_skills_from_file(path)
        elif path.is_dir():
            skills = load_skills_from_directory(path)
        else:
            raise FileNotFoundError(f"Path not found: {path}")

    for skill in skills:
        registry.register(skill)

    return len(skills)


# Example skill templates

EXAMPLE_SKILL_JSON = """
{
    "name": "custom_mechanical",
    "drawing_types": ["plan", "layout", "section"],
    "disciplines": ["mechanical", "HVAC"],
    "description": "Custom skill for mechanical equipment analysis",
    "capabilities": ["quantity_takeoff", "measurement", "notes_extraction"],
    "priority": 15,
    "analysis_prompt": "Analyze this mechanical drawing region.\\n\\nFocus on:\\n1. EQUIPMENT: Identify all mechanical equipment (AHUs, FCUs, pumps, fans)\\n2. DUCTWORK: Note duct sizes and types\\n3. PIPING: Identify pipe sizes and systems\\n4. SCHEDULES: Extract equipment schedules\\n\\nRespond with JSON including quantities and measurements."
}
"""

EXAMPLE_SKILL_YAML = """
name: custom_electrical_panel
drawing_types:
  - SLD
  - schematic
  - panel_schedule
disciplines:
  - electrical
description: Custom skill for electrical panel analysis
capabilities:
  - quantity_takeoff
  - schedule_extraction
  - finding_references
priority: 15
analysis_prompt: |
  Analyze this electrical panel or single line diagram.

  Focus on:
  1. PANELS: Identify panel names, ratings, and locations
  2. BREAKERS: Count circuit breakers by size and type
  3. LOADS: List connected loads with ratings
  4. FEEDERS: Note feeder sizes and lengths

  Respond with JSON including equipment counts and specifications.
"""


def create_example_skills_file(output_path: Path, format: str = "json") -> None:
    """Create an example skills file for reference"""
    output_path = Path(output_path)

    if format == "json":
        output_path.write_text(EXAMPLE_SKILL_JSON)
    elif format == "yaml":
        output_path.write_text(EXAMPLE_SKILL_YAML)
    else:
        raise ValueError(f"Unknown format: {format}")
