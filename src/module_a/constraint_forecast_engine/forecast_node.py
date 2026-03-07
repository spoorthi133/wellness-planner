"""
Forecast Node - LangGraph integration for constraint forecasting.

Implements the LangGraph node interface, state management, and orchestration
of the forecasting pipeline within the wellness agent graph.

SCHEMA COMPLIANCE NOTES (from Constraint Engine Module):
- CORRECTION 1: Do not add new top-level state fields
- Only update: forecast_data (existing), system_flags (existing), execution_trace (existing)
- Results stored in: forecast_data.predicted_* fields
- Metadata stored in: forecast_data.metadata
- Timestamps use ISO format
- Execution trace entries as dicts with node, timestamp, and relevant metrics
"""

import logging
from datetime import datetime
from typing import Dict, Any
from copy import deepcopy

from forecast_engine import ConstraintForecastEngine
from forecast_utils import (
    validate_forecast_input,
    calculate_data_quality_rating,
)
from forecast_models import PredictionFactors

logger = logging.getLogger(__name__)


def constraint_forecast_node(state: Dict) -> Dict:
    """
    LangGraph node for constraint forecasting.
    
    Responsible for:
    1. Reading initial_constraint_map from Constraint Engine
    2. Preparing prediction factors
    3. Generating forecast predictions
    4. Updating state with results
    5. Appending execution trace
    
    SCHEMA COMPLIANCE:
    - Input: state.forecast_data.initial_constraint_map (from Constraint Engine)
    - Output: state.forecast_data.predicted_energy_dips/disruptions/windows
    - No new top-level fields added (CORRECTION 1)
    
    Args:
        state: LangGraph agent state dictionary
        
    Returns:
        Updated state with forecast data populated
    """
    logger.info(f"Starting constraint forecast node")
    
    # Make a copy to avoid mutating original
    updated_state = deepcopy(state)
    updated_state["last_node_executed"] = "constraint_forecast_engine"
    # Extract initial constraint map from Constraint Engine output
    constraint_map = state.get("forecast_data", {}).get("initial_constraint_map", {})
    
    if not constraint_map:
        logger.warning("No initial_constraint_map found; skipping forecast")
        _append_trace_entry(updated_state, error=True)
        return updated_state
    
    # Step 1: Extract and prepare prediction factors
    logger.debug("Preparing prediction factors...")
    try:
        factors = _prepare_prediction_factors(state, constraint_map)
    except Exception as e:
        logger.error(f"Failed to prepare factors: {e}")
        _append_trace_entry(updated_state, error=True)
        return updated_state
    
    # Step 2: Validate inputs
    validation = validate_forecast_input(factors)
    if validation.warnings:
        for warning in validation.warnings:
            logger.warning(f"Forecast input warning: {warning}")
    
    if not validation.is_valid:
        logger.error(f"Forecast validation failed: {validation.errors}")
        _append_trace_entry(updated_state, error=True)
        return updated_state
    
    # Step 3: Generate forecast
    logger.debug("Generating forecast with ConstraintForecastEngine...")
    engine = ConstraintForecastEngine(forecast_window_days=7)
    
    try:
        forecast_result = engine.forecast(factors)
    except Exception as e:
        logger.error(f"Forecast generation failed: {e}")
        _append_trace_entry(updated_state, error=True)
        return updated_state
    
    # Step 4: Update state with forecast data (SCHEMA COMPLIANT)
    logger.debug("Updating state with forecast results...")
    _update_state_with_forecast(updated_state, forecast_result, factors, engine)
    
    # Step 5: Append execution trace entry
    _append_trace_entry(updated_state, forecast_result)
    
    # Step 6: Update last node executed
    updated_state["last_node_executed"] = "constraint_forecast_engine"
    
    logger.info("Constraint forecast node complete")
    
    return updated_state


