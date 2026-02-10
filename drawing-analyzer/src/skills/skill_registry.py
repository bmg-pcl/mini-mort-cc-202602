"""
Skill Registry

Manages a library of drawing analysis skills, one per drawing type.
Each skill defines what the drawing type is and what drawing review typically does.
"""
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum


class AnalysisCapability(str, Enum):
    """Types of analysis a skill can perform"""
    QUANTITY_TAKEOFF = "quantity_takeoff"
    FACTORING = "factoring"
    MEASUREMENT = "measurement"
    NOTES_EXTRACTION = "notes_extraction"
    METADATA_EXTRACTION = "metadata_extraction"
    FINDING_REFERENCES = "finding_references"
    SYMBOL_RECOGNITION = "symbol_recognition"
    SCHEDULE_EXTRACTION = "schedule_extraction"


@dataclass
class DrawingSkill:
    """
    A skill for analyzing a specific type of drawing.

    Each skill defines:
    - What the drawing type is
    - What drawing review typically does for this type
    - The prompt to use for analysis
    - Expected output structure
    """
    name: str
    drawing_types: list[str]  # Types this skill handles
    disciplines: list[str]  # Disciplines this skill handles
    description: str
    capabilities: list[AnalysisCapability]
    analysis_prompt: str
    output_schema: dict = field(default_factory=dict)
    priority: int = 0  # Higher priority skills are preferred

    def matches(self, drawing_type: str, discipline: str) -> bool:
        """Check if this skill matches the given drawing type and discipline"""
        type_match = drawing_type.lower() in [t.lower() for t in self.drawing_types]
        discipline_match = discipline.lower() in [d.lower() for d in self.disciplines]

        # If no specific disciplines, match all
        if not self.disciplines:
            discipline_match = True

        return type_match or discipline_match


class SkillRegistry:
    """Registry of available drawing analysis skills"""

    def __init__(self):
        self._skills: dict[str, DrawingSkill] = {}
        self._register_default_skills()

    def register(self, skill: DrawingSkill):
        """Register a new skill"""
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> Optional[DrawingSkill]:
        """Get a skill by name"""
        return self._skills.get(name)

    def find_skill(self, drawing_type: str, discipline: str) -> DrawingSkill:
        """
        Find the best matching skill for a drawing type and discipline.

        Returns the generic skill if no specific match is found.
        """
        matches = []
        for skill in self._skills.values():
            if skill.matches(drawing_type, discipline):
                matches.append(skill)

        if not matches:
            return self._skills.get("generic_technical", self._create_generic_skill())

        # Return highest priority match
        matches.sort(key=lambda s: s.priority, reverse=True)
        return matches[0]

    def list_skills(self) -> list[DrawingSkill]:
        """List all registered skills"""
        return list(self._skills.values())

    def _create_generic_skill(self) -> DrawingSkill:
        """Create the default generic technical drawing skill"""
        return DrawingSkill(
            name="generic_technical",
            drawing_types=["*"],
            disciplines=["*"],
            description="Generic skill for analyzing technical drawings",
            capabilities=[
                AnalysisCapability.QUANTITY_TAKEOFF,
                AnalysisCapability.MEASUREMENT,
                AnalysisCapability.NOTES_EXTRACTION,
                AnalysisCapability.METADATA_EXTRACTION,
                AnalysisCapability.FINDING_REFERENCES,
            ],
            analysis_prompt=GENERIC_ANALYSIS_PROMPT,
            priority=-1,
        )

    def _register_default_skills(self):
        """Register the default set of skills"""
        # Generic skill (fallback)
        self.register(self._create_generic_skill())

        # Structural skills
        self.register(DrawingSkill(
            name="structural_framing",
            drawing_types=["framing_plan", "plan", "layout"],
            disciplines=["structural"],
            description="Analyzes structural framing plans for steel/concrete members",
            capabilities=[
                AnalysisCapability.QUANTITY_TAKEOFF,
                AnalysisCapability.MEASUREMENT,
                AnalysisCapability.NOTES_EXTRACTION,
                AnalysisCapability.FINDING_REFERENCES,
            ],
            analysis_prompt=STRUCTURAL_FRAMING_PROMPT,
            priority=10,
        ))

        self.register(DrawingSkill(
            name="structural_detail",
            drawing_types=["detail", "section"],
            disciplines=["structural"],
            description="Analyzes structural details and sections",
            capabilities=[
                AnalysisCapability.QUANTITY_TAKEOFF,
                AnalysisCapability.MEASUREMENT,
                AnalysisCapability.NOTES_EXTRACTION,
            ],
            analysis_prompt=STRUCTURAL_DETAIL_PROMPT,
            priority=10,
        ))

        # Architectural skills
        self.register(DrawingSkill(
            name="architectural_plan",
            drawing_types=["floor_plan", "plan", "layout"],
            disciplines=["architectural"],
            description="Analyzes architectural floor plans",
            capabilities=[
                AnalysisCapability.QUANTITY_TAKEOFF,
                AnalysisCapability.MEASUREMENT,
                AnalysisCapability.NOTES_EXTRACTION,
                AnalysisCapability.FINDING_REFERENCES,
            ],
            analysis_prompt=ARCHITECTURAL_PLAN_PROMPT,
            priority=10,
        ))

        # MEP skills
        self.register(DrawingSkill(
            name="piping_isometric",
            drawing_types=["isometric"],
            disciplines=["piping", "mechanical", "plumbing"],
            description="Analyzes piping isometric drawings",
            capabilities=[
                AnalysisCapability.QUANTITY_TAKEOFF,
                AnalysisCapability.MEASUREMENT,
                AnalysisCapability.NOTES_EXTRACTION,
            ],
            analysis_prompt=PIPING_ISOMETRIC_PROMPT,
            priority=15,
        ))

        self.register(DrawingSkill(
            name="pid_diagram",
            drawing_types=["P&ID", "schematic"],
            disciplines=["piping", "process", "instrumentation"],
            description="Analyzes P&ID and process diagrams",
            capabilities=[
                AnalysisCapability.SYMBOL_RECOGNITION,
                AnalysisCapability.FINDING_REFERENCES,
                AnalysisCapability.NOTES_EXTRACTION,
            ],
            analysis_prompt=PID_PROMPT,
            priority=15,
        ))

        # Electrical skills
        self.register(DrawingSkill(
            name="electrical_sld",
            drawing_types=["SLD", "single_line_diagram", "schematic"],
            disciplines=["electrical"],
            description="Analyzes electrical single line diagrams",
            capabilities=[
                AnalysisCapability.SYMBOL_RECOGNITION,
                AnalysisCapability.FINDING_REFERENCES,
                AnalysisCapability.NOTES_EXTRACTION,
                AnalysisCapability.QUANTITY_TAKEOFF,
            ],
            analysis_prompt=ELECTRICAL_SLD_PROMPT,
            priority=15,
        ))

        # Schedule skill
        self.register(DrawingSkill(
            name="schedule_extraction",
            drawing_types=["schedule"],
            disciplines=["*"],
            description="Extracts tabular schedule data",
            capabilities=[
                AnalysisCapability.SCHEDULE_EXTRACTION,
                AnalysisCapability.QUANTITY_TAKEOFF,
            ],
            analysis_prompt=SCHEDULE_EXTRACTION_PROMPT,
            priority=20,
        ))


