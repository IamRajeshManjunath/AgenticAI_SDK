"""Ollama integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class OllamaConfig(BaseModel):
    """Configuration for Ollama local chat models."""
    
    # Required
    base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    
    # Model parameters
    model: str = Field(default="llama3.1", description="Model name (must be pulled locally)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    timeout: float = Field(default=120.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
    streaming: bool = Field(default=True)
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=False)  # Depends on model
    
    # Advanced
    keep_alive: Optional[str] = Field(default="5m", description="Keep model loaded")
    num_ctx: Optional[int] = Field(default=None, description="Context window size")
    num_gpu: Optional[int] = Field(default=None, description="Number of GPU layers")
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=False,
        )
    )
