"""
Life Mode Controller Models

Defines Pydantic models for life mode detection, profiles, and metadata.
Supports multiple simultaneous life modes with priority-based resolution.

Module: Life Mode Controller
Part of: Constraint-First Wellness Agent (Module A)
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class LifeModeName(str, Enum):
    """All supported life modes."""
    # Core modes
    MAINTENANCE = "maintenance"
    GROWTH = "growth"
    RECOVERY = "recovery"
    CRISIS = "crisis"
    
    # Situational modes
    EXAM_MODE = "exam_mode"
    TRAVEL_MODE = "travel_mode"
    WORK_CRUNCH_MODE = "work_crunch_mode"
    SOCIAL_WEEK_MODE = "social_week_mode"


class ActivityIntensity(str, Enum):
    """Allowed activity intensity levels."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class PlanComplexity(str, Enum):
    """Allowed plan complexity levels."""
    MINIMAL = "minimal"
    SIMPLE = "simple"
    NORMAL = "normal"
    FLEXIBLE = "flexible"
    AMBITIOUS = "ambitious"


class RecoveryPriority(str, Enum):
    """Recovery priority levels."""
    NORMAL = "normal"
    MODERATE = "moderate"
    HIGH = "high"
    MAXIMUM = "maximum"


class ModeDetectionSignal(BaseModel):
    """A signal that triggers detection of a life mode."""
    signal_name: str = Field(..., description="Name of the detected signal")
    triggered_mode: LifeModeName = Field(..., description="Life mode this signal suggests")
    signal_strength: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence of this signal (0.0-1.0)"
    )
    signal_evidence: str = Field(..., description="Explanation of why this signal was detected")
    contributing_factors: List[str] = Field(
        default_factory=list, description="What factors led to this signal"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ModeProfile(BaseModel):
    """Behavior profile for a specific life mode."""
    mode: LifeModeName = Field(..., description="Which life mode this profile applies to")
    plan_complexity: PlanComplexity = Field(..., description="Recommended plan complexity")
    activity_intensity: ActivityIntensity = Field(..., description="Recommended activity intensity")
    recovery_priority: RecoveryPriority = Field(..., description="How much to prioritize recovery")
    description: str = Field(..., description="Human-readable description of this mode")
    
    # Additional behavioral hints
    focus_areas: List[str] = Field(
        default_factory=list, description="What to focus planning on in this mode"
    )
    avoid_areas: List[str] = Field(
        default_factory=list, description="What to minimize or avoid in this mode"
    )
    energy_protection: bool = Field(
        default=False, description="Whether to protect remaining energy aggressively"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class LifeModeDetectionResult(BaseModel):
    """Results from life mode detection process."""
    candidate_modes: List[LifeModeName] = Field(
        ..., description="All modes that triggered at least one signal"
    )
    mode_signals: Dict[str, List[ModeDetectionSignal]] = Field(
        default_factory=dict, description="Signals grouped by mode name"
    )
    num_triggered_signals: int = Field(..., ge=0, description="Total number of triggered signals")
    conflicting_signals_count: int = Field(
        ..., ge=0, description="Number of conflicting signal pairs"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class LifeModeContext(BaseModel):
    """Contextual data used during life mode resolution."""
    current_mode: LifeModeName = Field(..., description="Currently active mode")
    constraint_pressure_level: str = Field(
        ..., description="Current constraint pressure: LOW, MODERATE, HIGH, CRITICAL"
    )
    overload_detected: bool = Field(..., description="Whether system overload was detected")
    energy_remaining: int = Field(..., ge=0, description="Remaining energy units")
    forecast_window_days: int = Field(..., ge=1, description="Forecast window in days")
    
    # History-based signals
    recent_recovery_periods: int = Field(
        ..., ge=0, description="Number of recent recovery periods"
    )
    recent_overload_count: int = Field(..., ge=0, description="Recent overload incidents")
    days_in_active_mode: int = Field(..., ge=0, description="Days in current mode")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class LifeModeResolution(BaseModel):
    """Final resolution after priority-based conflict resolution."""
    selected_mode: LifeModeName = Field(..., description="Final selected life mode")
    priority_rank: int = Field(..., ge=1, description="Priority rank of selected mode (1 is highest)")
    resolution_reason: str = Field(
        ..., description="Explanation of why this mode was chosen over others"
    )
    competing_modes: List[LifeModeName] = Field(
        default_factory=list, description="Other modes that were also triggered but deprioritized"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ConfidenceFactors(BaseModel):
    """Components of confidence calculation."""
    num_contributing_signals: int = Field(..., ge=0, description="How many signals contributed")
    signal_consistency: float = Field(
        ..., ge=0.0, le=1.0, description="Consistency among signals (0=conflicting, 1=aligned)"
    )
    historical_pattern_match: float = Field(
        ..., ge=0.0, le=1.0, description="How well this matches user history patterns"
    )
    baseline_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Base confidence from enabled signals"
    )
    adjustment_factor: float = Field(
        ..., ge=0.5, le=1.5, description="Adjustment based on context (0.5-1.5)"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class LifeModeSelection(BaseModel):
    """Complete life mode selection with all metadata."""
    selected_mode: LifeModeName = Field(..., description="The selected life mode")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the selection (0.0-1.0)"
    )
    confidence_factors: ConfidenceFactors = Field(..., description="Components of confidence score")
    reason: str = Field(..., description="Human-readable explanation")
    triggering_signals: List[str] = Field(
        default_factory=list, description="Names of signals that triggered this mode"
    )
    profile: ModeProfile = Field(..., description="Behavior profile for this mode")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata for tracking mode stability
    mode_stability: float = Field(
        ..., ge=0.0, le=1.0, description="How stable this mode appears (1.0 = very stable)"
    )
    expected_duration_hours: Optional[int] = Field(
        default=None, description="Estimated duration before mode might change"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ModePriorityMap(BaseModel):
    """Maps life modes to their priority for conflict resolution."""
    priority_order: List[LifeModeName] = Field(
        ..., description="Modes ordered by priority (index 0 = highest)"
    )
    priority_values: Dict[str, int] = Field(
        ..., description="Each mode mapped to its numeric priority"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class LifeModeControllerMetadata(BaseModel):
    """Metadata about the life mode controller's execution."""
    node_name: str = Field(..., description="Name of the node")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    selected_mode: LifeModeName = Field(..., description="Selected mode")
    confidence: float = Field(..., ge=0.0, le=1.0)
    signals_triggered: int = Field(..., ge=0)
    execution_time_ms: Optional[float] = Field(default=None)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
