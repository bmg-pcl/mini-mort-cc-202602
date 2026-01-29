"""
Element Deduplication

Handles deduplication of elements detected across overlapping convolutional windows.
Uses IoU (Intersection over Union) and content similarity to identify duplicates.
"""
from typing import TypeVar, Callable
from difflib import SequenceMatcher

from ..core.schema import (
    BoundingBox,
    QuantityItem,
    Measurement,
    NoteExtraction,
    CalloutExtraction,
)


T = TypeVar('T')


class ElementDeduplicator:
    """
    Deduplicates elements found across overlapping kernel windows.

    Uses a combination of:
    - Spatial overlap (IoU - Intersection over Union)
    - Content similarity (for text-based elements)
    - Exact matching for callout IDs

    When duplicates are found, prefers the one with higher confidence.
    """

    def __init__(self, iou_threshold: float = 0.5, text_similarity_threshold: float = 0.8):
        """
        Args:
            iou_threshold: IoU threshold for considering boxes as duplicates
            text_similarity_threshold: Text similarity threshold for considering content as duplicate
        """
        self.iou_threshold = iou_threshold
        self.text_similarity_threshold = text_similarity_threshold

    def calculate_iou(self, box1: BoundingBox, box2: BoundingBox) -> float:
        """Calculate Intersection over Union between two bounding boxes"""
        # Calculate intersection
        x1 = max(box1.x1, box2.x1)
        y1 = max(box1.y1, box2.y1)
        x2 = min(box1.x2, box2.x2)
        y2 = min(box1.y2, box2.y2)

        if x2 < x1 or y2 < y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)

        # Calculate union
        area1 = (box1.x2 - box1.x1) * (box1.y2 - box1.y1)
        area2 = (box2.x2 - box2.x1) * (box2.y2 - box2.y1)
        union = area1 + area2 - intersection

        if union == 0:
            return 0.0

        return intersection / union

    def text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def deduplicate_quantities(self, quantities: list[QuantityItem]) -> list[QuantityItem]:
        """
        Deduplicate quantity items.

        Considers items as duplicates if they have:
        - High IoU (overlapping spatial location)
        - Similar descriptions
        """
        if not quantities:
            return []

        result = []
        used = set()

        # Sort by confidence (prefer higher confidence items)
        sorted_quantities = sorted(
            enumerate(quantities),
            key=lambda x: x[1].confidence,
            reverse=True
        )

        for idx, item in sorted_quantities:
            if idx in used:
                continue

            # Check against all remaining items
            for other_idx, other_item in sorted_quantities:
                if other_idx <= idx or other_idx in used:
                    continue

                is_duplicate = self._are_quantities_duplicate(item, other_item)
                if is_duplicate:
                    used.add(other_idx)
                    # Merge quantities if they're duplicates
                    # (keep the higher confidence one, but could also sum)

            result.append(item)
            used.add(idx)

        return result

    def _are_quantities_duplicate(self, q1: QuantityItem, q2: QuantityItem) -> bool:
        """Check if two quantity items are duplicates"""
        # Check description similarity
        desc_similarity = self.text_similarity(q1.description, q2.description)
        if desc_similarity < self.text_similarity_threshold:
            return False

        # Check spatial overlap if both have bboxes
        if q1.source_bbox and q2.source_bbox:
            iou = self.calculate_iou(q1.source_bbox, q2.source_bbox)
            if iou < self.iou_threshold:
                return False

        # Check if same category
        if q1.category.level1 != q2.category.level1:
            return False

        # Check if same unit (quantities of different units are different items)
        if q1.unit != q2.unit:
            return False

        return True

    def deduplicate_measurements(self, measurements: list[Measurement]) -> list[Measurement]:
        """
        Deduplicate measurements.

        Considers measurements as duplicates if they have:
        - High IoU (overlapping location)
        - Same value (within tolerance)
        - Same unit
        """
        if not measurements:
            return []

        result = []
        used = set()

        # Sort by confidence
        sorted_measurements = sorted(
            enumerate(measurements),
            key=lambda x: x[1].confidence,
            reverse=True
        )

        for idx, item in sorted_measurements:
            if idx in used:
                continue

            for other_idx, other_item in sorted_measurements:
                if other_idx <= idx or other_idx in used:
                    continue

                is_duplicate = self._are_measurements_duplicate(item, other_item)
                if is_duplicate:
                    used.add(other_idx)

            result.append(item)
            used.add(idx)

        return result

    def _are_measurements_duplicate(self, m1: Measurement, m2: Measurement) -> bool:
        """Check if two measurements are duplicates"""
        # Check spatial overlap
        iou = self.calculate_iou(m1.source_bbox, m2.source_bbox)
        if iou < self.iou_threshold:
            return False

        # Check value similarity (within 1%)
        if m1.value > 0 and m2.value > 0:
            value_diff = abs(m1.value - m2.value) / max(m1.value, m2.value)
            if value_diff > 0.01:
                return False

        # Check unit
        if m1.unit != m2.unit:
            return False

        return True

    def deduplicate_notes(self, notes: list[NoteExtraction]) -> list[NoteExtraction]:
        """
        Deduplicate notes.

        Considers notes as duplicates if they have:
        - High text similarity
        - Overlapping locations
        """
        if not notes:
            return []

        result = []
        used = set()

        for idx, note in enumerate(notes):
            if idx in used:
                continue

            for other_idx, other_note in enumerate(notes):
                if other_idx <= idx or other_idx in used:
                    continue

                is_duplicate = self._are_notes_duplicate(note, other_note)
                if is_duplicate:
                    used.add(other_idx)

            result.append(note)
            used.add(idx)

        return result

    def _are_notes_duplicate(self, n1: NoteExtraction, n2: NoteExtraction) -> bool:
        """Check if two notes are duplicates"""
        # Check text similarity
        text_similarity = self.text_similarity(n1.content, n2.content)
        if text_similarity < self.text_similarity_threshold:
            return False

        # Check spatial overlap
        iou = self.calculate_iou(n1.source_bbox, n2.source_bbox)
        if iou < self.iou_threshold * 0.5:  # Lower threshold for notes
            return False

        return True

    def deduplicate_callouts(self, callouts: list[CalloutExtraction]) -> list[CalloutExtraction]:
        """
        Deduplicate callouts.

        Considers callouts as duplicates if they have the same callout_id
        and similar locations.
        """
        if not callouts:
            return []

        result = []
        seen_ids = {}  # Map of callout_id -> best CalloutExtraction

        for callout in callouts:
            if callout.callout_id in seen_ids:
                existing = seen_ids[callout.callout_id]
                # Check if this is a true duplicate (same location)
                iou = self.calculate_iou(callout.source_bbox, existing.source_bbox)
                if iou >= self.iou_threshold:
                    continue  # Skip this duplicate
                else:
                    # Same ID but different location - keep both
                    result.append(callout)
            else:
                seen_ids[callout.callout_id] = callout
                result.append(callout)

        return result

    def merge_quantities(self, quantities: list[QuantityItem]) -> list[QuantityItem]:
        """
        Merge quantities with the same description and category.

        Instead of deduplicating (removing), this sums quantities.
        Useful for items that appear multiple times across the drawing.
        """
        if not quantities:
            return []

        # Group by key
        groups: dict[tuple, list[QuantityItem]] = {}

        for q in quantities:
            key = (
                q.description.lower().strip(),
                q.category.level1,
                q.category.level2,
                q.category.level3,
                q.unit.value,
            )
            if key not in groups:
                groups[key] = []
            groups[key].append(q)

        # Merge each group
        result = []
        for key, group in groups.items():
            if len(group) == 1:
                result.append(group[0])
            else:
                # Sum quantities, keep highest confidence metadata
                merged = group[0].model_copy()
                merged.quantity = sum(q.quantity for q in group)
                merged.confidence = max(q.confidence for q in group)
                merged.source_elements = []
                for q in group:
                    merged.source_elements.extend(q.source_elements)
                merged.notes = list(set(
                    note for q in group for note in q.notes
                ))
                result.append(merged)

        return result
