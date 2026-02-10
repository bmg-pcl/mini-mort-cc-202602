"""
Output schema for drawing analysis results.

Designed to support:
- Multi-segment categorization for quantities
- Units of measure
- Relationships and annotations on quantity breakdowns
- Traceability to source documents
- Flags for manual review and verification
- Excel export and web app compatibility
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class BoundingBox(BaseModel):
    """Bounding box coordinates for an element"""
    x1: float = Field(..., description="Left coordinate (0-1 normalized)")
    y1: float = Field(..., description="Top coordinate (0-1 normalized)")
    x2: float = Field(..., description="Right coordinate (0-1 normalized)")
    y2: float = Field(..., description="Bottom coordinate (0-1 normalized)")

    @property
    def centroid(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


class ElementType(str, Enum):
    """Types of elements extracted from drawings"""
    TEXT = "text"
    ANNOTATION = "annotation"
    DIMENSION = "dimension"
    SYMBOL = "symbol"
    LINE = "line"
    SHAPE = "shape"
    TABLE = "table"
    TITLEBLOCK = "titleblock"
    CALLOUT = "callout"
    LEADER = "leader"
    REVISION = "revision"
    NOTE = "note"
    REFERENCE = "reference"


class ContainmentType(str, Enum):
    """Whether element is contained in kernel or external/adjacent"""
    CONTAINED = "contained"
    CROPPED = "cropped"
    EXTERNAL = "external"


class DrawingElement(BaseModel):
    """Individual element extracted from a drawing"""
    id: str = Field(..., description="Unique identifier for the element")
    type: ElementType
    content: str = Field(..., description="Text content or drawing instruction")
    bbox: BoundingBox
    containment: Optional[ContainmentType] = None
    confidence: float = Field(0.0, ge=0, le=1, description="Extraction confidence")
    page: int = Field(1, description="Page number in source document")
    layer: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class UnitOfMeasure(str, Enum):
    """Standard units of measure for quantities"""
    # Length
    EACH = "ea"
    LINEAR_FEET = "lf"
    LINEAR_METERS = "lm"
    INCHES = "in"
    MILLIMETERS = "mm"
    # Area
    SQUARE_FEET = "sf"
    SQUARE_METERS = "sm"
    # Volume
    CUBIC_FEET = "cf"
    CUBIC_METERS = "cm"
    CUBIC_YARDS = "cy"
    # Weight
    POUNDS = "lbs"
    KILOGRAMS = "kg"
    TONS = "ton"
    # Other
    PERCENT = "pct"
    LUMP_SUM = "ls"
    ALLOWANCE = "allow"


class VerificationStatus(str, Enum):
    """Status of manual verification"""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    FLAGGED = "flagged"
    REQUIRES_REVIEW = "requires_review"


class QuantityCategory(BaseModel):
    """Multi-segment categorization for quantities"""
    level1: str = Field(..., description="Top-level category (e.g., 'Structural')")
    level2: Optional[str] = Field(None, description="Sub-category (e.g., 'Steel')")
    level3: Optional[str] = Field(None, description="Detail category (e.g., 'Beams')")
    level4: Optional[str] = Field(None, description="Specific item (e.g., 'W12x26')")
    csi_division: Optional[str] = Field(None, description="CSI MasterFormat division")
    uniformat: Optional[str] = Field(None, description="UniFormat classification")


class QuantityItem(BaseModel):
    """A single quantity takeoff item"""
    id: str = Field(..., description="Unique identifier")
    description: str = Field(..., description="Item description")
    category: QuantityCategory
    quantity: float = Field(..., description="Measured/counted quantity")
    unit: UnitOfMeasure

    # Traceability
    source_drawing: str = Field(..., description="Source drawing reference")
    source_page: int = Field(1, description="Page in source document")
    source_bbox: Optional[BoundingBox] = Field(None, description="Location on drawing")
    source_elements: list[str] = Field(default_factory=list, description="Related element IDs")

    # Verification
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_notes: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

    # Annotations and relationships
    notes: list[str] = Field(default_factory=list)
    related_items: list[str] = Field(default_factory=list, description="Related quantity item IDs")
    breakdown_parent: Optional[str] = Field(None, description="Parent item ID for breakdowns")

    # AI analysis metadata
    confidence: float = Field(0.0, ge=0, le=1)
    extraction_method: str = Field("ai_vision", description="How quantity was determined")

    # For downstream allocation (rates, factoring, risk premiums)
    custom_fields: dict = Field(default_factory=dict, description="Extensible fields for downstream use")


class Measurement(BaseModel):
    """A measurement extracted from the drawing"""
    id: str
    value: float
    unit: UnitOfMeasure
    label: Optional[str] = None
    source_bbox: BoundingBox
    confidence: float = Field(0.0, ge=0, le=1)
    related_elements: list[str] = Field(default_factory=list)


class NoteExtraction(BaseModel):
    """A note or annotation extracted from the drawing"""
    id: str
    content: str
    note_type: Literal["general", "specification", "instruction", "warning", "reference"]
    source_bbox: BoundingBox
    related_elements: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CalloutExtraction(BaseModel):
    """A callout or reference extracted from the drawing"""
    id: str
    callout_id: str = Field(..., description="The callout identifier (e.g., 'A', '1', 'DET-01')")
    description: Optional[str] = None
    target_drawing: Optional[str] = None
    target_detail: Optional[str] = None
    source_bbox: BoundingBox


class DrawingMetadata(BaseModel):
    """Metadata about the drawing itself"""
    drawing_number: Optional[str] = None
    drawing_title: Optional[str] = None
    revision: Optional[str] = None
    revision_date: Optional[str] = None
    scale: Optional[str] = None
    project_name: Optional[str] = None
    project_number: Optional[str] = None
    discipline: Optional[str] = None
    drawn_by: Optional[str] = None
    checked_by: Optional[str] = None
    approved_by: Optional[str] = None
    sheet_size: Optional[str] = None
    custom_fields: dict = Field(default_factory=dict)


class DrawingClassification(BaseModel):
    """Classification of the drawing type and discipline"""
    drawing_type: str = Field(..., description="Type: layout, GA, P&ID, SLD, isometric, sectional, etc.")
    discipline: str = Field(..., description="Discipline: civil, structural, piping, electrical, architectural, etc.")
    sub_type: Optional[str] = None
    confidence: float = Field(0.0, ge=0, le=1)


class ConvolutionKernel(BaseModel):
    """A convolutional kernel/window used for analysis"""
    kernel_id: str
    bbox: BoundingBox
    pixel_size: tuple[int, int] = Field(..., description="NxM pixel dimensions")
    elements_in_kernel: list[DrawingElement] = Field(default_factory=list)
    complexity_rating: float = Field(0.0, ge=0, le=1)
    analysis_confidence: float = Field(0.0, ge=0, le=1)


class AnalysisResult(BaseModel):
    """Complete analysis result for a drawing"""
    # Source information
    source_file: str
    source_hash: Optional[str] = None
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    analyzer_version: str = "0.1.0"

    # Classification
    classification: DrawingClassification
    metadata: DrawingMetadata

    # Extracted elements
    elements: list[DrawingElement] = Field(default_factory=list)

    # Analysis outputs
    quantities: list[QuantityItem] = Field(default_factory=list)
    measurements: list[Measurement] = Field(default_factory=list)
    notes: list[NoteExtraction] = Field(default_factory=list)
    callouts: list[CalloutExtraction] = Field(default_factory=list)

    # Convolution tracking
    kernels_analyzed: list[ConvolutionKernel] = Field(default_factory=list)

    # Summary statistics
    total_elements: int = 0
    total_quantities: int = 0
    average_confidence: float = 0.0
    requires_review_count: int = 0

    def to_table_format(self) -> list[dict]:
        """Convert quantities to a flat table format suitable for Excel"""
        rows = []
        for q in self.quantities:
            row = {
                "ID": q.id,
                "Description": q.description,
                "Category L1": q.category.level1,
                "Category L2": q.category.level2 or "",
                "Category L3": q.category.level3 or "",
                "Category L4": q.category.level4 or "",
                "CSI Division": q.category.csi_division or "",
                "UniFormat": q.category.uniformat or "",
                "Quantity": q.quantity,
                "Unit": q.unit.value,
                "Source Drawing": q.source_drawing,
                "Source Page": q.source_page,
                "Confidence": q.confidence,
                "Verification Status": q.verification_status.value,
                "Notes": "; ".join(q.notes),
            }
            # Add custom fields
            for k, v in q.custom_fields.items():
                row[f"Custom_{k}"] = v
            rows.append(row)
        return rows
