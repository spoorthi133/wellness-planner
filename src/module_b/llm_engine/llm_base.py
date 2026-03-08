"""
LLM Base Interfaces

Abstract base classes for LLM providers.
Enables easy switching between different LLM backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class LLMResponse:
    """Standardized LLM response."""
    
    def __init__(self, 
                 text: str,
                 model: str,
                 generation_time_ms: int = 0,
                 tokens_used: int = 0,
                 error: Optional[str] = None):
        self.text = text
        self.model = model
        self.generation_time_ms = generation_time_ms
        self.tokens_used = tokens_used
        self.error = error
        self.timestamp = datetime.utcnow()
    
    @property
    def is_error(self) -> bool:
        return self.error is not None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "model": self.model,
            "generation_time_ms": self.generation_time_ms,
            "tokens_used": self.tokens_used,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            **kwargs: Provider-specific arguments
            
        Returns:
            LLMResponse
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get provider status."""
        pass