# ============================================================================
# ANALYSIS PROMPTS
# ============================================================================

GENERIC_ANALYSIS_PROMPT = """Analyze this technical drawing region and extract all relevant information.

You are looking at a portion of a technical/construction drawing. Your task is to:

1. QUANTITIES - Identify and count any items that can be quantified:
   - Equipment, fixtures, components
   - Materials (lengths, areas, counts)
   - Structural members (beams, columns, etc.)

2. MEASUREMENTS - Extract all dimensions and measurements:
   - Linear dimensions (length, width, height)
   - Area dimensions
   - Angles, radii, etc.

3. NOTES - Extract all text notes and annotations:
   - General notes
   - Specifications
   - Instructions
   - Warnings

4. CALLOUTS - Identify drawing references and callouts:
   - Detail references (e.g., "1/S-101")
   - Section markers
   - Drawing cross-references

5. METADATA - Extract any drawing metadata visible:
   - Drawing numbers
   - Revision information
   - Scale information

For each item, include its approximate location (as a bounding box percentage from 0-1).

Respond with JSON in this format:
{
    "confidence": <0.0-1.0>,
    "complexity": <0.0-1.0>,
    "quantities": [
        {"description": "...", "quantity": N, "unit": "...", "location": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}, "confidence": 0.0-1.0}
    ],
    "measurements": [
        {"value": N, "unit": "...", "label": "...", "location": {...}, "confidence": 0.0-1.0}
    ],
    "notes": [
        {"content": "...", "type": "general|specification|instruction|warning|reference", "location": {...}}
    ],
    "callouts": [
        {"id": "...", "description": "...", "target": "...", "location": {...}}
    ],
    "metadata": {
        "drawing_number": "...",
        "revision": "...",
        "scale": "...",
        "other": {}
    }
}"""

STRUCTURAL_FRAMING_PROMPT = """Analyze this structural framing plan region.

Focus on identifying:

1. STRUCTURAL MEMBERS:
   - Beams (W-shapes, HSS, channels) - note size designations like W12x26, HSS6x4x1/4
   - Columns - note sizes and grid locations
   - Joists - note designations and spacing
   - Decking - note gauge and type

2. QUANTITIES:
   - Count of each member type
   - Linear footage of beams
   - Square footage of deck areas
   - Number of connections

3. DIMENSIONS:
   - Span lengths
   - Bay sizes
   - Member spacing
   - Elevation marks

4. CONNECTIONS & DETAILS:
   - Connection types
   - Detail references
   - Special conditions

5. NOTES:
   - Structural specifications
   - Material grades (A992, A36, etc.)
   - Special requirements

Respond with JSON in the standard format with quantities, measurements, notes, callouts, and metadata.
Include CSI division codes where applicable (05 for structural steel, 03 for concrete)."""

