"""
AI Client Abstraction

Provides a unified interface for different AI providers (OpenAI, Anthropic).
Supports structured output via response_format (OpenAI) and tool use (Anthropic).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, TypeVar, Type
import json
import hashlib

from pydantic import BaseModel

from .models import APIConfig, APIProvider, ImageData


T = TypeVar('T', bound=BaseModel)


@dataclass
class AIMessage:
    """A message in the conversation"""
    role: str  # "user", "assistant", "system"
    content: str
    images: list[ImageData] | None = None


@dataclass
class AIResponse:
    """Response from an AI provider"""
    content: str
    raw_response: Any
    usage: dict | None = None
    cached: bool = False


class AIClient(ABC):
    """Abstract base class for AI clients"""

    def __init__(self, config: APIConfig):
        self.config = config
        self._client: Any = None

    @property
    @abstractmethod
    def client(self) -> Any:
        """Get or create the underlying API client"""
        pass

    @abstractmethod
    def complete(
        self,
        messages: list[AIMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AIResponse:
        """Send a completion request"""
        pass

    @abstractmethod
    def complete_structured(
        self,
        messages: list[AIMessage],
        response_model: Type[T],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> T:
        """
        Send a completion request with structured output.

        Uses response_format for OpenAI, tool use for Anthropic.
        Returns an instance of the response_model.
        """
        pass

    def get_cache_key(self, messages: list[AIMessage], model: str) -> str:
        """Generate a cache key for the request"""
        content_hash = hashlib.sha256()
        for msg in messages:
            content_hash.update(msg.role.encode())
            content_hash.update(msg.content.encode())
            if msg.images:
                for img in msg.images:
                    content_hash.update(img.data[:1000])  # First 1KB of image
        content_hash.update(model.encode())
        return content_hash.hexdigest()[:16]


class OpenAIClient(AIClient):
    """OpenAI API client"""

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return self._client

    def complete(
        self,
        messages: list[AIMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AIResponse:
        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            if msg.images:
                content = [{"type": "text", "text": msg.content}]
                for img in msg.images:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": img.data_url,
                            "detail": "high" if img.width > 512 else "low",
                        }
                    })
                openai_messages.append({"role": msg.role, "content": content})
            else:
                openai_messages.append({"role": msg.role, "content": msg.content})

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature if temperature is not None else self.config.temperature,
        )

        return AIResponse(
            content=response.choices[0].message.content or "",
            raw_response=response,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    def complete_structured(
        self,
        messages: list[AIMessage],
        response_model: Type[T],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> T:
        """Use OpenAI's response_format for structured output"""
        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            if msg.images:
                content = [{"type": "text", "text": msg.content}]
                for img in msg.images:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": img.data_url,
                            "detail": "high" if img.width > 512 else "low",
                        }
                    })
                openai_messages.append({"role": msg.role, "content": content})
            else:
                openai_messages.append({"role": msg.role, "content": msg.content})

        # Add instruction for JSON output
        schema_json = response_model.model_json_schema()

        # Use response_format with json_schema
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature if temperature is not None else self.config.temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": schema_json,
                }
            },
        )

        content = response.choices[0].message.content or "{}"
        return response_model.model_validate_json(content)


