"""
State Manager

High-level state management functions for LangGraph integration.
Handles state creation, loading, saving, and updates.

Module: State Model & Persistence Layer
Part of: Constraint-First Wellness Agent
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging
import uuid
from .agent_state import (
    AgentState, Constraint, EnergyBudget, EnvironmentContext,
    Forecast, Plan, Insight, UserHistory, SystemFlags,
    LifeMode, MotivationStyle
)
from .validators import StateValidator, StateValidationError, validate_state
from .persistence import get_persistence

logger = logging.getLogger(__name__)


def create_default_state(
    user_id: str,
    session_id: Optional[str] = None,
    **kwargs
) -> AgentState:
    """
    Create a clean, valid default agent state.
    
    Initializes safe defaults for all required fields.
    Suitable for new users or session resets.
    
    Args:
        user_id: Required user identifier
        session_id: Optional session ID (generated if not provided)
        **kwargs: Optional overrides for specific fields
        
    Returns:
        Valid AgentState with safe defaults
        
    Raises:
        StateValidationError: If user_id is invalid
    """
    if not user_id or not user_id.strip():
        raise StateValidationError("user_id is required and cannot be empty")

    session_id = session_id or str(uuid.uuid4())

    # Default energy budget (30-40-20-10 split)
    energy_budget = EnergyBudget(
        daily_total=100,
        morning=30,
        afternoon=40,
        evening=20,
        contingency=10,
    )

    # Default environment context
    environment_context = EnvironmentContext(
        timezone="UTC",
        work_hours={"start": "09:00", "end": "17:00"},
        commute_time_minutes=0,
        social_obligations_weekly=0,
        caregiving_hours_weekly=0.0,
        pets=0,
        living_situation="independent",
    )

    # Default forecast
    forecast_data = Forecast(
        period="week",
        predicted_energy_level=50.0,
        expected_disruptions=[],
        opportunity_windows=[],
        confidence_score=0.5,
    )

    # Empty initial constraints
    constraints = []

    # User history for new user
    user_history = UserHistory(
        total_plans_generated=0,
        plans_completed=0,
        micro_wins_achieved=0,
        days_active=1,
        last_interaction=datetime.utcnow(),
        feedback_provided=0,
        average_plan_completion=0.0,
    )

    # System flags for new user
    system_flags = SystemFlags(
        is_onboarded=False,
        requires_replan=False,
        emergency_mode=False,
        data_sync_pending=False,
        last_sync=datetime.utcnow(),
    )

    # Create base state
    state = AgentState(
        user_id=user_id,
        session_id=session_id,
        constraints=constraints,
        forecast_data=forecast_data,
        energy_budget=energy_budget,
        environment_context=environment_context,
        life_mode=LifeMode.MAINTENANCE,
        motivation_style=MotivationStyle.PROGRESS_TRACKING,
        plan=None,  # RENAMED: current_plan -> plan
        recent_insights=[],
        user_history=user_history,
        system_flags=system_flags,
        version=1,
    )

    # Apply any provided overrides
    if kwargs:
        state = update_state(state, kwargs)

    # Validate before returning
    StateValidator.assert_valid_state(state)
    logger.info(f"Created default state for user {user_id}")

    return state


def load_state(user_id: str) -> Optional[AgentState]:
    """
    Load user's saved state from persistence layer.
    
    Attempts to restore complete state from database.
    If user not found, returns None.
    
    Args:
        user_id: User identifier
        
    Returns:
        Loaded AgentState or None if user not found
    """
    try:
        persistence = get_persistence()
        state = persistence.load_full_state(user_id)

        if state:
            StateValidator.assert_valid_state(state)
            logger.info(f"Loaded state for user {user_id}")
            return state
        else:
            logger.info(f"No saved state found for user {user_id}")
            return None

    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return None


def save_state(state: AgentState) -> bool:
    """
    Save current state to persistence layer.
    
    Persists state across all tables.
    Validates before saving.
    
    Args:
        state: AgentState to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate before saving
        StateValidator.assert_valid_state(state)

        # Update timestamp
        state.last_updated = datetime.utcnow()

        # Save to persistence
        persistence = get_persistence()
        success = persistence.save_full_state(state)

        if success:
            logger.info(f"State saved for user {state.user_id}")
        else:
            logger.warning(f"Partial failure saving state for user {state.user_id}")

        return success

    except StateValidationError as e:
        logger.error(f"State validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to save state: {e}")
        return False


