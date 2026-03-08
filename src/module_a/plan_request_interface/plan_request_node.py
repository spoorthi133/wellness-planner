"""
Plan Request Node

LangGraph node integration for plan request interface.

Responsibilities:
1. Extract state signals
2. Orchestrate plan request via PlanRequestBuilder
3. Parse response into plan candidate
4. Update state with candidate plan
5. Append execution trace
6. Return updated state

This is the first node that interacts with the LLM (Module B).
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from copy import deepcopy

from .plan_request_models import (
    PlanRequestExecutionTrace,
    PlanCandidate,
    PlanStatus,
)
from .plan_request_builder import PlanRequestBuilder

logger = logging.getLogger(__name__)


# ============================================================================
# Node Functions
# ============================================================================

def plan_request_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Plan Request Interface.
    
    Orchestrates plan request workflow and returns updated state.
    
    Input state requirements:
    - user_id
    - constraints
    - energy_budget
    - environment_context
    - life_mode
    - forecast_data (optional)
    - execution_trace (optional)
    
    Output state mutations:
    - plan_candidates: List of plan candidates
    - last_node_executed: Set to 'plan_request_interface'
    - execution_trace: Appended with execution entry
    
    Args:
        state: Current state dictionary
        
    Returns:
        Updated state with plan candidate and trace
    """
    logger.info(f"=== PLAN REQUEST NODE ===")
    logger.info(f"User: {state.get('user_id')}")
    
    trace_start = datetime.utcnow()
    
    try:
        # Validate required fields
        user_id = state.get("user_id")
        if not user_id:
            logger.error("user_id required in state")
            raise ValueError("user_id required")
        
        logger.debug("Input validation passed")
        
        # Extract key context for tracing
        energy_budget = state.get("energy_budget", {}).get("daily_budget", 100)
        constraint_pressure = state.get("constraints", {}).get("pressure_level", "LOW")
        environment_complexity = state.get("environment_context", {}).get("environment_complexity", 0)
        life_mode = state.get("life_mode", {}).get("mode", "maintenance")
        
        logger.debug(f"Context: energy={energy_budget}, pressure={constraint_pressure}, "
                    f"env_complexity={environment_complexity}, mode={life_mode}")
        
        # Build and execute plan request
        builder = PlanRequestBuilder()
        
        logger.info("Building planning request...")
        candidate, request_metadata = builder.request_plan(state)
        
        if not candidate:
            logger.error("No plan candidate returned")
            raise ValueError("Plan request failed to produce candidate")
        
        logger.info(f"Plan candidate received: {candidate.candidate_id}")
        logger.info(f"  Status: {candidate.status.value}")
        logger.info(f"  Source: {candidate.source}")
        if candidate.plan:
            logger.info(f"  Activities: {len([a for t in [candidate.plan.morning_activities, candidate.plan.afternoon_activities, candidate.plan.evening_activities, candidate.plan.recovery_blocks] for a in t])}")
            logger.info(f"  Total energy: {candidate.plan.total_energy_allocated}")
        
        # Create execution trace
        trace_end = datetime.utcnow()
        execution_time_ms = int((trace_end - trace_start).total_seconds() * 1000)
        
        try:
            planning_approach = request_metadata.get("planning_approach", "standard")
        except:
            planning_approach = "standard"
        
        trace_entry = PlanRequestExecutionTrace(
            user_id=user_id,
            life_mode=life_mode,
            energy_budget=energy_budget,
            constraint_pressure=constraint_pressure,
            environment_complexity=environment_complexity,
            planning_approach=planning_approach,
            prompt_size_bytes=request_metadata.get("prompt_size_bytes", 0),
            compression_ratio=request_metadata.get("compression_ratio", 0),
            llm_model=request_metadata.get("llm_model", ""),
            generation_time_ms=request_metadata.get("generation_time_ms", 0),
            is_fallback=request_metadata.get("used_fallback", False),
            candidate_generated=candidate is not None and candidate.plan is not None,
            success=request_metadata.get("success", False),
            error_message=", ".join(request_metadata.get("errors", [])) if request_metadata.get("errors") else None,
        )
        
        logger.debug(f"Execution trace created: {execution_time_ms}ms")
        
        # Update state - deep copy for safety
        updated_state = deepcopy(state)
        
        # Add/append plan candidates
        if "plan_candidates" not in updated_state:
            updated_state["plan_candidates"] = []
        
        # Convert candidate to dict for storage
        candidate_dict = candidate.model_dump()
        updated_state["plan_candidates"].append(candidate_dict)
        
        logger.debug(f"Plan candidates count: {len(updated_state['plan_candidates'])}")
        
        # Update metadata
        updated_state["last_node_executed"] = "plan_request_interface"
        
        # Append execution trace
        if "execution_trace" not in updated_state:
            updated_state["execution_trace"] = []
        
        updated_state["execution_trace"].append(trace_entry.model_dump())
        logger.debug("Execution trace appended to state")
        
        logger.info(f"=== NODE COMPLETE: Success ===")
        return updated_state
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        
        # Return state with error trace
        error_state = deepcopy(state)
        error_state["last_node_executed"] = "plan_request_interface"
        
        error_trace = PlanRequestExecutionTrace(
            user_id=state.get("user_id", "unknown"),
            life_mode=state.get("life_mode", {}).get("mode", "unknown"),
            energy_budget=state.get("energy_budget", {}).get("daily_budget", 0),
            constraint_pressure=state.get("constraints", {}).get("pressure_level", "unknown"),
            environment_complexity=state.get("environment_context", {}).get("environment_complexity", 0),
            planning_approach="error",
            success=False,
            error_message=str(e),
        )
        
        if "execution_trace" not in error_state:
            error_state["execution_trace"] = []
        
        error_state["execution_trace"].append(error_trace.model_dump())
        
        logger.info(f"=== NODE COMPLETE: Error ===")
        return error_state
        
    except Exception as e:
        logger.error(f"Unexpected error in plan request node: {str(e)}", exc_info=True)
        
        # Return state with error trace
        error_state = deepcopy(state)
        error_state["last_node_executed"] = "plan_request_interface"
        
        error_trace = PlanRequestExecutionTrace(
            user_id=state.get("user_id", "unknown"),
            life_mode=state.get("life_mode", {}).get("mode", "unknown"),
            energy_budget=state.get("energy_budget", {}).get("daily_budget", 0),
            constraint_pressure=state.get("constraints", {}).get("pressure_level", "unknown"),
            environment_complexity=state.get("environment_context", {}).get("environment_complexity", 0),
            planning_approach="error",
            success=False,
            error_message=f"Unexpected error: {str(e)}",
        )
        
        if "execution_trace" not in error_state:
            error_state["execution_trace"] = []
        
        error_state["execution_trace"].append(error_trace.model_dump())
        
        logger.info(f"=== NODE COMPLETE: Error ===")
        return error_state


