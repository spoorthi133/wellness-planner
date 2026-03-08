"""
Energy Budget Manager Node - LangGraph Integration

LangGraph node for energy budget management.
Integrates energy budget calculations into the constraint-first wellness workflow.

Position in workflow:
User Input
   ↓
Constraint Analyzer
   ↓
Constraint Forecast Engine
   ↓
Energy Budget Manager   ← THIS NODE
   ↓
Environment Adapter
   ↓
Life Mode Controller

Module: Energy Budget Manager
Part of: Constraint-First Wellness Agent (Module A)

Schema Compliance Notes:
- CORRECTION 1: No new top-level state fields
- Only updates: energy_budget (new nested field), system_flags, execution_trace
- Input sources: constraints, forecast_data, life_mode, environment_context, user_history, system_flags
- Output: state.energy_budget with full structure
- Metadata stored in: energy_budget.metadata
- Timestamps use ISO format
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from copy import deepcopy

from energy_manager import EnergyBudgetManager
from energy_models import EnergyBudgetState

logger = logging.getLogger(__name__)


def energy_budget_node(state: Dict[str, Any]) -> Dict[str, Any]:

    try:
        logger.info("Starting energy_budget_manager node")
        
        # Make a copy to avoid mutating original
        updated_state = deepcopy(state)
        
        # Extract required inputs
        user_id = state.get("user_id")
        session_id = state.get("session_id", "")
        life_mode = state.get("life_mode", "maintenance")
        constraints = state.get("constraints", [])
        forecast_data = state.get("forecast_data", {})
        environment_context = state.get("environment_context", {})
        user_history = state.get("user_history", {})
        system_flags = state.get("system_flags", {})
        
        # Validate critical inputs
        if not user_id:
            raise ValueError("user_id is required in state")
        
        logger.debug(
            f"Energy budget node inputs: "
            f"user_id={user_id}, session={session_id}, "
            f"life_mode={life_mode}, constraints={len(constraints)}"
        )
        
        # Extract constraint analysis results
        constraint_score = _extract_constraint_score(state)
        constraint_pressure_level = _extract_constraint_pressure_level(state)
        
        logger.debug(
            f"Constraint analysis from state: "
            f"score={constraint_score}, pressure={constraint_pressure_level}"
        )
        
        # Initialize manager
        manager = EnergyBudgetManager()
        
        # Calculate energy budget
        logger.info(f"Calculating energy budget for {life_mode} mode")
        energy_budget = manager.calculate_energy_budget(
            life_mode=life_mode,
            constraints=_normalize_constraints(constraints),
            constraint_score=constraint_score,
            constraint_pressure_level=constraint_pressure_level,
            forecast_data=forecast_data,
            environment_context=environment_context,
            user_history=user_history,
            system_flags=system_flags,
        )
        
        logger.info(
            f"Energy budget calculated: "
            f"daily={energy_budget.daily_budget}, "
            f"recovery={energy_budget.recovery_factor:.2f}"
        )
        
        # Update state with energy budget
        updated_state["energy_budget"] = energy_budget.dict()
        
        # Update tracking fields
        updated_state["last_node_executed"] = "energy_budget_manager"
        
        # Append execution trace entry
        trace_entry = {
            "node": "energy_budget_manager",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "daily_budget": energy_budget.daily_budget,
            "allocated_energy": energy_budget.allocated_energy,
            "remaining_energy": energy_budget.remaining_energy,
            "recovery_factor": round(energy_budget.recovery_factor, 3),
            "constraint_pressure": constraint_pressure_level,
            "overload_detected": energy_budget.overload_detected,
        }
        
        if "execution_trace" not in updated_state:
            updated_state["execution_trace"] = []
        
        updated_state["execution_trace"].append(trace_entry)
        
        logger.info(
            f"Energy budget node completed successfully. "
            f"Trace: {trace_entry['timestamp']}"
        )
        
        return updated_state
        
    except ValueError as ve:
        logger.error(f"Validation error in energy_budget_node: {ve}")
        _append_error_trace(updated_state, str(ve))
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in energy_budget_node: {e}")
        _append_error_trace(updated_state, str(e))
        raise


# ============================================================================
# Helper Functions
# ============================================================================

def _extract_constraint_score(state: Dict[str, Any]) -> float:
    """
    Extract constraint score from state.
    
    Tries multiple possible locations in state.
    
    Args:
        state: Agent state
        
    Returns:
        Constraint score (0-10)
    """
    # Try forecast_data first (output from constraint engine)
    if "forecast_data" in state:
        initial_map = state["forecast_data"].get("initial_constraint_map", {})
        if "constraint_score" in initial_map:
            return float(initial_map["constraint_score"])
    
    # Try direct state field
    if "constraint_score" in state:
        return float(state["constraint_score"])
    
    # Default to moderate
    logger.debug("No constraint_score found in state, defaulting to 5.0")
    return 5.0


def _extract_constraint_pressure_level(state: Dict[str, Any]) -> str:
    """
    Extract constraint pressure level from state.
    
    Tries multiple locations.
    
    Args:
        state: Agent state
        
    Returns:
        Pressure level (LOW, MODERATE, HIGH, CRITICAL)
    """
    # Try constraint engine output
    if "constraint_analysis_result" in state:
        pressure = state["constraint_analysis_result"].get(
            "constraint_pressure_level", "MODERATE"
        )
        return pressure
    
    # Try system_flags
    system_flags = state.get("system_flags", {})
    if "constraint_pressure_level" in system_flags:
        return system_flags["constraint_pressure_level"]
    
    # Try direct state field
    if "constraint_pressure_level" in state:
        return state["constraint_pressure_level"]
    
    # Default to MODERATE
    logger.debug("No constraint_pressure_level found, defaulting to MODERATE")
    return "MODERATE"


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
        "node": "energy_budget_manager",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error": error,
        "status": "failed",
    }
    
    state["execution_trace"].append(error_entry)
    logger.debug(f"Error trace added: {error_entry}")


# ============================================================================
# Node Registration Functions
# ============================================================================

def get_energy_budget_node_config() -> Dict[str, Any]:
    """
    Get configuration for energy budget node in LangGraph.
    
    Returns:
        Node configuration dict
    """
    return {
        "name": "energy_budget_manager",
        "description": "Calculates and manages daily energy budget based on constraints and forecast",
        "function": energy_budget_node,
        "input_fields": [
            "user_id",
            "session_id",
            "life_mode",
            "constraints",
            "forecast_data",
            "environment_context",
            "user_history",
            "system_flags",
        ],
        "output_fields": [
            "energy_budget",
            "last_node_executed",
            "execution_trace",
        ],
        "position_in_graph": "after constraint_forecast_engine, before environment_adapter",
    }


def validate_node_inputs(state: Dict[str, Any]) -> tuple[bool, list]:
    """
    Validate that state has required inputs for energy budget node.
    
    Args:
        state: Agent state
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    if "user_id" not in state:
        errors.append("Missing required field: user_id")
    
    if "life_mode" not in state:
        errors.append("Missing required field: life_mode")
    
    # Optional but important fields
    if "constraints" not in state:
        logger.warning("No constraints in state for energy_budget_manager")
    
    if "forecast_data" not in state:
        logger.warning("No forecast_data in state for energy_budget_manager")
    
    return len(errors) == 0, errors