def update_state(state: AgentState, updates: Dict[str, Any]) -> AgentState:
    """
    Apply updates to state and return new instance.
    
    Creates updated state without mutating original.
    Validates updated state before returning.
    
    Args:
        state: Current AgentState
        updates: Dictionary of fields to update
        
    Returns:
        Updated AgentState instance
        
    Raises:
        StateValidationError: If updates result in invalid state
    """
    try:
        # Convert state to dict for update
        state_dict = state.dict()

        # Apply updates
        state_dict.update(updates)

        # Create new state from updated dict
        updated_state = AgentState(**state_dict)

        # Validate
        StateValidator.assert_valid_state(updated_state)

        logger.info(f"State updated for user {state.user_id} with fields: {', '.join(updates.keys())}")
        return updated_state

    except Exception as e:
        logger.error(f"Failed to update state: {e}")
        raise StateValidationError(f"Failed to update state: {e}")


def update_constraints(state: AgentState, constraints: list) -> AgentState:
    """
    Update state constraints.
    
    Args:
        state: Current AgentState
        constraints: List of new constraints
        
    Returns:
        Updated AgentState
    """
    return update_state(state, {"constraints": constraints})


def update_energy_budget(state: AgentState, budget_updates: Dict[str, float]) -> AgentState:
    """
    Update energy budget allocation.
    
    Args:
        state: Current AgentState
        budget_updates: Dictionary of budget field updates
        
    Returns:
        Updated AgentState
    """
    current_budget = state.energy_budget.dict()
    current_budget.update(budget_updates)
    new_budget = EnergyBudget(**current_budget)
    return update_state(state, {"energy_budget": new_budget})


def update_environment(state: AgentState, env_updates: Dict[str, Any]) -> AgentState:
    """
    Update environment context.
    
    Args:
        state: Current AgentState
        env_updates: Dictionary of environment field updates
        
    Returns:
        Updated AgentState
    """
    current_env = state.environment_context.dict()
    current_env.update(env_updates)
    new_env = EnvironmentContext(**current_env)
    return update_state(state, {"environment_context": new_env})


def update_life_mode(state: AgentState, mode: str) -> AgentState:
    """
    Update user's life mode.
    
    Args:
        state: Current AgentState
        mode: New life mode ("maintenance", "growth", "recovery", "crisis")
        
    Returns:
        Updated AgentState
    """
    return update_state(state, {"life_mode": LifeMode(mode)})


def update_motivation_style(state: AgentState, style: str) -> AgentState:
    """
    Update user's motivation style.
    
    Args:
        state: Current AgentState
        style: New motivation style
        
    Returns:
        Updated AgentState
    """
    return update_state(state, {"motivation_style": MotivationStyle(style)})


def add_constraint(state: AgentState, constraint: Constraint) -> AgentState:
    """
    Add a new constraint to state.
    
    Args:
        state: Current AgentState
        constraint: Constraint to add
        
    Returns:
        Updated AgentState
    """
    new_constraints = state.constraints + [constraint]
    return update_constraints(state, new_constraints)


def remove_constraint(state: AgentState, constraint_id: str) -> AgentState:
    """
    Remove a constraint from state by ID.
    
    Args:
        state: Current AgentState
        constraint_id: ID of constraint to remove
        
    Returns:
        Updated AgentState
    """
    new_constraints = [c for c in state.constraints if c.id != constraint_id]
    return update_constraints(state, new_constraints)


