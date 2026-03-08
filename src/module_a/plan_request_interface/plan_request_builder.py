"""
Plan Request Builder

Main orchestration class for plan request handling.

Coordinates:
1. Context building from state
2. Context compression
3. Prompt construction
4. Call to Module B (LLM Engine) for generation
5. Return raw response
6. Fallback handling
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from .plan_request_models import (
    PlanningContext,
    CompressedContextSummary,
    PlanningPrompt,
    PlanCandidate,
    PlanningApproach,
    PlanStatus,
)
from .plan_request_utils import (
    build_planning_context,
    determine_planning_approach,
    compress_planning_context,
    build_planning_prompt,
    create_fallback_plan,
)

# Import Module B LLM Engine
try:
    from ...module_b.llm_engine import OllamaClient
    HAS_MODULE_B = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Module B not available. LLM invocation will fail.")
    HAS_MODULE_B = False

logger = logging.getLogger(__name__)


class PlanRequestBuilder:
    """
    Orchestrates the complete plan request workflow.
    
    Responsibilities:
    1. Extract planning context from state
    2. Determine optimal planning approach
    3. Compress context for LLM
    4. Build structured prompt
    5. Request plan from LLM
    6. Parse response into structured plan
    7. Handle failures with fallback
    8. Return updated state with candidate plan
    """
    
    def __init__(self,
                 model: str = "mistral",
                 temperature: float = 0.7,
                 timeout_seconds: int = 30):
        """
        Initialize builder.
        
        Args:
            model: LLM model to use
            temperature: Generation temperature
            timeout_seconds: Request timeout
        """
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        
        logger.info(
            f"PlanRequestBuilder initialized: model={model}, "
            f"temp={temperature}, timeout={timeout_seconds}s"
        )
    
    def request_plan(self, state: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Workflow: context → compress → prompt → call Module B → return raw response.
        
        Main orchestration method.
        This module ONLY requests the plan via Module B.
        Parsing and validation done by downstream modules.
        
        Args:
            state: Current state
            
        Returns:
            (raw_llm_response_text, metadata) tuple
            
        Raises:
            ValueError: If required state fields missing
        """
        logger.info(f"Starting plan request for user {state.get('user_id')}")
        
        metadata = {
            "workflow_started": datetime.utcnow().isoformat(),
            "steps_completed": [],
            "success": False,
            "used_fallback": False,
            "errors": [],
        }
        
        try:
            # Step 1: Build context
            logger.debug("Step 1: Building planning context")
            context = build_planning_context(state)
            metadata["steps_completed"].append("context_built")
            
            # Step 2: Determine approach
            logger.debug("Step 2: Determining planning approach")
            approach = determine_planning_approach(context)
            metadata["planning_approach"] = approach.value
            metadata["steps_completed"].append("approach_determined")
            
            # Step 3: Compress context
            logger.debug("Step 3: Compressing context")
            compressed = compress_planning_context(context)
            metadata["compression_ratio"] = compressed.compression_ratio
            metadata["compressed_size_bytes"] = compressed.compressed_size
            metadata["steps_completed"].append("context_compressed")
            
            # Step 4: Build prompt
            logger.debug("Step 4: Building prompt")
            full_prompt = f"{compressed.summary_text}\n{compressed.energy_summary}\n{compressed.constraint_summary}"
            metadata["prompt_size_bytes"] = len(full_prompt)
            metadata["steps_completed"].append("prompt_built")
            
            # Step 5: Call Module B (LLM Engine)
            if not HAS_MODULE_B:
                logger.error("Module B not available")
                raise RuntimeError("Module B (LLM Engine) not available")
            
            logger.debug("Step 5: Invoking Module B (Ollama Client)")
            client = OllamaClient(model=self.model, temperature=self.temperature, timeout=self.timeout_seconds)
            
            llm_response = client.generate(full_prompt)
            metadata["llm_model"] = llm_response.model
            metadata["generation_time_ms"] = llm_response.generation_time_ms
            metadata["steps_completed"].append("module_b_invoked")
            
            # Check if Module B invocation failed
            if llm_response.is_error:
                logger.warning(f"Module B error: {llm_response.error}")
                metadata["llm_error"] = llm_response.error
                metadata["errors"].append(f"Module B error: {llm_response.error}")
                
                # Use fallback
                logger.info("LLM unavailable, returning fallback signal")
                metadata["used_fallback"] = True
                metadata["fallback_reason"] = llm_response.error
                metadata["steps_completed"].append("fallback_triggered")
                metadata["success"] = False
                
                return None, metadata  # Signal fallback to downstream
            
            # Success: return raw response for Plan Parser module
            metadata["success"] = True
            metadata["response_length"] = len(llm_response.text)
            logger.info(f"Module B response received: {len(llm_response.text)} chars")
            
            return llm_response.text, metadata
            
        except Exception as e:
            logger.error(f"Error in plan request workflow: {str(e)}")
            metadata["errors"].append(f"Workflow error: {str(e)}")
            metadata["used_fallback"] = True
            metadata["fallback_reason"] = f"Error: {str(e)}"
            
            return None, metadata  # Signal fallback to downstream
    
    def request_plan_with_retry(self,
                                state: Dict[str, Any],
                                max_retries: int = 2) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Request plan with retry logic for transient failures.
        
        Args:
            state: Current state
            max_retries: Max retry attempts
            
        Returns:
            (raw_response_text, metadata) tuple
        """
        logger.info(f"Plan request with retry (max {max_retries} attempts)")
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{max_retries}")
                response_text, metadata = self.request_plan(state)
                
                if response_text:
                    logger.info(f"Plan request successful on attempt {attempt + 1}")
                    metadata["retry_attempts"] = attempt + 1
                    return response_text, metadata
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
        
        # All retries failed
        logger.error(f"All retry attempts failed.")
        return None, {
            "workflow_started": datetime.utcnow().isoformat(),
            "success": False,
            "used_fallback": True,
            "fallback_reason": f"All retries failed: {str(last_error)}",
            "errors": [str(last_error)],
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current builder status."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
            "module_b_available": HAS_MODULE_B,
            "initialized": True,
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def build_and_request_plan(state: Dict[str, Any],
                          model: str = "mistral",
                          temperature: float = 0.7,
                          timeout_seconds: int = 30) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Convenience function to request plan in one call.
    
    Returns raw LLM response for downstream Plan Parser module.
    
    Args:
        state: Current state
        model: LLM model
        temperature: Generation temperature
        timeout_seconds: Request timeout
        
    Returns:
        (raw_response_text, metadata) tuple
    """
    builder = PlanRequestBuilder(
        model=model,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
    )
    return builder.request_plan_with_retry(state, max_retries=2)


def get_planning_status(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check current planning capabilities and status.
    
    Args:
        state: Current state
        
    Returns:
        Status dictionary with planning readiness info
    """
    builder = PlanRequestBuilder()
    return builder.get_status()
