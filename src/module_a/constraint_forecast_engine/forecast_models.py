"""
Forecast Models - Data structures for constraint forecasting.

Defines all Pydantic models used in the Constraint Forecast Engine pipeline.
These models handle energy dips, schedule disruptions, opportunity windows,
and forecast metadata.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class SeverityLevel(str, Enum):
    """Severity levels for predicted events."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DisruptionType(str, Enum):
    """Types of schedule disruptions."""
    DEADLINE_PRESSURE = "deadline_pressure"
    TRAVEL_DISRUPTION = "travel_disruption"
    SOCIAL_CONFLICT = "social_conflict"
    ENVIRONMENT_STRESS = "environment_stress"
    RECOVERY_NEEDED = "recovery_needed"
    COMPOUNDING_LOAD = "compounding_load"


class PredictedEnergyDip(BaseModel):
    """Prediction of a period with reduced energy availability."""
    day_offset: int = Field(..., ge=0, le=365, description="Days from now")
    severity: SeverityLevel = Field(..., description="Severity of energy dip")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence (0-1)")
    primary_cause: str = Field(..., description="Primary reason for dip")
    secondary_causes: List[str] = Field(default_factory=list, description="Additional factors")
    recommended_action: str = Field(default="", description="Suggested adaptation")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0-1."""
        return max(0.0, min(1.0, v))


class PredictedScheduleDisruption(BaseModel):
    """Prediction of a schedule disruption event."""
    day_offset: int = Field(..., ge=0, le=365, description="Days from now")
    disruption_type: DisruptionType = Field(..., description="Type of disruption")
    severity: SeverityLevel = Field(..., description="Severity of disruption")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence (0-1)")
    affected_categories: List[str] = Field(default_factory=list, description="Constraint categories affected")
    expected_duration_hours: Optional[int] = Field(None, description="Expected duration")
    mitigation_available: bool = Field(default=False, description="Can be mitigated")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0-1."""
        return max(0.0, min(1.0, v))


class OpportunityWindow(BaseModel):
    """Prediction of a period with lower constraint pressure."""
    start_day: int = Field(..., ge=0, le=365, description="Start day from now")
    duration: int = Field(..., ge=1, le=30, description="Duration in days")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence (0-1)")
    flexibility_available: float = Field(..., ge=0.0, le=1.0, description="Available flexibility (0-1)")
    recommended_activities: List[str] = Field(default_factory=list, description="Suggested activities")
    constraint_categories_relaxed: List[str] = Field(default_factory=list, description="Which categories relax")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0-1."""
        return max(0.0, min(1.0, v))


class ForecastMetadata(BaseModel):
    """Metadata about the forecast."""
    generated_at: datetime = Field(..., description="When forecast was generated")
    expires_at: datetime = Field(..., description="When forecast expires")
    forecast_window_days: int = Field(..., ge=1, le=365, description="Forecast horizon")
    forecast_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence (0-1)")
    data_quality: str = Field(..., description="Quality indicator: HIGH/MEDIUM/LOW")
    samples_analyzed: int = Field(..., ge=0, description="History samples used")

    @field_validator("forecast_confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0-1."""
        return max(0.0, min(1.0, v))


class ForecastResult(BaseModel):
    """Complete forecast result."""
    predicted_energy_dips: List[PredictedEnergyDip] = Field(
        default_factory=list,
        description="Predicted periods of low energy"
    )
    predicted_schedule_disruptions: List[PredictedScheduleDisruption] = Field(
        default_factory=list,
        description="Predicted schedule disruptions"
    )
    opportunity_windows: List[OpportunityWindow] = Field(
        default_factory=list,
        description="Predicted periods of lower pressure"
    )
    metadata: ForecastMetadata = Field(..., description="Forecast metadata")
    summary: str = Field(default="", description="Human-readable forecast summary")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dict for state storage."""
        return {
            "predicted_energy_dips": [d.model_dump() for d in self.predicted_energy_dips],
            "predicted_schedule_disruptions": [d.model_dump() for d in self.predicted_schedule_disruptions],
            "opportunity_windows": [w.model_dump() for w in self.opportunity_windows],
            "metadata": self.metadata.model_dump(),
            "summary": self.summary,
        }


class ForecastValidationResult(BaseModel):
    """Validation result for forecast input."""
    is_valid: bool = Field(..., description="Is forecast valid?")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal issues")
    errors: List[str] = Field(default_factory=list, description="Fatal issues")
    data_quality_score: float = Field(..., ge=0.0, le=1.0, description="Input data quality (0-1)")


class ConstraintHistoryEntry(BaseModel):
    """Historical record of constraint analysis."""
    timestamp: datetime = Field(..., description="When analyzed")
    constraint_score: float = Field(..., ge=0.0, le=10.0, description="Constraint score at time")
    pressure_level: str = Field(..., description="Pressure level then")
    categories: Dict[str, Any] = Field(default_factory=dict, description="Category data")
    life_mode: str = Field(..., description="Life mode at time")


class PredictionFactors(BaseModel):
    """Input factors for prediction engine."""
    current_constraint_score: float = Field(...,description="Current score")
    pressure_level: str = Field(..., description="Current pressure level")
    life_mode: str = Field(..., description="Current life mode")
    constraint_clusters: Dict[str, Any] = Field(default_factory=dict, description="Category clusters")
    constraint_conflicts: List[str] = Field(default_factory=list, description="Active conflicts")
    recent_constraint_frequency: int = Field(..., ge=0, description="Constraint count last week")
    overload_history: int = Field(..., ge=0, description="Overload incidents last month")
    recovery_periods: int = Field(..., ge=0, description="Recovery periods in history")
    environment_stability: str = Field(..., description="Environment: stable/variable/unstable")
    schedule_regularity: str = Field(..., description="Schedule: regular/irregular")
    adaptation_capacity: float = Field(..., ge=0.0, le=1.0, description="User adaptability (0-1)")
    user_history_sample_size: int = Field(..., ge=0, description="Historical data points available")