def _prepare_prediction_factors(state: Dict, constraint_map: Dict) -> PredictionFactors:
    """
    Prepare prediction factors from state and constraint map.
    
    Extracts all available data to build the PredictionFactors object
    used by the forecast engine.
    
    Args:
        state: LangGraph agent state
        constraint_map: Initial constraint analysis (from Constraint Engine)
        
    Returns:
        PredictionFactors object ready for forecasting
    """
    # Extract from constraint map
    current_score = constraint_map.get("constraint_score", 5.0)
    pressure_level = constraint_map.get("pressure_level", "MODERATE")
    clusters = constraint_map.get("clusters", {})
    conflicts = constraint_map.get("conflicts", [])
    categories = constraint_map.get("categories", {})
    
    # Extract from system flags
    system_flags = state.get("system_flags", {})
    overload_history = system_flags.get("overload_history", 0)
    constraint_diagnostics = system_flags.get("constraint_diagnostics", {})
    
    # Extract from user history
    user_history = state.get("user_history", {})
    constraint_history = user_history.get("constraint_history", [])
    recent_constraint_frequency = len([
        h for h in constraint_history[-7:] if h.get("constraint_score", 0) > 5
    ])
    recovery_periods = len([
        h for h in constraint_history[-30:] if h.get("life_mode") == "recovery"
    ])
    user_history_sample_size = len(constraint_history)
    
    # Extract from environment context
    environment = state.get("environment_context", {})
    environment_stability = environment.get("stability", "variable")  # stable/variable/unstable
    schedule_regularity = environment.get("schedule_regularity", "irregular")  # regular/irregular
    
    # Extract user adaptation capacity
    adaptation_capacity = _estimate_adaptation_capacity(state)
    
    # Extract life mode
    life_mode = state.get("life_mode", "maintenance")
    
    def _cluster_count(value):
        """Normalize cluster value to a count."""
        if isinstance(value, list):
            return len(value)
        if isinstance(value, int):
            return value
        return 0


    cluster_counts = {
        "time": _cluster_count(clusters.get("time")),
        "energy": _cluster_count(clusters.get("energy")),
        "environment": _cluster_count(clusters.get("environment")),
        "social": _cluster_count(clusters.get("social")),
        "mental": _cluster_count(clusters.get("mental")),
        "physical": _cluster_count(clusters.get("physical")),
        "logistical": _cluster_count(clusters.get("logistical")),
    }
    
    return PredictionFactors(
        current_constraint_score=min(10.0, max(0.0, current_score)),
        pressure_level=pressure_level,
        life_mode=life_mode,
        constraint_clusters=cluster_counts,
        constraint_conflicts=conflicts,
        recent_constraint_frequency=recent_constraint_frequency,
        overload_history=overload_history,
        recovery_periods=recovery_periods,
        environment_stability=environment_stability,
        schedule_regularity=schedule_regularity,
        adaptation_capacity=min(1.0, max(0.0, adaptation_capacity)),
        user_history_sample_size=user_history_sample_size,
    )


def _estimate_adaptation_capacity(state: Dict) -> float:
    """
    Estimate user's capacity to adapt to constraints.
    
    Based on past recovery periods, flexibility scores, and life mode.
    
    Args:
        state: LangGraph agent state
        
    Returns:
        Adaptation capacity score 0-1
    """
    base = 0.5
    
    # Higher in growth/maintenance mode
    life_mode = state.get("life_mode", "maintenance")
    if life_mode == "growth":
        base += 0.2
    elif life_mode == "recovery":
        base -= 0.1
    elif life_mode == "crisis":
        base -= 0.3
    
    # Reduced by constraint score
    constraint_map = state.get("forecast_data", {}).get("initial_constraint_map", {})
    score = constraint_map.get("constraint_score", 5.0)
    if score > 7:
        base -= 0.2
    
    # Increased by history of recovery periods
    user_history = state.get("user_history", {})
    recovery_periods = len([
        h for h in user_history.get("constraint_history", [])[-30:]
        if h.get("life_mode") == "recovery"
    ])
    if recovery_periods >= 3:
        base += 0.15
    
    return min(1.0, max(0.0, base))