STRUCTURAL_DETAIL_PROMPT = """Analyze this structural detail drawing.

Focus on identifying:

1. MATERIALS & COMPONENTS:
   - Steel members and sizes
   - Concrete elements
   - Reinforcing (rebar sizes, spacing)
   - Hardware (bolts, welds, anchors)

2. DIMENSIONS:
   - All dimensions shown
   - Edge distances
   - Embed depths
   - Clearances

3. SPECIFICATIONS:
   - Material grades
   - Weld symbols and sizes
   - Bolt specifications
   - Concrete strength

4. QUANTITIES:
   - Count of bolts/anchors
   - Length of welds
   - Rebar quantities

Respond with JSON in the standard format."""

ARCHITECTURAL_PLAN_PROMPT = """Analyze this architectural floor plan region.

Focus on identifying:

1. SPACES & AREAS:
   - Room names and numbers
   - Area calculations
   - Space functions

2. BUILDING ELEMENTS:
   - Walls (types, thicknesses)
   - Doors (sizes, types, hardware sets)
   - Windows (sizes, types)
   - Stairs, elevators

3. DIMENSIONS:
   - Room dimensions
   - Overall dimensions
   - Door/window sizes

4. FINISHES & NOTES:
   - Floor finishes
   - Wall finishes
   - Ceiling heights
   - Specifications

5. REFERENCES:
   - Interior elevations
   - Detail references
   - Door/window schedules

Respond with JSON in the standard format."""

PIPING_ISOMETRIC_PROMPT = """Analyze this piping isometric drawing.

Focus on identifying:

1. PIPE SPECIFICATIONS:
   - Pipe sizes (NPS)
   - Pipe materials and schedules
   - Insulation requirements

2. FITTINGS:
   - Elbows (count by size and type)
   - Tees, reducers, caps
   - Flanges

3. VALVES:
   - Valve types (gate, globe, ball, check, etc.)
   - Valve sizes
   - Valve tags

4. DIMENSIONS:
   - Pipe lengths
   - Elevation changes
   - Tie-in points

5. INSTRUMENTATION:
   - Instrument connections
   - Flow elements
   - Pressure/temp points

Respond with JSON including pipe footage by size and fitting counts."""

PID_PROMPT = """Analyze this P&ID (Piping and Instrumentation Diagram) region.

Focus on identifying:

1. EQUIPMENT:
   - Vessels, tanks, pumps, compressors
   - Equipment tags and descriptions
   - Operating conditions

2. INSTRUMENTS:
   - Instrument tags (following ISA format)
   - Instrument types (FT, LT, PT, TT, etc.)
   - Control valves

3. PIPING:
   - Line numbers
   - Line specifications
   - Process connections

4. CONTROL SYSTEMS:
   - Control loops
   - Interlocks
   - Safety systems (SIS, PSV)

Respond with JSON focusing on equipment and instrument lists."""

ELECTRICAL_SLD_PROMPT = """Analyze this electrical single line diagram.

Focus on identifying:

1. EQUIPMENT:
   - Transformers (kVA ratings, voltages)
   - Switchgear and switchboards
   - Motor control centers
   - Panels

2. PROTECTIVE DEVICES:
   - Circuit breakers (frame/trip ratings)
   - Fuses
   - Relays

3. FEEDERS:
   - Cable/conduit sizes
   - Feeder designations
   - Voltage levels

4. LOADS:
   - Motor loads (HP, FLA)
   - Connected loads
   - Demand factors

Respond with JSON including equipment schedules and protection coordination."""

SCHEDULE_EXTRACTION_PROMPT = """Extract all tabular/schedule data from this region.

This appears to be a schedule (table) from a technical drawing. Extract:

1. COLUMN HEADERS:
   - All column names/titles

2. ROW DATA:
   - All row entries
   - Preserve the relationship between columns and values

3. TOTALS/SUMMARIES:
   - Any subtotals or totals
   - Summary information

4. NOTES:
   - Schedule notes
   - Footnotes
   - Abbreviations/legends

Respond with JSON in this format:
{
    "schedule_type": "door|window|equipment|finish|other",
    "columns": ["col1", "col2", ...],
    "rows": [
        {"col1": "value1", "col2": "value2", ...},
        ...
    ],
    "notes": ["note1", "note2", ...],
    "confidence": 0.0-1.0,
    "complexity": 0.0-1.0
}"""
