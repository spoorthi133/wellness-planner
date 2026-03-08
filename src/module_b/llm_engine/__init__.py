"""
Module B - LLM Engine

Responsible for all LLM interactions.

This is Module B of the Constraint-First Wellness Agent.

Workflow:
    Module A: Constraint-First Orchestration
        ↓
        Creates structured prompts
        ↓
    Module B: LLM Intelligence (THIS MODULE)
        ↓
        Generates wellness plans
        ↓
        Returns raw responses
        ↓
    Back to Module A:
        Plan Parser → Plan Validator → Activate Plan

Architecture:
- Abstracts LLM provider (LLMProvider base class)
- Supports multiple backends (Ollama, OpenAI, Claude, etc.)
- Easy to switch providers by changing client

Current Implementation:
- OllamaClient: Local Ollama server
- Supports any Ollama model

Quick Start:

    # Create client
    client = OllamaClient(model="mistral")
    
    # Generate response
    response = client.generate("Your prompt here")
    
    # Check result
    if response.is_error:
        print(f"Error: {response.error}")
    else:
        print(f"Generated: {response.text}")
"""

__version__ = "1.0.0"
__module_name__ = "LLM Engine"
__description__ = "LLM interaction and response generation"

from .llm_base import (
    LLMProvider,
    LLMResponse,
)

from .ollama_client import OllamaClient

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "OllamaClient",
]


def get_module_info() -> dict:
    """Get module information."""
    return {
        "name": __module_name__,
        "version": __version__,
        "description": __description__,
        "module_b_component": True,
        "workflow_position": "LLM Intelligence",
        "responsibilities": [
            "LLM client abstraction",
            "Ollama integration",
            "Provider switching capability",
            "Response generation",
        ],
    }
