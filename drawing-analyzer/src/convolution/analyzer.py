"""
Convolutional Analyzer

Implements a sliding window (convolutional) approach to analyze technical drawings.
Handles kernel sizing, overlap, complexity-based resizing, and deduplication.
"""
import io
import json
import uuid
from dataclasses import dataclass, field
from typing import Iterator, Optional

from PIL import Image

from ..core.models import (
    APIConfig,
    APIProvider,
    ImageData,
    Thumbnail,
    ConvContext,
    SkillResult,
    AnalysisConfig,
)
from ..core.schema import (
    DrawingElement,
    BoundingBox,
    ContainmentType,
    ConvolutionKernel,
    QuantityItem,
    Measurement,
    NoteExtraction,
    CalloutExtraction,
    QuantityCategory,
    UnitOfMeasure,
    VerificationStatus,
)
from ..skills import get_skill_for_drawing, DrawingSkill
from .deduplication import ElementDeduplicator


@dataclass
class KernelPosition:
    """Position and size of a convolutional kernel"""
    x: int  # Pixel x position (top-left)
    y: int  # Pixel y position (top-left)
    width: int  # Kernel width in pixels
    height: int  # Kernel height in pixels

    # Normalized coordinates (0-1)
    norm_x1: float = 0.0
    norm_y1: float = 0.0
    norm_x2: float = 1.0
    norm_y2: float = 1.0


