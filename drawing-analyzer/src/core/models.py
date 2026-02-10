"""
Core models and types for drawing analysis
"""
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum
import base64
from pathlib import Path


class APIProvider(str, Enum):
    """Supported API providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class APIConfig:
    """Configuration for API connection"""
    provider: APIProvider
    api_key: str
    base_url: Optional[str] = None
    model: str = "gpt-4o"  # default model, can be changed
    max_tokens: int = 4096
    temperature: float = 0.1

    @classmethod
    def from_env(cls, provider: APIProvider = APIProvider.OPENAI) -> "APIConfig":
        import os
        if provider == APIProvider.OPENAI:
            return cls(
                provider=provider,
                api_key=os.environ.get("OPENAI_API_KEY", ""),
                base_url=os.environ.get("OPENAI_BASE_URL"),
                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            )
        elif provider == APIProvider.ANTHROPIC:
            return cls(
                provider=provider,
                api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            )
        raise ValueError(f"Unknown provider: {provider}")


@dataclass
class ImageData:
    """Container for image data"""
    data: bytes
    width: int
    height: int
    format: str = "png"
    page: int = 1

    @property
    def base64(self) -> str:
        return base64.b64encode(self.data).decode("utf-8")

    @property
    def data_url(self) -> str:
        return f"data:image/{self.format};base64,{self.base64}"

    @classmethod
    def from_file(cls, path: Path) -> "ImageData":
        from PIL import Image
        import io

        with Image.open(path) as img:
            width, height = img.size
            fmt = img.format.lower() if img.format else "png"

            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format=fmt.upper())
            data = buffer.getvalue()

        return cls(data=data, width=width, height=height, format=fmt)


@dataclass
class Thumbnail:
    """Low-resolution thumbnail of a drawing"""
    image: ImageData
    scale_factor: float  # How much smaller than original
    original_width: int
    original_height: int

    @classmethod
    def create(cls, image_data: ImageData, max_size: int = 1024) -> "Thumbnail":
        """Create a thumbnail from image data"""
        from PIL import Image
        import io

        # Load the image
        img = Image.open(io.BytesIO(image_data.data))
        original_width, original_height = img.size

        # Calculate scale
        scale = min(max_size / original_width, max_size / original_height)
        if scale >= 1:
            # Image already small enough
            return cls(
                image=image_data,
                scale_factor=1.0,
                original_width=original_width,
                original_height=original_height,
            )

        # Resize
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert to bytes
        buffer = io.BytesIO()
        img_resized.save(buffer, format="PNG")
        thumb_data = buffer.getvalue()

        return cls(
            image=ImageData(
                data=thumb_data,
                width=new_width,
                height=new_height,
                format="png",
                page=image_data.page,
            ),
            scale_factor=scale,
            original_width=original_width,
            original_height=original_height,
        )


@dataclass
class ConvContext:
    """
    Convolutional context passed to the API for analysis.
    Contains the full-page thumbnail, a kernel crop, and nearby elements.
    """
    thumbnail: Thumbnail
    kernel_image: ImageData
    kernel_bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 (normalized 0-1)
    kernel_pixel_size: tuple[int, int]  # NxM pixels
    elements_in_context: list[dict] = field(default_factory=list)

    def to_api_payload(self) -> dict:
        """Convert to a payload suitable for API submission"""
        return {
            "thumbnail_base64": self.thumbnail.image.base64,
            "kernel_base64": self.kernel_image.base64,
            "kernel_bbox": {
                "x1": self.kernel_bbox[0],
                "y1": self.kernel_bbox[1],
                "x2": self.kernel_bbox[2],
                "y2": self.kernel_bbox[3],
            },
            "kernel_size_pixels": {
                "width": self.kernel_pixel_size[0],
                "height": self.kernel_pixel_size[1],
            },
            "context_elements": self.elements_in_context,
        }


@dataclass
class SkillResult:
    """Result from applying a skill to a drawing region"""
    skill_name: str
    confidence: float
    complexity: float
    quantities: list[dict] = field(default_factory=list)
    measurements: list[dict] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)
    callouts: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    raw_response: Optional[str] = None


@dataclass
class AnalysisConfig:
    """Configuration for the analysis process"""
    # Kernel settings
    initial_kernel_size: tuple[int, int] = (512, 512)  # NxM pixels
    min_kernel_size: tuple[int, int] = (128, 128)
    kernel_overlap: float = 0.2  # 20% overlap between kernels
    complexity_threshold: float = 0.7  # Above this, reduce kernel size

    # Thumbnail settings
    thumbnail_max_size: int = 1024

    # API settings
    api_config: Optional[APIConfig] = None

    # Output settings
    output_format: str = "json"  # json, csv, excel
    include_raw_responses: bool = False

    # Deduplication
    dedup_iou_threshold: float = 0.5  # IoU threshold for element deduplication
