"""Plugin metadata package for AgenticAI SDK."""

# Import all plugin metadata for entry point discovery
from .openai import OpenAIPluginMetadata, AzureOpenAIPluginMetadata
from .anthropic import AnthropicPluginMetadata, VertexAIAnthropicPluginMetadata
from .google import GoogleGenAIPluginMetadata, GoogleVertexAIPluginMetadata, GoogleEmbeddingsPluginMetadata
from .aws import BedrockPluginMetadata, BedrockEmbeddingsPluginMetadata
from .groq import GroqPluginMetadata
from .ollama import OllamaPluginMetadata
from .mistral import MistralPluginMetadata
from .cohere import CoherePluginMetadata, CohereEmbeddingsPluginMetadata
from .xai import XAIPluginMetadata
from .deepseek import DeepSeekPluginMetadata
from .nvidia import NVIDIAPluginMetadata, NVIDIAEmbeddingsPluginMetadata
from .together import TogetherPluginMetadata, TogetherEmbeddingsPluginMetadata
from .fireworks import FireworksPluginMetadata
from .databricks import DatabricksPluginMetadata, DatabricksEmbeddingsPluginMetadata
from .ibm import WatsonXPluginMetadata, WatsonXEmbeddingsPluginMetadata
from .perplexity import PerplexityPluginMetadata
from .cerebras import CerebrasPluginMetadata
from .huggingface import HuggingFacePluginMetadata, HuggingFaceEmbeddingsPluginMetadata
from .litellm import LiteLLMPluginMetadata
from .openrouter import OpenRouterPluginMetadata
from .azure import AzureAIPluginMetadata
from .tavily import TavilyPluginMetadata
from .qdrant import QdrantPluginMetadata, QdrantCheckpointerPluginMetadata
from .pinecone import PineconePluginMetadata

# Tools
from .composio import ComposioPluginMetadata
from .exa import ExaPluginMetadata
from .google_search import GoogleSearchPluginMetadata

# Sandboxes
from .e2b import E2BPluginMetadata
from .modal import ModalPluginMetadata
from .agentcore import AgentCorePluginMetadata
from .daytona import DaytonaPluginMetadata

__all__ = [
    "OpenAIPluginMetadata",
    "AzureOpenAIPluginMetadata",
    "AnthropicPluginMetadata",
    "VertexAIAnthropicPluginMetadata",
    "GoogleGenAIPluginMetadata",
    "GoogleVertexAIPluginMetadata",
    "GoogleEmbeddingsPluginMetadata",
    "BedrockPluginMetadata",
    "BedrockEmbeddingsPluginMetadata",
    "GroqPluginMetadata",
    "OllamaPluginMetadata",
    "MistralPluginMetadata",
    "CoherePluginMetadata",
    "CohereEmbeddingsPluginMetadata",
    "XAIPluginMetadata",
    "DeepSeekPluginMetadata",
    "NVIDIAPluginMetadata",
    "NVIDIAEmbeddingsPluginMetadata",
    "TogetherPluginMetadata",
    "TogetherEmbeddingsPluginMetadata",
    "FireworksPluginMetadata",
    "DatabricksPluginMetadata",
    "DatabricksEmbeddingsPluginMetadata",
    "WatsonXPluginMetadata",
    "WatsonXEmbeddingsPluginMetadata",
    "PerplexityPluginMetadata",
    "CerebrasPluginMetadata",
    "HuggingFacePluginMetadata",
    "HuggingFaceEmbeddingsPluginMetadata",
    "LiteLLMPluginMetadata",
    "OpenRouterPluginMetadata",
    "AzureAIPluginMetadata",
    "TavilyPluginMetadata",
    "QdrantPluginMetadata",
    "QdrantCheckpointerPluginMetadata",
    "PineconePluginMetadata",
    # Tools
    "ComposioPluginMetadata",
    "ExaPluginMetadata",
    "GoogleSearchPluginMetadata",
    # Sandboxes
    "E2BPluginMetadata",
    "ModalPluginMetadata",
    "AgentCorePluginMetadata",
    "DaytonaPluginMetadata",
]