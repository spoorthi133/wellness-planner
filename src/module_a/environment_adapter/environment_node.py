"""
Environment Adapter Node - LangGraph Integration

LangGraph node for environment adaptation.
Integrates environment adaptation into the constraint-first wellness workflow.

Position in workflow:
User Input
   ↓
Constraint Analyzer
   ↓
Constraint Forecast Engine
   ↓
Energy Budget Manager
   ↓
Environment Adapter   ← THIS NODE
   ↓
Life Mode Controller
   ↓
Plan Request (Module B)

Module: Environment Adapter
Part of: Constraint-First Wellness Agent (Module A)

Schema Compliance Notes:
- CORRECTION 1: No new top-level state fields
- Only updates: environment_context (existing), execution_trace (existing)
- Input sources: environment_context, constraints, energy_budget, system_flags
- Output: state.environment_context with derived fields populated
- Metadata stored in: environment_context.adaptation_summary
- Timestamps use ISO format
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from copy import deepcopy

from environment_adapter import EnvironmentAdapterManager
from environment_models import EnvironmentContextExtended

logger = logging.getLogger(__name__)


def environment_adapter_node(state: Dict[str, Any]) -> Dict[str, Any]:

    try:
        logger.info("Starting environment_adapter node")
        
        # Make a copy to avoid mutating original
        updated_state = deepcopy(state)
        
        # Extract inputs
        user_id = state.get("user_id")
        session_id = state.get("session_id", "")
        environment_context = state.get("environment_context", {})
        constraints = state.get("constraints", [])
        energy_budget = state.get("energy_budget", {})
        
        # Validate critical inputs
        if not user_id:
            raise ValueError("user_id is required in state")
        
        logger.debug(
            f"Environment adapter inputs: "
            f"user_id={user_id}, session={session_id}, "
            f"env_fields={len(environment_context)}"
        )
        
        # Initialize adapter manager
        manager = EnvironmentAdapterManager()
        
        # Adapt environment context
        logger.info("Adapting environment context")
        adapted_context = manager.adapt_environment_context(
            environment_context=environment_context,
            constraints=_normalize_constraints(constraints),
            energy_budget=energy_budget,
        )
        
        logger.info(
            f"Environment adaptation complete: "
            f"complexity={adapted_context.environment_complexity}, "
            f"restrictions={len(adapted_context.activity_restrictions)}"
        )
        
        # Convert to dict for state storage
        context_dict = adapted_context.dict()
        
        # Update state with adapted context
        updated_state["environment_context"] = context_dict
        
        # Update tracking fields
        updated_state["last_node_executed"] = "environment_adapter"
        
        # Calculate adaptation impact for metadata
        impact = manager.calculate_adaptation_impact(context_dict, energy_budget)
        
        # Append execution trace entry
        trace_entry = {
            "node": "environment_adapter",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "environment_complexity": adapted_context.environment_complexity,
            "activity_restrictions": len(adapted_context.activity_restrictions),
            "activity_modifiers": len(adapted_context.activity_modifiers),
            "adaptation_required": adapted_context.adaptation_summary.adaptation_required if adapted_context.adaptation_summary else False,
            "planning_approach": impact.get("planning_approach", "flexible"),
        }
        
        if "execution_trace" not in updated_state:
            updated_state["execution_trace"] = []
        
        updated_state["execution_trace"].append(trace_entry)
        
        logger.info(
            f"Environment adapter node completed successfully. "
            f"Trace: {trace_entry['timestamp']}"
        )
        
        return updated_state
        
    except ValueError as ve:
        logger.error(f"Validation error in environment_adapter_node: {ve}")
        _append_error_trace(updated_state, str(ve))
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in environment_adapter_node: {e}")
        _append_error_trace(updated_state, str(e))
        raise


# ============================================================================
# Helper Functions
# ============================================================================

def _normalize_constraints(constraints: Any) -> list:
    """
    Normalize constraints to list of dicts.
    
    Args:
        constraints: Constraints (may be list or Pydantic models)
        
    Returns:
        List of constraint dicts
    """
    if not constraints:
        return []
    
    normalized = []
    for constraint in constraints:
        if isinstance(constraint, dict):
            normalized.append(constraint)
        elif hasattr(constraint, "dict"):
            # Pydantic model
            normalized.append(constraint.dict())
        elif hasattr(constraint, "__dict__"):
            # Regular object
            normalized.append(constraint.__dict__)
        else:
            logger.warning(f"Cannot normalize constraint: {constraint}")
    
    return normalized


def _append_error_trace(state: Dict[str, Any], error: str) -> None:
    """
    Append error entry to execution trace.
    
    Args:
        state: Agent state (modified in place)
        error: Error message
    """
    if "execution_trace" not in state:
        state["execution_trace"] = []
    
    error_entry = {
        "node": "environment_adapter",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error": error,
        "status": "failed",
    }
    
    state["execution_trace"].append(error_entry)
    logger.debug(f"Error trace added: {error_entry}")


# ============================================================================
# Node Registration Functions
# ============================================================================

def get_environment_adapter_node_config() -> Dict[str, Any]:
    """
    Get configuration for environment adapter node in LangGraph.
    
    Returns:
        Node configuration dict
    """
    return {
        "name": "environment_adapter",
        "description": "Adapts planning context based on physical environment constraints",
        "function": environment_adapter_node,
        "input_fields": [
            "user_id",
            "session_id",
            "environment_context",
            "constraints",
            "energy_budget",
        ],
        "output_fields": [
            "environment_context",
            "last_node_executed",
            "execution_trace",
        ],
        "position_in_graph": "after energy_budget_manager, before life_mode_controller",
    }


def validate_node_inputs(state: Dict[str, Any]) -> tuple[bool, list]:
    """
    Validate that state has required inputs for environment adapter node.
    
    Args:
        state: Agent state
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    if "user_id" not in state:
        errors.append("Missing required field: user_id")
    
    # Optional but important fields
    if "environment_context" not in state:
        logger.warning("No environment_context in state for environment_adapter")
    
    if "constraints" not in state:
        logger.warning("No constraints in state for environment_adapter")
    
    return len(errors) == 0, errors
