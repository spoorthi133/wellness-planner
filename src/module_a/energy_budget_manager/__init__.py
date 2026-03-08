"""
Energy Budget Manager Module

Manages daily energy allocation based on constraints and forecasts.

Treats human energy as a daily resource and determines:
- How much effort the user can realistically spend
- When recovery periods are needed
- When plans must be simplified

Module: Energy Budget Manager
Part of: Constraint-First Wellness Agent (Module A)

Classes:
    EnergyBudgetManager: Main orchestrator for energy budget calculations

Functions:
    energy_budget_node: LangGraph integration node
    get_energy_budget_node_config: Configuration for LangGraph
    validate_node_inputs: Input validation

Models:
    EnergyBudgetState: Complete energy budget state
    EnergyBudgetMetrics: Energy metrics for display
    TaskCategory: Task category enumeration
    ConstraintPressureLevel: Pressure level enumeration
"""

from energy_models import (
    EnergySource,
    TaskCategory,
    ConstraintPressureLevel,
    EnergyDipSeverity,
    BaseEnergyBudget,
    TaskEnergyCost,
    RecoveryProfile,
    ConstraintAdjustment,
    ForecastAdjustment,
    AllocatedTask,
    EnergyBudgetMetrics,
    EnergyBudgetState,
)

from energy_manager import EnergyBudgetManager

from energy_node import (
    energy_budget_node,
    get_energy_budget_node_config,
    validate_node_inputs,
)

__all__ = [
    # Models
    "EnergySource",
    "TaskCategory",
    "ConstraintPressureLevel",
    "EnergyDipSeverity",
    "BaseEnergyBudget",
    "TaskEnergyCost",
    "RecoveryProfile",
    "ConstraintAdjustment",
    "ForecastAdjustment",
    "AllocatedTask",
    "EnergyBudgetMetrics",
    "EnergyBudgetState",
    # Manager
    "EnergyBudgetManager",
    # Node functions
    "energy_budget_node",
    "get_energy_budget_node_config",
    "validate_node_inputs",
]

__version__ = "1.0.0"
__module_name__ = "Energy Budget Manager"
__description__ = "Manages daily energy allocation as a resource"
