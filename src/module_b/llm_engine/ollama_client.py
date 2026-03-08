"""
Ollama LLM Client

Module B - LLM Engine

Client for interacting with Ollama local LLM server.
Implements LLMProvider interface for unified API.

Configuration:
- Endpoint: http://localhost:11434/api/chat
- Models: mistral, neural-chat, orca, etc.
- Timeout: 30 seconds (configurable)
"""

import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

from .llm_base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OllamaClient(LLMProvider):
    """
    Ollama local LLM client.
    
    Communicates with Ollama server running locally.
    Supports any model available in Ollama.
    """
    
    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "mistral"
    DEFAULT_TIMEOUT = 30
    DEFAULT_TEMPERATURE = 0.7
    
    def __init__(self,
                 base_url: str = DEFAULT_BASE_URL,
                 model: str = DEFAULT_MODEL,
                 timeout: int = DEFAULT_TIMEOUT,
                 temperature: float = DEFAULT_TEMPERATURE):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama server URL
            model: Model to use
            timeout: Request timeout in seconds
            temperature: Generation temperature (0-1)
        """
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.api_endpoint = f"{base_url}/api/chat"
        
        logger.info(
            f"OllamaClient initialized: {base_url}, model={model}, "
            f"timeout={timeout}s, temp={temperature}"
        )
    
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate completion from prompt.
        
        Args:
            prompt: Input prompt
            **kwargs: Override defaults (model, temperature, timeout)
            
        Returns:
            LLMResponse
        """
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)
        timeout = kwargs.get("timeout", self.timeout)
        
        logger.debug(f"Generating with {model}: {len(prompt)} chars")
        
        try:
            # Prepare request
            messages = [{"role": "user", "content": prompt}]
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }
            
            start_time = datetime.utcnow()
            
            # Send request
            response = requests.post(
                self.api_endpoint,
                json=payload,
                timeout=timeout,
            )
            
            end_time = datetime.utcnow()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Check response
            if response.status_code != 200:
                error = f"HTTP {response.status_code}: {response.text[:100]}"
                logger.error(error)
                return LLMResponse(
                    text="",
                    model=model,
                    generation_time_ms=generation_time_ms,
                    error=error,
                )
            
            # Parse response
            data = response.json()
            text = data.get("message", {}).get("content", "")
            tokens_used = data.get("eval_count", 0)
            
            logger.info(f"Generated {len(text)} chars in {generation_time_ms}ms")
            
            return LLMResponse(
                text=text,
                model=model,
                generation_time_ms=generation_time_ms,
                tokens_used=tokens_used,
            )
            
        except requests.Timeout:
            error = f"Request timeout after {timeout}s"
            logger.error(error)
            return LLMResponse(
                text="",
                model=model,
                error=error,
            )
        except requests.ConnectionError as e:
            error = f"Connection error: {str(e)}"
            logger.error(error)
            return LLMResponse(
                text="",
                model=model,
                error=error,
            )
        except Exception as e:
            error = f"Error: {str(e)}"
            logger.error(error)
            return LLMResponse(
                text="",
                model=model,
                error=error,
            )
    
    def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get Ollama server status."""
        return {
            "provider": "Ollama",
            "base_url": self.base_url,
            "model": self.model,
            "available": self.is_available(),
            "temperature": self.temperature,
            "timeout": self.timeout,
        }
    
    def list_models(self) -> list:
        """List available models on Ollama server."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                return [m.get("name") for m in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            return []
    
    def set_model(self, model: str):
        """Change model."""
        self.model = model
        logger.info(f"Model changed to: {model}")
    
    def set_temperature(self, temperature: float):
        """Change temperature."""
        if not (0 <= temperature <= 1):
            raise ValueError("Temperature must be 0-1")
        self.temperature = temperature
        logger.info(f"Temperature changed to: {temperature}")
