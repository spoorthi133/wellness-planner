"""
Constraint Forecast Engine Module

This module predicts upcoming constraint patterns and identifies periods of
reduced pressure and opportunity for adaptation or recovery.

Exports:
- ConstraintForecastEngine: Main forecasting orchestrator
- constraint_forecast_node: LangGraph node interface
- All prediction utilities and models
"""

from forecast_models import (
    SeverityLevel,
    DisruptionType,
    PredictedEnergyDip,
    PredictedScheduleDisruption,
    OpportunityWindow,
    ForecastMetadata,
    ForecastResult,
    ForecastValidationResult,
    ConstraintHistoryEntry,
    PredictionFactors,
)

from forecast_utils import (
    predict_energy_dips,
    predict_schedule_disruptions,
    detect_opportunity_windows,
    calculate_forecast_confidence,
    compute_forecast_expiry,
    validate_forecast_input,
    calculate_data_quality_rating,
)

from forecast_engine import ConstraintForecastEngine

from forecast_node import constraint_forecast_node

__all__ = [
    # Models
    "SeverityLevel",
    "DisruptionType",
    "PredictedEnergyDip",
    "PredictedScheduleDisruption",
    "OpportunityWindow",
    "ForecastMetadata",
    "ForecastResult",
    "ForecastValidationResult",
    "ConstraintHistoryEntry",
    "PredictionFactors",
    # Utilities
    "predict_energy_dips",
    "predict_schedule_disruptions",
    "detect_opportunity_windows",
    "calculate_forecast_confidence",
    "compute_forecast_expiry",
    "validate_forecast_input",
    "calculate_data_quality_rating",
    # Engine
    "ConstraintForecastEngine",
    # Node
    "constraint_forecast_node",
]

__version__ = "1.0.0"
__author__ = "Wellness Agent Development Team"