class ConvolutionalAnalyzer:
    """
    Analyzes drawings using a sliding window (convolutional) approach.

    For each kernel position:
    1. Crops the image to the kernel region
    2. Gathers context elements that are in or adjacent to the kernel
    3. Passes the CONV_CONTEXT to the API
    4. Collects results with confidence and complexity ratings
    5. If complexity is high, reduces kernel size and re-analyzes

    Handles deduplication to avoid double-counting elements across overlapping kernels.
    """

    def __init__(
        self,
        api_config: APIConfig,
        config: Optional[AnalysisConfig] = None,
    ):
        self.api_config = api_config
        self.config = config or AnalysisConfig()
        self.deduplicator = ElementDeduplicator(
            iou_threshold=self.config.dedup_iou_threshold
        )
        self._client = None

    @property
    def client(self):
        """Lazy-load API client"""
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

    def analyze(
        self,
        image: ImageData,
        thumbnail: Thumbnail,
        elements: list[DrawingElement],
        drawing_type: str,
        discipline: str,
    ) -> tuple[list[QuantityItem], list[Measurement], list[NoteExtraction], list[CalloutExtraction], list[ConvolutionKernel]]:
        """
        Analyze a drawing using convolutional approach.

        Args:
            image: Full resolution drawing image
            thumbnail: Low-res thumbnail
            elements: Pre-extracted elements (text, drawings, etc.)
            drawing_type: Classified drawing type
            discipline: Classified discipline

        Returns:
            Tuple of (quantities, measurements, notes, callouts, kernels_analyzed)
        """
        # Get the appropriate skill for this drawing
        skill = get_skill_for_drawing(drawing_type, discipline)

        # Generate kernel positions
        kernel_positions = list(self._generate_kernel_positions(
            image.width, image.height
        ))

        # Results accumulators
        all_quantities: list[QuantityItem] = []
        all_measurements: list[Measurement] = []
        all_notes: list[NoteExtraction] = []
        all_callouts: list[CalloutExtraction] = []
        kernels_analyzed: list[ConvolutionKernel] = []

        # Process each kernel
        for kernel_pos in kernel_positions:
            result, kernel_info = self._analyze_kernel(
                image, thumbnail, elements, skill, kernel_pos
            )

            if result:
                # Check complexity and potentially re-analyze with smaller kernel
                if (
                    result.complexity > self.config.complexity_threshold
                    and kernel_pos.width > self.config.min_kernel_size[0]
                ):
                    # Subdivide this kernel and re-analyze
                    sub_results = self._subdivide_and_analyze(
                        image, thumbnail, elements, skill, kernel_pos
                    )
                    for sub_result, sub_kernel in sub_results:
                        if sub_result:
                            self._accumulate_results(
                                sub_result, sub_kernel, kernel_pos,
                                all_quantities, all_measurements,
                                all_notes, all_callouts
                            )
                            kernels_analyzed.append(sub_kernel)
                else:
                    self._accumulate_results(
                        result, kernel_info, kernel_pos,
                        all_quantities, all_measurements,
                        all_notes, all_callouts
                    )
                    kernels_analyzed.append(kernel_info)

        # Deduplicate results
        all_quantities = self.deduplicator.deduplicate_quantities(all_quantities)
        all_measurements = self.deduplicator.deduplicate_measurements(all_measurements)
        all_notes = self.deduplicator.deduplicate_notes(all_notes)
        all_callouts = self.deduplicator.deduplicate_callouts(all_callouts)

        return all_quantities, all_measurements, all_notes, all_callouts, kernels_analyzed

    def _generate_kernel_positions(
        self, image_width: int, image_height: int
    ) -> Iterator[KernelPosition]:
        """
        Generate kernel positions for sliding window analysis.

        Uses overlap to ensure coverage of elements at kernel boundaries.
        """
        kernel_w, kernel_h = self.config.initial_kernel_size
        overlap = self.config.kernel_overlap

        # Calculate step sizes
        step_x = int(kernel_w * (1 - overlap))
        step_y = int(kernel_h * (1 - overlap))

        y = 0
        while y < image_height:
            x = 0
            while x < image_width:
                # Calculate actual kernel size (may be smaller at edges)
                actual_w = min(kernel_w, image_width - x)
                actual_h = min(kernel_h, image_height - y)

                yield KernelPosition(
                    x=x,
                    y=y,
                    width=actual_w,
                    height=actual_h,
                    norm_x1=x / image_width,
                    norm_y1=y / image_height,
                    norm_x2=(x + actual_w) / image_width,
                    norm_y2=(y + actual_h) / image_height,
                )

                x += step_x
            y += step_y

    def _analyze_kernel(
        self,
        image: ImageData,
        thumbnail: Thumbnail,
        elements: list[DrawingElement],
        skill: DrawingSkill,
        kernel_pos: KernelPosition,
    ) -> tuple[Optional[SkillResult], ConvolutionKernel]:
        """Analyze a single kernel region"""
        # Crop the image to the kernel region
        kernel_image = self._crop_image(image, kernel_pos)

        # Find elements in or adjacent to this kernel
        context_elements = self._find_context_elements(elements, kernel_pos)

        # Build the CONV_CONTEXT
        conv_context = ConvContext(
            thumbnail=thumbnail,
            kernel_image=kernel_image,
            kernel_bbox=(
                kernel_pos.norm_x1,
                kernel_pos.norm_y1,
                kernel_pos.norm_x2,
                kernel_pos.norm_y2,
            ),
            kernel_pixel_size=(kernel_pos.width, kernel_pos.height),
            elements_in_context=[
                {
                    "item": e.id,
                    "type": e.type.value,
                    "content": e.content,
                    "bbox": {
                        "x1": e.bbox.x1,
                        "y1": e.bbox.y1,
                        "x2": e.bbox.x2,
                        "y2": e.bbox.y2,
                    },
                    "centroid": e.bbox.centroid,
                    "containment": e.containment.value if e.containment else "unknown",
                }
                for e in context_elements
            ],
        )

        # Call the API
        result = self._call_api(conv_context, skill)

        # Build kernel info
        kernel_info = ConvolutionKernel(
            kernel_id=str(uuid.uuid4())[:8],
            bbox=BoundingBox(
                x1=kernel_pos.norm_x1,
                y1=kernel_pos.norm_y1,
                x2=kernel_pos.norm_x2,
                y2=kernel_pos.norm_y2,
            ),
            pixel_size=(kernel_pos.width, kernel_pos.height),
            elements_in_kernel=[e for e in context_elements if e.containment == ContainmentType.CONTAINED],
            complexity_rating=result.complexity if result else 0.0,
            analysis_confidence=result.confidence if result else 0.0,
        )

        return result, kernel_info

    def _crop_image(self, image: ImageData, kernel_pos: KernelPosition) -> ImageData:
        """Crop the image to the kernel region"""
        img = Image.open(io.BytesIO(image.data))

        # Crop
        cropped = img.crop((
            kernel_pos.x,
            kernel_pos.y,
            kernel_pos.x + kernel_pos.width,
            kernel_pos.y + kernel_pos.height,
        ))

        # Convert back to bytes
        buffer = io.BytesIO()
        cropped.save(buffer, format="PNG")

        return ImageData(
            data=buffer.getvalue(),
            width=kernel_pos.width,
            height=kernel_pos.height,
            format="png",
            page=image.page,
        )

    def _find_context_elements(
        self,
        elements: list[DrawingElement],
        kernel_pos: KernelPosition,
    ) -> list[DrawingElement]:
        """
        Find elements that are in or adjacent to the kernel.

        Sets the containment type for each element:
        - CONTAINED: Element is completely within the kernel
        - CROPPED: Element is partially within the kernel
        - EXTERNAL: Element is adjacent (within a margin) but outside
        """
        context = []
        margin = 0.05  # 5% margin for adjacent elements

        for elem in elements:
            # Check relationship between element bbox and kernel bbox
            elem_x1, elem_y1 = elem.bbox.x1, elem.bbox.y1
            elem_x2, elem_y2 = elem.bbox.x2, elem.bbox.y2

            kern_x1 = kernel_pos.norm_x1
            kern_y1 = kernel_pos.norm_y1
            kern_x2 = kernel_pos.norm_x2
            kern_y2 = kernel_pos.norm_y2

            # Check if completely contained
            if (
                elem_x1 >= kern_x1
                and elem_y1 >= kern_y1
                and elem_x2 <= kern_x2
                and elem_y2 <= kern_y2
            ):
                elem.containment = ContainmentType.CONTAINED
                context.append(elem)

            # Check if partially overlapping
            elif self._boxes_overlap(
                elem_x1, elem_y1, elem_x2, elem_y2,
                kern_x1, kern_y1, kern_x2, kern_y2
            ):
                elem.containment = ContainmentType.CROPPED
                context.append(elem)

            # Check if adjacent (within margin)
            elif self._boxes_overlap(
                elem_x1, elem_y1, elem_x2, elem_y2,
                kern_x1 - margin, kern_y1 - margin,
                kern_x2 + margin, kern_y2 + margin
            ):
                elem.containment = ContainmentType.EXTERNAL
                context.append(elem)

        return context

    def _boxes_overlap(
        self,
        x1a: float, y1a: float, x2a: float, y2a: float,
        x1b: float, y1b: float, x2b: float, y2b: float,
    ) -> bool:
        """Check if two bounding boxes overlap"""
        return not (x2a < x1b or x2b < x1a or y2a < y1b or y2b < y1a)

    def _call_api(
        self, conv_context: ConvContext, skill: DrawingSkill
    ) -> Optional[SkillResult]:
        """Call the API with the convolutional context"""
        try:
            if self.api_config.provider == APIProvider.OPENAI:
                return self._call_openai(conv_context, skill)
            elif self.api_config.provider == APIProvider.ANTHROPIC:
                return self._call_anthropic(conv_context, skill)
        except Exception as e:
            print(f"API call failed: {e}")
            return None

    def _call_openai(
        self, conv_context: ConvContext, skill: DrawingSkill
    ) -> Optional[SkillResult]:
        """Call OpenAI API"""
        # Build the prompt with context
        context_text = self._build_context_text(conv_context)
        full_prompt = f"{skill.analysis_prompt}\n\n{context_text}"

        response = self.client.chat.completions.create(
            model=self.api_config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": conv_context.thumbnail.image.data_url,
                                "detail": "low",
                            },
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": conv_context.kernel_image.data_url,
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=self.api_config.max_tokens,
            temperature=self.api_config.temperature,
        )

        return self._parse_skill_result(
            response.choices[0].message.content, skill.name
        )

    def _call_anthropic(
        self, conv_context: ConvContext, skill: DrawingSkill
    ) -> Optional[SkillResult]:
        """Call Anthropic API"""
        context_text = self._build_context_text(conv_context)
        full_prompt = f"{skill.analysis_prompt}\n\n{context_text}"

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
                                "media_type": "image/png",
                                "data": conv_context.thumbnail.image.base64,
                            },
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": conv_context.kernel_image.base64,
                            },
                        },
                        {"type": "text", "text": full_prompt},
                    ],
                }
            ],
        )

        return self._parse_skill_result(response.content[0].text, skill.name)

    def _build_context_text(self, conv_context: ConvContext) -> str:
        """Build context text describing the kernel and nearby elements"""
        lines = [
            "CONTEXT INFORMATION:",
            f"Kernel region: ({conv_context.kernel_bbox[0]:.2%}, {conv_context.kernel_bbox[1]:.2%}) to ({conv_context.kernel_bbox[2]:.2%}, {conv_context.kernel_bbox[3]:.2%})",
            f"Kernel size: {conv_context.kernel_pixel_size[0]}x{conv_context.kernel_pixel_size[1]} pixels",
            "",
            "Elements in/near this region:",
        ]

        for elem in conv_context.elements_in_context:
            containment = elem.get("containment", "unknown")
            lines.append(
                f"  - [{elem['type']}] {elem['content'][:50]}... "
                f"at ({elem['bbox']['x1']:.2%}, {elem['bbox']['y1']:.2%}) [{containment}]"
            )

        return "\n".join(lines)

    def _parse_skill_result(
        self, response_text: str, skill_name: str
    ) -> Optional[SkillResult]:
        """Parse API response into a SkillResult"""
        try:
            # Extract JSON from response
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text)

            return SkillResult(
                skill_name=skill_name,
                confidence=float(data.get("confidence", 0.5)),
                complexity=float(data.get("complexity", 0.5)),
                quantities=data.get("quantities", []),
                measurements=data.get("measurements", []),
                notes=data.get("notes", []),
                callouts=data.get("callouts", []),
                metadata=data.get("metadata", {}),
                raw_response=response_text if self.config.include_raw_responses else None,
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse API response: {e}")
            return SkillResult(
                skill_name=skill_name,
                confidence=0.0,
                complexity=0.0,
                raw_response=response_text,
            )

    def _subdivide_and_analyze(
        self,
        image: ImageData,
        thumbnail: Thumbnail,
        elements: list[DrawingElement],
        skill: DrawingSkill,
        kernel_pos: KernelPosition,
    ) -> list[tuple[Optional[SkillResult], ConvolutionKernel]]:
        """
        Subdivide a kernel into smaller kernels and analyze each.

        Used when complexity is too high for the current kernel size.
        """
        results = []

        # Divide into 4 sub-kernels
        half_w = kernel_pos.width // 2
        half_h = kernel_pos.height // 2

        sub_positions = [
            KernelPosition(
                x=kernel_pos.x,
                y=kernel_pos.y,
                width=half_w,
                height=half_h,
            ),
            KernelPosition(
                x=kernel_pos.x + half_w,
                y=kernel_pos.y,
                width=half_w,
                height=half_h,
            ),
            KernelPosition(
                x=kernel_pos.x,
                y=kernel_pos.y + half_h,
                width=half_w,
                height=half_h,
            ),
            KernelPosition(
                x=kernel_pos.x + half_w,
                y=kernel_pos.y + half_h,
                width=half_w,
                height=half_h,
            ),
        ]

        for sub_pos in sub_positions:
            # Update normalized coordinates
            sub_pos.norm_x1 = sub_pos.x / image.width
            sub_pos.norm_y1 = sub_pos.y / image.height
            sub_pos.norm_x2 = (sub_pos.x + sub_pos.width) / image.width
            sub_pos.norm_y2 = (sub_pos.y + sub_pos.height) / image.height

            result, kernel_info = self._analyze_kernel(
                image, thumbnail, elements, skill, sub_pos
            )
            results.append((result, kernel_info))

        return results

    def _accumulate_results(
        self,
        result: SkillResult,
        kernel_info: ConvolutionKernel,
        kernel_pos: KernelPosition,
        quantities: list[QuantityItem],
        measurements: list[Measurement],
        notes: list[NoteExtraction],
        callouts: list[CalloutExtraction],
    ):
        """Convert skill results to schema objects and accumulate"""
        # Convert quantities
        for q in result.quantities:
            location = q.get("location", {})
            category_data = q.get("category", {})

            quantities.append(QuantityItem(
                id=str(uuid.uuid4())[:8],
                description=q.get("description", "Unknown"),
                category=QuantityCategory(
                    level1=category_data.get("level1", "General"),
                    level2=category_data.get("level2"),
                    level3=category_data.get("level3"),
                    level4=category_data.get("level4"),
                    csi_division=category_data.get("csi_division"),
                    uniformat=category_data.get("uniformat"),
                ),
                quantity=float(q.get("quantity", 0)),
                unit=self._parse_unit(q.get("unit", "ea")),
                source_drawing="",  # Set by caller
                source_page=1,
                source_bbox=BoundingBox(
                    x1=location.get("x1", 0) * (kernel_pos.norm_x2 - kernel_pos.norm_x1) + kernel_pos.norm_x1,
                    y1=location.get("y1", 0) * (kernel_pos.norm_y2 - kernel_pos.norm_y1) + kernel_pos.norm_y1,
                    x2=location.get("x2", 1) * (kernel_pos.norm_x2 - kernel_pos.norm_x1) + kernel_pos.norm_x1,
                    y2=location.get("y2", 1) * (kernel_pos.norm_y2 - kernel_pos.norm_y1) + kernel_pos.norm_y1,
                ) if location else None,
                confidence=float(q.get("confidence", result.confidence)),
                verification_status=VerificationStatus.UNVERIFIED,
            ))

        # Convert measurements
        for m in result.measurements:
            location = m.get("location", {})
            measurements.append(Measurement(
                id=str(uuid.uuid4())[:8],
                value=float(m.get("value", 0)),
                unit=self._parse_unit(m.get("unit", "in")),
                label=m.get("label"),
                source_bbox=BoundingBox(
                    x1=location.get("x1", 0),
                    y1=location.get("y1", 0),
                    x2=location.get("x2", 1),
                    y2=location.get("y2", 1),
                ) if location else BoundingBox(x1=0, y1=0, x2=1, y2=1),
                confidence=float(m.get("confidence", result.confidence)),
            ))

        # Convert notes
        for n in result.notes:
            location = n.get("location", {})
            notes.append(NoteExtraction(
                id=str(uuid.uuid4())[:8],
                content=n.get("content", ""),
                note_type=n.get("type", "general"),
                source_bbox=BoundingBox(
                    x1=location.get("x1", 0),
                    y1=location.get("y1", 0),
                    x2=location.get("x2", 1),
                    y2=location.get("y2", 1),
                ) if location else BoundingBox(x1=0, y1=0, x2=1, y2=1),
            ))

        # Convert callouts
        for c in result.callouts:
            location = c.get("location", {})
            callouts.append(CalloutExtraction(
                id=str(uuid.uuid4())[:8],
                callout_id=c.get("id", ""),
                description=c.get("description"),
                target_drawing=c.get("target"),
                source_bbox=BoundingBox(
                    x1=location.get("x1", 0),
                    y1=location.get("y1", 0),
                    x2=location.get("x2", 1),
                    y2=location.get("y2", 1),
                ) if location else BoundingBox(x1=0, y1=0, x2=1, y2=1),
            ))

    def _parse_unit(self, unit_str: str) -> UnitOfMeasure:
        """Parse a unit string into a UnitOfMeasure enum"""
        unit_map = {
            "ea": UnitOfMeasure.EACH,
            "each": UnitOfMeasure.EACH,
            "lf": UnitOfMeasure.LINEAR_FEET,
            "linear feet": UnitOfMeasure.LINEAR_FEET,
            "ft": UnitOfMeasure.LINEAR_FEET,
            "lm": UnitOfMeasure.LINEAR_METERS,
            "m": UnitOfMeasure.LINEAR_METERS,
            "in": UnitOfMeasure.INCHES,
            "inches": UnitOfMeasure.INCHES,
            "mm": UnitOfMeasure.MILLIMETERS,
            "sf": UnitOfMeasure.SQUARE_FEET,
            "sqft": UnitOfMeasure.SQUARE_FEET,
            "sm": UnitOfMeasure.SQUARE_METERS,
            "sqm": UnitOfMeasure.SQUARE_METERS,
            "cf": UnitOfMeasure.CUBIC_FEET,
            "cy": UnitOfMeasure.CUBIC_YARDS,
            "lbs": UnitOfMeasure.POUNDS,
            "kg": UnitOfMeasure.KILOGRAMS,
            "ton": UnitOfMeasure.TONS,
            "ls": UnitOfMeasure.LUMP_SUM,
            "allow": UnitOfMeasure.ALLOWANCE,
        }
        return unit_map.get(unit_str.lower(), UnitOfMeasure.EACH)