def _update_state_with_forecast(
    state: Dict,
    forecast_result,
    factors,
    engine: ConstraintForecastEngine,
) -> None:
    """
    Update state with forecast results (SCHEMA COMPLIANT).
    
    Stores predictions in state.forecast_data.* fields only.
    Does not add new top-level state fields (CORRECTION 1).
    
    Args:
        state: State dict to update
        forecast_result: Generated forecast
        factors: Prediction factors used
        engine: Forecast engine for impact estimation
    """
    # Ensure forecast_data exists
    if "forecast_data" not in state:
        state["forecast_data"] = {}
    
    forecast_data = state["forecast_data"]
    
    # Store predictions (never overwrites initial_constraint_map)
    forecast_data["predicted_energy_dips"] = [
        d.model_dump() for d in forecast_result.predicted_energy_dips
    ]
    
    forecast_data["predicted_schedule_disruptions"] = [
        d.model_dump() for d in forecast_result.predicted_schedule_disruptions
    ]
    
    forecast_data["opportunity_windows"] = [
        w.model_dump() for w in forecast_result.opportunity_windows
    ]
    
    forecast_data["forecast_confidence"] = forecast_result.metadata.forecast_confidence
    forecast_data["forecast_window_days"] = forecast_result.metadata.forecast_window_days
    forecast_data["generated_at"] = forecast_result.metadata.generated_at.isoformat()
    forecast_data["expires_at"] = forecast_result.metadata.expires_at.isoformat()
    forecast_data["forecast_summary"] = forecast_result.summary
    
    # Update system flags with forecast impact (no new top-level fields)
    if "system_flags" not in state:
        state["system_flags"] = {}
    
    system_flags = state["system_flags"]
    
    # Add forecast diagnostics to system_flags
    if "forecast_diagnostics" not in system_flags:
        system_flags["forecast_diagnostics"] = {}
    
    impact_analysis = engine.estimate_system_impact(forecast_result, factors)
    system_flags["forecast_diagnostics"].update({
        "energy_preservation_needed": impact_analysis["energy_preservation_needed"],
        "schedule_flexibility_required": impact_analysis["schedule_flexibility_required"],
        "recovery_priority": impact_analysis["recovery_priority"],
        "opportunity_utilization": impact_analysis["opportunity_utilization"],
        "planning_complexity": impact_analysis["planning_complexity"],
        "recommended_intervention": impact_analysis["recommended_intervention"],
        "energy_dip_count": len(forecast_result.predicted_energy_dips),
        "disruption_count": len(forecast_result.predicted_schedule_disruptions),
        "opportunity_count": len(forecast_result.opportunity_windows),
        "forecast_confidence": forecast_result.metadata.forecast_confidence,
        "data_quality": forecast_result.metadata.data_quality,
    })


def _append_trace_entry(state: Dict, forecast_result=None, error: bool = False) -> None:
    """
    Append execution trace entry.
    
    CORRECTION 9 (from Constraint Engine): Standardize trace entries as dicts
    with node, timestamp, and relevant metrics.
    
    Args:
        state: State to update
        forecast_result: Forecast result (if successful)
        error: Whether this is an error entry
    """
    if "execution_trace" not in state:
        state["execution_trace"] = []
    
    trace_entry = {
        "node": "constraint_forecast_engine",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if forecast_result and not error:
        trace_entry.update({
            "forecast_confidence": forecast_result.metadata.forecast_confidence,
            "energy_dips_count": len(forecast_result.predicted_energy_dips),
            "disruptions_count": len(forecast_result.predicted_schedule_disruptions),
            "opportunities_count": len(forecast_result.opportunity_windows),
            "data_quality": forecast_result.metadata.data_quality,
            "status": "success",
        })
    else:
        trace_entry["status"] = "error"
    
    state["execution_trace"].append(trace_entry)
