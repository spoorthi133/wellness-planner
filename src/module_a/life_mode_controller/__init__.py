"""
Life Mode Controller Package

Module 6 of the Constraint-First Wellness Agent.

This module determines the current life phase of the user and sets the global
operating mode for the planning system. It functions as the system's mood selector.

Key Functionality:
- Detects candidate life modes based on system signals
- Resolves conflicts using priority hierarchy
- Calculates confidence scores
- Retrieves behavior profiles
- Generates human-readable explanations

Supported Life Modes:
- maintenance: Default balanced state
- growth: User pushing progress
- recovery: User rebuilding energy
- crisis: System protection mode
- exam_mode: Academic pressure
- travel_mode: Environment disruption
- work_crunch_mode: High professional workload
- social_week_mode: Heavy social commitments

Position in LangGraph Pipeline:
User Input
   ↓
Constraint Analyzer
   ↓
Constraint Forecast Engine
   ↓
Energy Budget Manager
   ↓
Environment Adapter
   ↓
Life Mode Controller   ← THIS MODULE
   ↓
Plan Request Node (LLM)

Module: Life Mode Controller
Part of: Constraint-First Wellness Agent (Module A)
"""

from life_mode_models import (
    LifeModeName,
    ActivityIntensity,
    PlanComplexity,
    RecoveryPriority,
    ModeDetectionSignal,
    ModeProfile,
    LifeModeDetectionResult,
    LifeModeContext,
    LifeModeResolution,
    ConfidenceFactors,
    LifeModeSelection,
    ModePriorityMap,
    LifeModeControllerMetadata,
)

from life_mode_utils import (
    get_mode_priority_map,
    get_mode_profiles,
    detect_life_mode,
    resolve_mode_priority,
    get_mode_profile,
    calculate_mode_confidence,
    generate_mode_reason,
    calculate_mode_stability,
    estimate_mode_duration,
)

from life_mode_controller import LifeModeController

from life_mode_node import life_mode_controller_node

__all__ = [
    # Models
    "LifeModeName",
    "ActivityIntensity",
    "PlanComplexity",
    "RecoveryPriority",
    "ModeDetectionSignal",
    "ModeProfile",
    "LifeModeDetectionResult",
    "LifeModeContext",
    "LifeModeResolution",
    "ConfidenceFactors",
    "LifeModeSelection",
    "ModePriorityMap",
    "LifeModeControllerMetadata",
    # Utils
    "get_mode_priority_map",
    "get_mode_profiles",
    "detect_life_mode",
    "resolve_mode_priority",
    "get_mode_profile",
    "calculate_mode_confidence",
    "generate_mode_reason",
    "calculate_mode_stability",
    "estimate_mode_duration",
    # Controller
    "LifeModeController",
    # LangGraph Node
    "life_mode_controller_node",
]

__version__ = "1.0.0"
__author__ = "Wellness Planner Team"
__module_name__ = "Life Mode Controller"
