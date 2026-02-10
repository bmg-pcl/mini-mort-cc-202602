"""Tests for the deduplication module"""
import pytest
from src.core.schema import (
    BoundingBox,
    QuantityItem,
    QuantityCategory,
    UnitOfMeasure,
    Measurement,
    NoteExtraction,
    CalloutExtraction,
)
from src.convolution.deduplication import ElementDeduplicator


@pytest.fixture
def deduplicator():
    return ElementDeduplicator(iou_threshold=0.5, text_similarity_threshold=0.8)


def test_calculate_iou_no_overlap(deduplicator):
    """Test IoU calculation with no overlap"""
    box1 = BoundingBox(x1=0.0, y1=0.0, x2=0.3, y2=0.3)
    box2 = BoundingBox(x1=0.5, y1=0.5, x2=0.8, y2=0.8)
    assert deduplicator.calculate_iou(box1, box2) == 0.0


def test_calculate_iou_partial_overlap(deduplicator):
    """Test IoU calculation with partial overlap"""
    box1 = BoundingBox(x1=0.0, y1=0.0, x2=0.5, y2=0.5)
    box2 = BoundingBox(x1=0.25, y1=0.25, x2=0.75, y2=0.75)
    iou = deduplicator.calculate_iou(box1, box2)
    assert 0.0 < iou < 1.0


def test_calculate_iou_full_overlap(deduplicator):
    """Test IoU calculation with full overlap"""
    box1 = BoundingBox(x1=0.2, y1=0.2, x2=0.8, y2=0.8)
    box2 = BoundingBox(x1=0.2, y1=0.2, x2=0.8, y2=0.8)
    assert deduplicator.calculate_iou(box1, box2) == 1.0


def test_text_similarity(deduplicator):
    """Test text similarity calculation"""
    assert deduplicator.text_similarity("hello", "hello") == 1.0
    assert deduplicator.text_similarity("hello", "HELLO") == 1.0
    assert deduplicator.text_similarity("hello", "world") < 0.5
    assert deduplicator.text_similarity("W12x26 Beam", "W12x26 Steel Beam") > 0.7


def test_deduplicate_quantities(deduplicator):
    """Test deduplicating quantity items"""
    quantities = [
        QuantityItem(
            id="q1",
            description="W12x26 Steel Beam",
            category=QuantityCategory(level1="Structural"),
            quantity=10,
            unit=UnitOfMeasure.LINEAR_FEET,
            source_drawing="test.pdf",
            source_bbox=BoundingBox(x1=0.1, y1=0.1, x2=0.3, y2=0.3),
            confidence=0.9,
        ),
        QuantityItem(
            id="q2",
            description="W12x26 Steel Beam",  # Same description
            category=QuantityCategory(level1="Structural"),
            quantity=10,
            unit=UnitOfMeasure.LINEAR_FEET,
            source_drawing="test.pdf",
            source_bbox=BoundingBox(x1=0.15, y1=0.15, x2=0.35, y2=0.35),  # Overlapping
            confidence=0.8,
        ),
        QuantityItem(
            id="q3",
            description="W14x30 Steel Beam",  # Different
            category=QuantityCategory(level1="Structural"),
            quantity=5,
            unit=UnitOfMeasure.LINEAR_FEET,
            source_drawing="test.pdf",
            source_bbox=BoundingBox(x1=0.5, y1=0.5, x2=0.7, y2=0.7),
            confidence=0.85,
        ),
    ]

    result = deduplicator.deduplicate_quantities(quantities)

    # Should have 2 unique items (q1 and q3, q2 is duplicate of q1)
    assert len(result) == 2
    # Higher confidence item should be kept
    assert result[0].id == "q1"
    assert result[0].confidence == 0.9


def test_deduplicate_callouts(deduplicator):
    """Test deduplicating callouts"""
    callouts = [
        CalloutExtraction(
            id="c1",
            callout_id="A",
            source_bbox=BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2),
        ),
        CalloutExtraction(
            id="c2",
            callout_id="A",  # Same callout ID
            source_bbox=BoundingBox(x1=0.12, y1=0.12, x2=0.22, y2=0.22),  # Overlapping
        ),
        CalloutExtraction(
            id="c3",
            callout_id="B",  # Different callout
            source_bbox=BoundingBox(x1=0.5, y1=0.5, x2=0.6, y2=0.6),
        ),
    ]

    result = deduplicator.deduplicate_callouts(callouts)

    # Should have 2 unique callouts (A and B)
    assert len(result) == 2
    callout_ids = {c.callout_id for c in result}
    assert callout_ids == {"A", "B"}


def test_merge_quantities(deduplicator):
    """Test merging quantities instead of deduplicating"""
    quantities = [
        QuantityItem(
            id="q1",
            description="Bolt",
            category=QuantityCategory(level1="Hardware"),
            quantity=10,
            unit=UnitOfMeasure.EACH,
            source_drawing="test.pdf",
            confidence=0.9,
        ),
        QuantityItem(
            id="q2",
            description="Bolt",
            category=QuantityCategory(level1="Hardware"),
            quantity=15,
            unit=UnitOfMeasure.EACH,
            source_drawing="test.pdf",
            confidence=0.8,
        ),
    ]

    result = deduplicator.merge_quantities(quantities)

    assert len(result) == 1
    assert result[0].quantity == 25  # Summed
    assert result[0].confidence == 0.9  # Max confidence