def set_plan(state: AgentState, plan: Plan) -> AgentState:
    """
    Set the plan in state.
    
    Args:
        state: Current AgentState
        plan: Plan to set
        
    Returns:
        Updated AgentState
    """
    return update_state(state, {"plan": plan})


def add_insight(state: AgentState, insight: Insight) -> AgentState:
    """
    Add an insight to recent insights.
    
    Args:
        state: Current AgentState
        insight: Insight to add
        
    Returns:
        Updated AgentState
    """
    new_insights = state.recent_insights + [insight]
    # Keep only last 10 insights
    new_insights = new_insights[-10:]
    return update_state(state, {"recent_insights": new_insights})


def mark_onboarded(state: AgentState) -> AgentState:
    """
    Mark user as onboarded.
    
    Args:
        state: Current AgentState
        
    Returns:
        Updated AgentState
    """
    new_flags = state.system_flags.dict()
    new_flags["is_onboarded"] = True
    return update_state(state, {"system_flags": SystemFlags(**new_flags)})


def increment_plan_count(state: AgentState) -> AgentState:
    """
    Increment plan generation counter.
    
    Args:
        state: Current AgentState
        
    Returns:
        Updated AgentState
    """
    history = state.user_history.dict()
    history["total_plans_generated"] += 1
    history["last_interaction"] = datetime.utcnow()
    return update_state(state, {"user_history": UserHistory(**history)})


def record_micro_win(state: AgentState) -> AgentState:
    """
    Record a micro-win achievement.
    
    Args:
        state: Current AgentState
        
    Returns:
        Updated AgentState
    """
    history = state.user_history.dict()
    history["micro_wins_achieved"] += 1
    history["last_interaction"] = datetime.utcnow()
    return update_state(state, {"user_history": UserHistory(**history)})


# ============================================================================
# LangGraph State Conversion Utilities (Correction 2)
# ============================================================================

def state_to_dict(state: AgentState) -> dict:
    """
    Convert Pydantic AgentState to JSON-safe dictionary for LangGraph nodes.
    
    LangGraph nodes operate on dictionaries, not Pydantic models.
    This conversion ensures datetime objects are ISO strings and all
    nested objects are JSON-serializable.
    
    Args:
        state: AgentState to convert
        
    Returns:
        JSON-safe dictionary representation
    """
    state_dict = state.dict(exclude_unset=False, by_alias=False)
    # Datetime objects are already converted by Pydantic config
    return state_dict


def dict_to_state(data: dict) -> AgentState:
    """
    Convert dictionary to validated AgentState.
    
    LangGraph nodes return dictionaries that need to be converted
    back to AgentState. This function validates during conversion
    to catch any schema violations.
    
    Args:
        data: Dictionary representation of state
        
    Returns:
        Validated AgentState
        
    Raises:
        StateValidationError: If state fails validation
    """
    state = AgentState(**data)
    StateValidator.assert_valid_state(state)
    return state


def get_state_summary(state: AgentState) -> Dict[str, Any]:
    """
    Get a summary of current state for logging/debugging.
    
    Args:
        state: AgentState to summarize
        
    Returns:
        Dictionary with state summary
    """
    return {
        "user_id": state.user_id,
        "session_id": state.session_id,
        "life_mode": state.life_mode.value,
        "motivation_style": state.motivation_style.value,
        "constraints_count": len(state.constraints),
        "has_plan": state.plan is not None,
        "recent_insights_count": len(state.recent_insights),
        "plans_generated": state.user_history.total_plans_generated,
        "micro_wins": state.user_history.micro_wins_achieved,
        "is_onboarded": state.system_flags.is_onboarded,
        "version": state.version,
        "state_version": state.state_version,
        "last_node_executed": state.last_node_executed,
        "last_updated": state.last_updated.isoformat(),
    }


def get_validation_report(state: AgentState) -> str:
    """
    Get detailed validation report for state.
    
    Args:
        state: AgentState to validate
        
    Returns:
        Formatted validation report
    """
    return StateValidator.get_validation_report(state)
