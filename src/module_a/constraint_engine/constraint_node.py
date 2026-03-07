"""
Constraint Analyzer Node

LangGraph node for constraint analysis.
Integrates with LangGraph pipeline to analyze constraints and update state.

Module: Constraint Analysis & Processing
Part of: Constraint-First Wellness Agent

CORRECTIONS IMPLEMENTED:
- Correction 1: No new top-level state fields (constraint_analysis, constraint_engine_impact removed)
- Correction 6: Crisis mode automatic overload detection
- Correction 7: Overload threshold rules (score >= 7, score >= 9)
- Correction 8: Populate forecast context properly
- Correction 9: Standardized execution trace entries
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from constraint_analyzer import ConstraintAnalyzer
from constraint_models import ConstraintAnalysisContext

logger = logging.getLogger(__name__)


def constraint_analyzer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for constraint analysis.

    Reads constraints from state, analyzes them, and updates state with results.

    Args:
        state: Current AgentState as dict (from LangGraph)

    Returns:
        Updated state dict with constraint analysis results

    Raises:
        ValueError: If required state fields are missing
        Exception: If analysis fails
    """
    try:
        # Extract required fields from state
        user_id = state.get("user_id")
        session_id = state.get("session_id", "")
        raw_constraints = state.get("constraints", [])
        life_mode = state.get("life_mode", "maintenance")
        environment_context = state.get("environment_context", {})
        user_history = state.get("user_history", {})
        system_flags = state.get("system_flags", {})

        if not user_id:
            raise ValueError("user_id is required in state")

        logger.info(
            f"Constraint analyzer node started for user {user_id}, "
            f"session {session_id} with {len(raw_constraints)} constraints"
        )

        # Build analysis context
        context = ConstraintAnalysisContext(
            user_id=user_id,
            session_id=session_id,
            life_mode=life_mode,
            recent_plans_count=user_history.get("total_plans_generated", 0),
            days_since_last_analysis=_calculate_days_since_last_analysis(user_history),
            has_emergency_flag=system_flags.get("emergency_mode", False),
            environment_is_restrictive=_is_environment_restrictive(environment_context),
            user_adaptive_capacity=_estimate_user_adaptive_capacity(user_history),
        )

        # Create analyzer
        analyzer = ConstraintAnalyzer(context=context)

        # Convert constraint models to dicts if they're Pydantic models
        constraint_dicts = _normalize_constraints_to_dict(raw_constraints)

        # Estimate recent overload count
        recent_overload_count = _estimate_recent_overload_count(user_history)

        # Run analysis
        analysis_result = analyzer.analyze(
            raw_constraints=constraint_dicts,
            life_mode=life_mode,
            recent_overload_count=recent_overload_count,
            user_adaptive_capacity=context.user_adaptive_capacity,
        )

        logger.info(
            f"Constraint analysis completed. Score: {analysis_result.constraint_score}, "
            f"Pressure: {analysis_result.constraint_pressure_level.value}"
        )

        # Update state with analysis results
        updated_state = _update_state_with_analysis(state, analysis_result, analyzer)

        logger.debug(
            f"State updated with constraint analysis results. "
            f"Overload detected: {updated_state['system_flags']['overload_detected']}"
        )

        return updated_state

    except ValueError as ve:
        logger.error(f"Validation error in constraint analyzer: {ve}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in constraint analyzer: {e}", exc_info=True)
        raise


def _normalize_constraints_to_dict(constraints: list) -> list:
    """
    Convert constraint models to dicts for analysis.

    Args:
        constraints: List of constraints (can be dicts or Pydantic models)

    Returns:
        List of constraint dicts
    """
    result = []
    for constraint in constraints:
        if isinstance(constraint, dict):
            result.append(constraint)
        elif hasattr(constraint, "dict"):
            # Pydantic model
            result.append(constraint.dict())
        elif hasattr(constraint, "__dict__"):
            # Python object
            result.append(vars(constraint))
        else:
            result.append(str(constraint))
    return result


