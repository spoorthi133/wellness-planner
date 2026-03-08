"""
Environment Adapter Models

Defines Pydantic models for environment context and adaptation.
Handles physical environment constraints and restrictions.

Module: Environment Adapter
Part of: Constraint-First Wellness Agent (Module A)
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class EnvironmentType(str, Enum):
    """Types of living environments."""
    INDEPENDENT = "independent"
    SHARED_APARTMENT = "shared_apartment"
    FAMILY_HOME = "family_home"
    SINGLE_ROOM = "single_room"
    STUDIO = "studio"
    DORM = "dorm"
    OPEN_OFFICE = "open_office"
    HOME_OFFICE = "home_office"


class ActivityType(str, Enum):
    """Types of activities that may be restricted."""
    EXERCISE = "exercise"
    MEDITATION = "meditation"
    FOCUS_WORK = "focus_work"
    SOCIAL = "social"
    MOVEMENT = "movement"
    STRETCHING = "stretching"
    DEEP_WORK = "deep_work"
    CREATIVE = "creative"
    OUTDOOR = "outdoor"
    LOUD_ACTIVITY = "loud_activity"


class EnvironmentRestriction(str, Enum):
    """Types of environment restrictions."""
    INDOOR_ONLY = "indoor_only"
    SMALL_SPACE = "small_space"
    SHARED_ROOM = "shared_room"
    SILENT_REQUIRED = "silent_required"
    LIMITED_EQUIPMENT = "limited_equipment"
    NO_PRIVACY = "no_privacy"
    CLIMATE_CONTROLLED = "climate_controlled"
    NOISE_SENSITIVE = "noise_sensitive"


class ActivityRestrictionReason(BaseModel):
    """Why an activity is restricted."""
    activity: str = Field(..., description="Activity name")
    reason: str = Field(..., description="Why it's restricted")
    restriction_type: str = Field(..., description="Environment restriction causing it")
    alternative: Optional[str] = None
    severity: int = Field(..., ge=1, le=10, description="Restriction severity (1=light, 10=impossible)")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ActivityModifier(BaseModel):
    """How to modify an activity to fit environment."""
    original_activity: str = Field(..., description="Original activity type")
    modified_activity: str = Field(..., description="Modified version")
    modification_rationale: str = Field(..., description="Why this modification")
    effectiveness_multiplier: float = Field(
        ..., ge=0.3, le=1.0, description="Effectiveness vs original (0.3-1.0)"
    )
    energy_cost_multiplier: float = Field(
        ..., ge=0.5, le=2.0, description="Energy cost vs original (0.5-2.0)"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EnvironmentComplexityFactors(BaseModel):
    """Factors contributing to environment complexity."""
    indoor_only_penalty: int = Field(ge=0, le=10)
    small_space_penalty: int = Field(ge=0, le=10)
    shared_room_penalty: int = Field(ge=0, le=10)
    silent_required_penalty: int = Field(ge=0, le=10)
    equipment_limitation_penalty: int = Field(ge=0, le=10)
    privacy_limitation_penalty: int = Field(ge=0, le=10)

    def total_penalty(self) -> int:
        """Calculate total penalty from all factors."""
        return min(
            10,
            max(
                self.indoor_only_penalty,
                self.small_space_penalty,
                self.shared_room_penalty,
                self.silent_required_penalty,
                self.equipment_limitation_penalty,
                self.privacy_limitation_penalty,
            ),
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EnvironmentAdaptationSummary(BaseModel):
    """Complete environment adaptation summary."""
    original_restrictions: List[str] = Field(default_factory=list, description="Detected restrictions")
    active_restrictions: List[str] = Field(default_factory=list, description="Effective restrictions")
    activity_restrictions: List[str] = Field(
        default_factory=list, description="Activities that cannot be performed"
    )
    activity_modifiers: Dict[str, str] = Field(
        default_factory=dict, description="How to modify activities"
    )
    environment_complexity: int = Field(
        ge=0, le=10, default=0, description="Environment complexity score"
    )
    adaptation_required: bool = Field(default=False, description="Whether adaptation needed")
    environment_type: Optional[str] = None
    equipment_available: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(
        default_factory=list, description="Adaptation recommendations"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EnvironmentContextExtended(BaseModel):
    """Extended environment context with derived fields."""
    # Original fields (from agent_state)
    timezone: str = "UTC"
    work_hours: Dict[str, str] = Field(default_factory=lambda: {"start": "09:00", "end": "17:00"})
    commute_time_minutes: int = 0
    social_obligations_weekly: int = 0
    caregiving_hours_weekly: float = 0.0
    pets: int = 0
    living_situation: str = "independent"

    # Environment restrictions
    indoor_only: bool = False
    small_space: bool = False
    silent_required: bool = False
    shared_room: bool = False
    equipment_available: List[str] = Field(default_factory=list)

    # Derived fields (populated by Environment Adapter)
    activity_restrictions: List[str] = Field(default_factory=list)
    activity_modifiers: Dict[str, str] = Field(default_factory=dict)
    environment_complexity: int = Field(ge=0, le=10, default=0)
    available_activity_types: List[str] = Field(
        default_factory=list, 
        description="Activity types that CAN be performed in this environment (e.g., 'light_movement', 'focus_work')"
    )
    environment_stability_score: float = Field(
        ge=0, le=1, default=0.5,
        description="Environment stability (0.0=highly dynamic, 1.0=stable). Affects plan structure and flexibility."
    )
    adaptation_summary: Optional[EnvironmentAdaptationSummary] = None
    last_adapted_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