# ============================================================================
# Node Configuration
# ============================================================================

def get_plan_request_node_config() -> Dict[str, Any]:
    """
    Get node configuration for LangGraph integration.
    
    Returns:
        Configuration dictionary
    """
    return {
        "name": "plan_request_interface",
        "description": "Request wellness plan from LLM",
        "input_fields": {
            "user_id": "User identifier",
            "constraints": "Constraint analysis results",
            "energy_budget": "Energy budget state",
            "environment_context": "Environment adaptation results",
            "life_mode": "Life mode information",
            "forecast_data": "Forecast information (optional)",
        },
        "output_fields": {
            "plan_candidates": "Generated plan candidates",
            "last_node_executed": "Node name",
            "execution_trace": "Execution trace entries",
        },
        "required_inputs": [
            "user_id",
            "constraints",
            "energy_budget",
            "environment_context",
            "life_mode",
        ],
        "node_type": "module_a",
        "module": "plan_request_interface",
        "position_in_workflow": 7,
        "is_llm_interface": True,
        "llm_interaction_type": "planner",
    }


# ============================================================================
# Helper Functions
# ============================================================================

def validate_node_inputs(state: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate that state has required fields for plan request node.
    
    Args:
        state: State to validate
        
    Returns:
        (is_valid, error_message) tuple
    """
    required_fields = [
        ("user_id", "User identifier"),
        ("constraints", "Constraint data"),
        ("energy_budget", "Energy budget"),
        ("environment_context", "Environment context"),
        ("life_mode", "Life mode"),
    ]
    
    for field, description in required_fields:
        if field not in state or state[field] is None:
            error = f"Missing required field: {field} ({description})"
            logger.warning(error)
            return False, error
    
    logger.debug("Input validation passed")
    return True, None


def extract_planning_signals(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract planning signals from state for reference.
    
    Args:
        state: Current state
        
    Returns:
        Dictionary of extracted signals
    """
    signals = {
        "user_id": state.get("user_id"),
        "life_mode": state.get("life_mode", {}).get("mode", "unknown"),
        "energy_budget": state.get("energy_budget", {}).get("daily_budget", 100),
        "remaining_energy": state.get("energy_budget", {}).get("remaining_energy", 100),
        "constraint_pressure": state.get("constraints", {}).get("pressure_level", "LOW"),
        "constraint_score": state.get("constraints", {}).get("constraint_score", 0),
        "environment_complexity": state.get("environment_context", {}).get("environment_complexity", 0),
        "activity_restrictions": state.get("environment_context", {}).get("activity_restrictions", []),
        "energy_volatility": state.get("energy_budget", {}).get("energy_volatility", 0),
        "forecast_dips": state.get("forecast_data", {}).get("predicted_energy_dips", []),
    }
    
    return signals


def get_candidate_summary(candidate: PlanCandidate) -> Dict[str, Any]:
    """
    Get summary of plan candidate.
    
    Args:
        candidate: Plan candidate
        
    Returns:
        Summary dictionary
    """
    summary = {
        "candidate_id": candidate.candidate_id,
        "source": candidate.source,
        "status": candidate.status.value,
        "has_plan": candidate.plan is not None,
    }
    
    if candidate.plan:
        activities = (
            len(candidate.plan.morning_activities) +
            len(candidate.plan.afternoon_activities) +
            len(candidate.plan.evening_activities) +
            len(candidate.plan.recovery_blocks)
        )
        summary.update({
            "activity_count": activities,
            "total_energy_allocated": candidate.plan.total_energy_allocated,
            "rationale": candidate.plan.plan_rationale[:100] if candidate.plan.plan_rationale else None,
        })
    
    if candidate.validation_errors:
        summary["errors"] = candidate.validation_errors
    
    return summary


# Type hints
from typing import Tuple