class AnthropicClient(AIClient):
    """Anthropic API client"""

    @property
    def client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.config.api_key)
        return self._client

    def complete(
        self,
        messages: list[AIMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AIResponse:
        # Convert messages to Anthropic format
        anthropic_messages = []
        system_message = None

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
                continue

            if msg.images:
                content = []
                for img in msg.images:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": f"image/{img.format}",
                            "data": img.base64,
                        }
                    })
                content.append({"type": "text", "text": msg.content})
                anthropic_messages.append({"role": msg.role, "content": content})
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        kwargs = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        if system_message:
            kwargs["system"] = system_message
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = self.client.messages.create(**kwargs)

        return AIResponse(
            content=response.content[0].text if response.content else "",
            raw_response=response,
            usage={
                "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.output_tokens if response.usage else 0,
            },
        )

    def complete_structured(
        self,
        messages: list[AIMessage],
        response_model: Type[T],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> T:
        """Use Anthropic's tool use for structured output"""
        # Convert messages to Anthropic format
        anthropic_messages = []
        system_message = None

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
                continue

            if msg.images:
                content = []
                for img in msg.images:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": f"image/{img.format}",
                            "data": img.base64,
                        }
                    })
                content.append({"type": "text", "text": msg.content})
                anthropic_messages.append({"role": msg.role, "content": content})
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        # Create tool definition from Pydantic model
        schema = response_model.model_json_schema()

        # Remove $defs and inline them (Anthropic doesn't support $ref)
        schema = self._inline_refs(schema)

        tool = {
            "name": "structured_response",
            "description": f"Return the analysis result as a {response_model.__name__}",
            "input_schema": schema,
        }

        kwargs = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": "structured_response"},
        }
        if system_message:
            kwargs["system"] = system_message
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = self.client.messages.create(**kwargs)

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use" and block.name == "structured_response":
                return response_model.model_validate(block.input)

        # Fallback: try to parse from text
        for block in response.content:
            if block.type == "text":
                try:
                    return response_model.model_validate_json(block.text)
                except Exception:
                    pass

        raise ValueError("No structured response found in API response")

    def _inline_refs(self, schema: dict) -> dict:
        """Inline $ref references in a JSON schema"""
        defs = schema.pop("$defs", {})

        def resolve_refs(obj: Any) -> Any:
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref_path = obj["$ref"].split("/")[-1]
                    if ref_path in defs:
                        return resolve_refs(defs[ref_path])
                return {k: resolve_refs(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve_refs(item) for item in obj]
            return obj

        return resolve_refs(schema)


def create_client(config: APIConfig) -> AIClient:
    """Factory function to create the appropriate AI client"""
    if config.provider == APIProvider.OPENAI:
        return OpenAIClient(config)
    elif config.provider == APIProvider.ANTHROPIC:
        return AnthropicClient(config)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


# Structured response models for analysis
class AnalysisConfidence(BaseModel):
    """Confidence and complexity ratings"""
    confidence: float
    complexity: float


class QuantityOutput(BaseModel):
    """A single quantity output"""
    description: str
    quantity: float
    unit: str
    category_level1: str = "General"
    category_level2: Optional[str] = None
    category_level3: Optional[str] = None
    csi_division: Optional[str] = None
    location_x1: float = 0.0
    location_y1: float = 0.0
    location_x2: float = 1.0
    location_y2: float = 1.0
    confidence: float = 0.5


class MeasurementOutput(BaseModel):
    """A single measurement output"""
    value: float
    unit: str
    label: Optional[str] = None
    location_x1: float = 0.0
    location_y1: float = 0.0
    location_x2: float = 1.0
    location_y2: float = 1.0
    confidence: float = 0.5


class NoteOutput(BaseModel):
    """A single note output"""
    content: str
    note_type: str = "general"
    location_x1: float = 0.0
    location_y1: float = 0.0
    location_x2: float = 1.0
    location_y2: float = 1.0


class CalloutOutput(BaseModel):
    """A single callout output"""
    callout_id: str
    description: Optional[str] = None
    target: Optional[str] = None
    location_x1: float = 0.0
    location_y1: float = 0.0
    location_x2: float = 1.0
    location_y2: float = 1.0


class StructuredAnalysisResult(BaseModel):
    """Complete structured analysis result"""
    confidence: float
    complexity: float
    quantities: list[QuantityOutput] = []
    measurements: list[MeasurementOutput] = []
    notes: list[NoteOutput] = []
    callouts: list[CalloutOutput] = []
    metadata: dict[str, Any] = {}


class ClassificationResult(BaseModel):
    """Drawing classification result"""
    drawing_type: str
    discipline: str
    sub_type: Optional[str] = None
    confidence: float
    reasoning: Optional[str] = None
