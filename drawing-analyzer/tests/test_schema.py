"""Tests for the schema module"""
import pytest
from src.core.schema import (
    BoundingBox,
    QuantityItem,
    QuantityCategory,
    UnitOfMeasure,
    VerificationStatus,
    AnalysisResult,
    DrawingClassification,
    DrawingMetadata,
)


def test_bounding_box_centroid():
    """Test bounding box centroid calculation"""
    bbox = BoundingBox(x1=0.0, y1=0.0, x2=1.0, y2=1.0)
    assert bbox.centroid == (0.5, 0.5)

    bbox2 = BoundingBox(x1=0.2, y1=0.3, x2=0.6, y2=0.7)
    assert bbox2.centroid == (0.4, 0.5)


def test_bounding_box_dimensions():
    """Test bounding box width and height"""
    bbox = BoundingBox(x1=0.1, y1=0.2, x2=0.5, y2=0.8)
    assert bbox.width == pytest.approx(0.4)
    assert bbox.height == pytest.approx(0.6)


def test_quantity_item_creation():
    """Test creating a quantity item"""
    item = QuantityItem(
        id="q001",
        description="W12x26 Steel Beam",
        category=QuantityCategory(
            level1="Structural",
            level2="Steel",
            level3="Beams",
            csi_division="05 12 00",
        ),
        quantity=15,
        unit=UnitOfMeasure.LINEAR_FEET,
        source_drawing="S-101",
        source_page=1,
        confidence=0.85,
    )

    assert item.description == "W12x26 Steel Beam"
    assert item.quantity == 15
    assert item.unit == UnitOfMeasure.LINEAR_FEET
    assert item.verification_status == VerificationStatus.UNVERIFIED
    assert item.category.csi_division == "05 12 00"


def test_analysis_result_to_table():
    """Test converting analysis result to table format"""
    result = AnalysisResult(
        source_file="test.pdf",
        classification=DrawingClassification(
            drawing_type="plan",
            discipline="structural",
            confidence=0.9,
        ),
        metadata=DrawingMetadata(),
    )

    # Add some quantities
    result.quantities.append(QuantityItem(
        id="q001",
        description="Test Item",
        category=QuantityCategory(level1="General"),
        quantity=10,
        unit=UnitOfMeasure.EACH,
        source_drawing="test.pdf",
        confidence=0.8,
    ))

    table = result.to_table_format()
    assert len(table) == 1
    assert table[0]["Description"] == "Test Item"
    assert table[0]["Quantity"] == 10
    assert table[0]["Unit"] == "ea"


def test_unit_of_measure_values():
    """Test unit of measure enum values"""
    assert UnitOfMeasure.EACH.value == "ea"
    assert UnitOfMeasure.LINEAR_FEET.value == "lf"
    assert UnitOfMeasure.SQUARE_FEET.value == "sf"
    assert UnitOfMeasure.CUBIC_YARDS.value == "cy"
