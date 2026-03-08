"""
Environment Adapter Module

Adapts planning context based on physical environment constraints.

Ensures that planning recommendations account for:
- Indoor/outdoor availability
- Space limitations
- Noise restrictions
- Equipment availability
- Privacy requirements

Module: Environment Adapter
Part of: Constraint-First Wellness Agent (Module A)

Classes:
    EnvironmentAdapterManager: Main orchestrator for environment adaptation

Functions:
    environment_adapter_node: LangGraph integration node
    get_environment_adapter_node_config: Configuration for LangGraph
    validate_node_inputs: Input validation

Models:
    EnvironmentContextExtended: Extended environment context with derived fields
    EnvironmentAdaptationSummary: Summary of adaptations needed
"""

from environment_models import (
    EnvironmentType,
    ActivityType,
    EnvironmentRestriction,
    ActivityRestrictionReason,
    ActivityModifier,
    EnvironmentComplexityFactors,
    EnvironmentAdaptationSummary,
    EnvironmentContextExtended,
)

from environment_adapter import EnvironmentAdapterManager

from environment_node import (
    environment_adapter_node,
    get_environment_adapter_node_config,
    validate_node_inputs,
)

__all__ = [
    # Models
    "EnvironmentType",
    "ActivityType",
    "EnvironmentRestriction",
    "ActivityRestrictionReason",
    "ActivityModifier",
    "EnvironmentComplexityFactors",
    "EnvironmentAdaptationSummary",
    "EnvironmentContextExtended",
    # Manager
    "EnvironmentAdapterManager",
    # Node functions
    "environment_adapter_node",
    "get_environment_adapter_node_config",
    "validate_node_inputs",
]

__version__ = "1.0.0"
__module_name__ = "Environment Adapter"
__description__ = "Adapts planning context based on physical environment constraints"
