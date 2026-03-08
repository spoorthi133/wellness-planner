"""
Energy Budget Manager Models

Defines Pydantic models for energy budget calculations and tracking.
All models handle energy as a daily resource with recovery dynamics.

Module: Energy Budget Manager
Part of: Constraint-First Wellness Agent (Module A)
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class EnergySource(str, Enum):
    """Sources that contribute to or deplete user energy."""
    SLEEP = "sleep"
    REST = "rest"
    EXERCISE = "exercise"
    SOCIAL_CONNECTION = "social_connection"
    CREATIVE_WORK = "creative_work"
    LEISURE = "leisure"
    FOCUS_WORK = "focus_work"
    MEETINGS = "meetings"
    CAREGIVING = "caregiving"
    COMMUTE = "commute"


class TaskCategory(str, Enum):
    """Categories of tasks with energy costs."""
    LIGHT_MOVEMENT = "light_movement"
    FOCUS_WORK = "focus_work"
    EXERCISE = "exercise"
    DEEP_WORK = "deep_work"
    SOCIAL_ACTIVITY = "social_activity"
    CREATIVE_WORK = "creative_work"
    CARE_GIVING = "care_giving"
    ADMINISTRATIVE = "administrative"
    RECOVERY = "recovery"
    LEISURE = "leisure"


class ConstraintPressureLevel(str, Enum):
    """Qualification of constraint-induced pressure on energy."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EnergyDipSeverity(str, Enum):
    """Severity of predicted energy dips."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class EnergyBreakdown(BaseModel):
    """Detailed breakdown of how budget was calculated at each step."""
    base_budget: int = Field(..., ge=20, le=200, description="Starting budget from life mode")
    constraint_adjustment: int = Field(..., description="Units removed due to constraints")
    constraint_pressure_level: str = Field(..., description="Pressure level applied")
    forecast_adjustment: int = Field(..., ge=0, description="Units removed due to forecast dips")
    overload_adjustment: int = Field(..., ge=0, description="Units removed due to overload")
    final_budget: int = Field(..., ge=20, le=200, description="Final budget after all adjustments")
    total_adjustments: int = Field(..., ge=0, description="Sum of all adjustments")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dict for JSON serialization."""
        return {
            "base_budget": self.base_budget,
            "constraint_adjustment": self.constraint_adjustment,
            "constraint_pressure_level": self.constraint_pressure_level,
            "forecast_adjustment": self.forecast_adjustment,
            "overload_adjustment": self.overload_adjustment,
            "final_budget": self.final_budget,
            "total_adjustments": self.total_adjustments,
        }


class BaseEnergyBudget(BaseModel):
    """Base energy levels by life mode."""
    life_mode: str
    base_units: int = Field(..., ge=20, le=200, description="Base daily energy units")
    description: str

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TaskEnergyCost(BaseModel):
    """Energy cost for a specific task category."""
    task_category: TaskCategory
    base_cost: int = Field(..., ge=1, description="Base energy units required")
    recovery_required: int = Field(ge=0, description="Energy units needed to recover")
    duration_minutes: Optional[int] = None
    description: str = ""

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RecoveryProfile(BaseModel):
    """Defines how quickly user recovers energy."""
    recovery_factor: float = Field(..., ge=0.3, le=1.0, description="Recovery rate (0.3-1.0)")
    base_recovery_units_per_hour: float = Field(..., ge=0.5, description="Units recovered per hour of rest")
    sleep_quality_factor: float = Field(..., ge=0.0, le=1.0, description="Sleep quality (0-1)")
    needs_forced_rest_threshold: int = Field(..., ge=0, description="Energy level triggering forced rest")
    overload_recovery_time_hours: int = Field(..., ge=1, le=72, description="Hours to recover from overload")

    @field_validator('recovery_factor')
    @classmethod
    def validate_recovery_factor(cls, v: float) -> float:
        """Clamp recovery factor to valid range."""
        return max(0.3, min(1.0, v))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ConstraintAdjustment(BaseModel):
    """Adjustments to energy budget based on constraints."""
    pressure_level: ConstraintPressureLevel
    reduction_percentage: int = Field(..., ge=0, le=50, description="Percentage reduction")
    description: str = ""
    affected_hours: Optional[int] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ForecastAdjustment(BaseModel):
    """Adjustments based on predicted energy dips."""
    dip_severity: EnergyDipSeverity
    energy_reduction: int = Field(..., ge=0, description="Energy units to subtract")
    days_affected: int = Field(..., ge=1, le=30, description="How many days affected")
    description: str = ""

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AllocatedTask(BaseModel):
    """A task allocated to the energy budget."""
    task_id: str
    category: TaskCategory
    energy_cost: int = Field(..., ge=1)
    scheduled_for: Optional[str] = None  # Time of day or specific day
    is_flexible: bool = True
    priority: int = Field(..., ge=1, le=5, description="1=low, 5=critical")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EnergyBudgetMetrics(BaseModel):
    """Metrics tracking energy budget performance."""
    daily_budget: int = Field(..., ge=20, description="Total daily energy units")
    allocated_energy: int = Field(..., ge=0, description="Energy assigned to tasks")
    remaining_energy: int = Field(..., ge=0, description="Available energy")
    buffer_energy: int = Field(ge=0, description="Reserved for unexpected needs")
    recovery_capacity: float = Field(..., ge=0.0, le=1.0, description="Recovery rate (0-1)")
    
    tasks: List[AllocatedTask] = Field(default_factory=list, description="Allocated tasks")
    energy_dips_detected: List[Dict[str, Any]] = Field(default_factory=list, description="Predicted dips")
    warnings: List[str] = Field(default_factory=list, description="Alert messages")

    @field_validator('remaining_energy')
    @classmethod
    def remaining_must_be_non_negative(cls, v: int) -> int:
        """Ensure remaining energy is never negative."""
        return max(0, v)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EnergyBudgetState(BaseModel):
    """Complete energy budget state for storage in AgentState."""
    daily_budget: int = Field(..., ge=20, le=200, description="Total units available today")
    allocated_energy: int = Field(..., ge=0, description="Energy assigned to tasks")
    remaining_energy: int = Field(..., ge=0, description="Available unallocated energy")
    recovery_factor: float = Field(..., ge=0.3, le=1.0, description="Recovery rate multiplier")
    task_energy_costs: Dict[str, int] = Field(default_factory=dict, description="Task→energy mapping")
    
    # Extended fields
    buffer_energy: int = Field(ge=0, default=5, description="Reserved for surprises")
    estimated_recovery_per_hour: float = Field(..., ge=0.5, description="Units/hour recovery")
    predicted_energy_dips: List[Dict[str, Any]] = Field(default_factory=list, description="Forecast dips")
    overload_detected: bool = False
    constraint_pressure_applied: str = Field(default="LOW", description="Current pressure level")
    
    # NEW: Energy volatility indicator
    energy_volatility: float = Field(ge=0.0, le=1.0, default=0.0, description="Budget stability (0=stable, 1=highly volatile)")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    @field_validator('remaining_energy')
    @classmethod
    def clamp_remaining(cls, v: int) -> int:
        """Ensure remaining is never negative."""
        return max(0, v)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