def _update_state_with_analysis(
    state: Dict[str, Any], analysis_result: Any, analyzer: ConstraintAnalyzer
) -> Dict[str, Any]:
    """
    Update state dict with constraint analysis results.
    
    Implements CORRECTION 1: Store results in forecast_data and system_flags only
    Implements CORRECTION 6: Crisis mode automatic overload
    Implements CORRECTION 7: Overload threshold rules
    Implements CORRECTION 8: Populate forecast context
    Implements CORRECTION 9: Standardized execution trace

    Args:
        state: Current state
        analysis_result: ConstraintAnalysisResult from analyzer
        analyzer: ConstraintAnalyzer instance

    Returns:
        Updated state dict (schema compliant)
    """
    # Deep copy state to avoid mutations
    updated_state = state.copy()
    
    life_mode = state.get("life_mode", "maintenance")
    constraint_score = analysis_result.constraint_score

    # ========================================================================
    # CORRECTION 1: Update system_flags (no new top-level fields)
    # ========================================================================
    
    if "system_flags" not in updated_state:
        updated_state["system_flags"] = {}

    system_flags = updated_state["system_flags"].copy()
    
    # Store pressure level 
    system_flags["constraint_pressure_level"] = analysis_result.constraint_pressure_level.value
    
    # CORRECTION 6: Crisis mode automatic overload
    if life_mode == "crisis":
        system_flags["overload_detected"] = True
        logger.warning("CRISIS MODE: Automatic overload detection activated")
    # CORRECTION 7: Overload threshold rules
    elif constraint_score >= 9:
        system_flags["overload_detected"] = True
        system_flags["reentry_required"] = True
        logger.warning(f"CRITICAL OVERLOAD: Score {constraint_score:.1f} triggers re-entry protocol")
    elif constraint_score >= 7:
        system_flags["overload_detected"] = True
        logger.warning(f"OVERLOAD DETECTED: Score {constraint_score:.1f} exceeds threshold 7")
    else:
        system_flags["overload_detected"] = False

    # Store constraint diagnostics for debugging
    system_flags["constraint_diagnostics"] = {
        "constraint_count": analysis_result.constraint_count,
        "categories": analysis_result.constraint_categories_present,
        "cluster_count": len(analysis_result.constraint_clusters),
        "conflict_count": len(analysis_result.constraint_conflicts),
        "flexibility_score": analysis_result.flexibility_score,
    }

    updated_state["system_flags"] = system_flags

    # ========================================================================
    # CORRECTION 8: Populate forecast_data.initial_constraint_map properly
    # ========================================================================
    
    if "forecast_data" not in updated_state:
        updated_state["forecast_data"] = {}

    forecast_data = updated_state["forecast_data"].copy()
    
    # Build category summary for forecast engine
    category_summary = {
        category: len([c for c in analysis_result.constraint_categories_present if c == category])
        for category in analysis_result.constraint_categories_present
    }
    
    # CORRECTION 8: Structured forecast context (no predictions, only constraint interpretation)
    forecast_data["initial_constraint_map"] = {
        "constraint_score": round(constraint_score, 2),
        "pressure_level": analysis_result.constraint_pressure_level.value,
        "clusters": analysis_result.constraint_clusters,
        "conflicts": analysis_result.constraint_conflicts,
        "categories": category_summary,
    }

    updated_state["forecast_data"] = forecast_data

    # ========================================================================
    # CORRECTION 9: Standardized execution trace entries (dict format)
    # ========================================================================
    
    if "execution_trace" not in updated_state:
        updated_state["execution_trace"] = []

    execution_trace = updated_state["execution_trace"].copy()
    
    # Append standardized trace entry with timestamp
    trace_entry = {
        "node": "constraint_analyzer",
        "timestamp": datetime.utcnow().isoformat(),
        "constraint_score": round(constraint_score, 2),
        "pressure_level": analysis_result.constraint_pressure_level.value,
    }
    execution_trace.append(trace_entry)
    updated_state["execution_trace"] = execution_trace

    # Update last node executed
    updated_state["last_node_executed"] = "constraint_analyzer"

    logger.info(
        f"State updated successfully. Score: {constraint_score:.1f}, "
        f"Overload: {system_flags['overload_detected']}, "
        f"Pressure: {system_flags['constraint_pressure_level']}"
    )

    return updated_state


def _calculate_days_since_last_analysis(user_history: Dict[str, Any]) -> int:
    """
    Calculate days since last analysis from user history.

    Args:
        user_history: User history dict

    Returns:
        Days since last interaction
    """
    # This is a simplified calculation. In production, you'd compare
    # last_interaction timestamp with current time.
    return 0  # Assume fresh analysis


def _is_environment_restrictive(environment_context: Dict[str, Any]) -> bool:
    """
    Determine if environment context indicates restrictions.

    Args:
        environment_context: Environment context dict

    Returns:
        True if environment is restrictive
    """
    return (
        environment_context.get("indoor_only", False)
        or environment_context.get("small_space", False)
        or environment_context.get("shared_room", False)
    )


def _estimate_user_adaptive_capacity(user_history: Dict[str, Any]) -> float:
    """
    Estimate user's adaptive capacity based on history.

    Args:
        user_history: User history dict

    Returns:
        Adaptive capacity 0-1 (0.5 = average)
    """
    # Base capacity
    capacity = 0.5

    # Increase if user has completed plans
    completion_rate = user_history.get("average_plan_completion", 0.5)
    if completion_rate > 0.7:
        capacity += 0.2
    elif completion_rate < 0.3:
        capacity -= 0.1

    # Consider experience level (total plans)
    total_plans = user_history.get("total_plans_generated", 0)
    if total_plans > 10:
        capacity += 0.1
    elif total_plans == 0:
        capacity -= 0.1

    # Clamp to valid range
    return max(0.0, min(1.0, capacity))


def _estimate_recent_overload_count(user_history: Dict[str, Any]) -> int:
    """
    Estimate recent overload count from user history.

    Args:
        user_history: User history dict

    Returns:
        Recent overload count 0-3
    """
    # In a full implementation, this would check recent interaction patterns
    # For now, use a simple heuristic based on completion rate
    average_completion = user_history.get("average_plan_completion", 0.5)

    if average_completion < 0.2:
        return 3  # Frequent failures indicate overload
    elif average_completion < 0.4:
        return 2
    elif average_completion < 0.6:
        return 1
    else:
        return 0


# Export node for integration
__all__ = ["constraint_analyzer_node"]
