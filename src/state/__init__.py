"""
State Model & Persistence Layer Package

Core state management for Constraint-First Wellness Agent.
Implements LangGraph-compatible state schema with Supabase persistence.

Module: State Model & Persistence Layer (Module A)
Part of: Constraint-First Wellness Agent
"""

# Agent State and Schemas
from .agent_state import (
    AgentState,
    AgentStateDict,
    Constraint,
    EnergyBudget,
    EnvironmentContext,
    Forecast,
    Plan,
    Insight,
    UserHistory,
    SystemFlags,
    LifeMode,
    MotivationStyle,
)

# State Management Functions
from .state_manager import (
    create_default_state,
    load_state,
    save_state,
    update_state,
    update_constraints,
    update_energy_budget,
    update_environment,
    update_life_mode,
    update_motivation_style,
    add_constraint,
    remove_constraint,
    set_plan,  # RENAMED: Correction 1
    add_insight,
    mark_onboarded,
    increment_plan_count,
    record_micro_win,
    state_to_dict,  # NEW: Correction 2 - LangGraph conversion
    dict_to_state,  # NEW: Correction 2 - LangGraph conversion
    get_state_summary,
    get_validation_report,
)

# Validation Functions
from .validators import (
    StateValidator,
    StateValidationError,
    validate_state,
    assert_valid,
)

# Persistence Layer
from .persistence import (
    SupabasePersistence,
    SupabaseConfig,
    initialize_persistence,
    get_persistence,
)

__version__ = "1.0.0"

__all__ = [
    # State Schema
    "AgentState",
    "AgentStateDict",
    "Constraint",
    "EnergyBudget",
    "EnvironmentContext",
    "Forecast",
    "Plan",
    "Insight",
    "UserHistory",
    "SystemFlags",
    "LifeMode",
    "MotivationStyle",
    # State Management
    "create_default_state",
    "load_state",
    "save_state",
    "update_state",
    "update_constraints",
    "update_energy_budget",
    "update_environment",
    "update_life_mode",
    "update_motivation_style",
    "add_constraint",
    "remove_constraint",
    "set_plan",  # RENAMED: Correction 1
    "add_insight",
    "mark_onboarded",
    "increment_plan_count",
    "record_micro_win",
    "state_to_dict",  # NEW: Correction 2
    "dict_to_state",  # NEW: Correction 2
    "get_state_summary",
    "get_validation_report",
    # Validation
    "StateValidator",
    "StateValidationError",
    "validate_state",
    "assert_valid",
    # Persistence
    "SupabasePersistence",
    "SupabaseConfig",
    "initialize_persistence",
    "get_persistence",
]
