"""
LangGraph Agent State Schema

Defines the core state object used by LangGraph nodes.
All state must be JSON serializable and support persistence.

Module: State Model & Persistence Layer
Part of: Constraint-First Wellness Agent
"""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class LifeMode(str, Enum):
    """Life modes representing user's current situation."""
    MAINTENANCE = "maintenance"
    GROWTH = "growth"
    RECOVERY = "recovery"
    CRISIS = "crisis"


class MotivationStyle(str, Enum):
    """User motivation preferences."""
    REWARD_FOCUSED = "reward_focused"
    LOSS_AVERSION = "loss_aversion"
    PROGRESS_TRACKING = "progress_tracking"
    SOCIAL_ACCOUNTABILITY = "social_accountability"


class Constraint(BaseModel):
    """Represents a user constraint."""
    id: str
    name: str
    category: str  # e.g., "time", "energy", "physical", "mental"
    description: str
    severity: int = Field(ge=1, le=10)  # 1-10 scale
    flexible: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EnergyBudget(BaseModel):
    """Represents user's energy allocation."""
    daily_total: float = Field(ge=0, le=100)
    morning: float = Field(ge=0, le=100)
    afternoon: float = Field(ge=0, le=100)
    evening: float = Field(ge=0, le=100)
    contingency: float = Field(ge=0, le=100)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    # NEW: Task-level allocation fields
    daily_budget: int = Field(ge=0, default=100)
    allocated_energy: int = Field(ge=0, default=0)
    remaining_energy: int = Field(ge=0, default=100)
    task_energy_costs: Dict[str, int] = Field(default_factory=dict)
    recovery_factor: float = Field(gt=0, le=1, default=0.8)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EnvironmentContext(BaseModel):
    """Physical and social environment context."""
    timezone: str = "UTC"
    work_hours: Dict[str, str] = Field(default_factory=lambda: {
        "start": "09:00",
        "end": "17:00"
    })
    commute_time_minutes: int = 0
    social_obligations_weekly: int = 0
    caregiving_hours_weekly: float = 0.0
    pets: int = 0
    living_situation: str = "independent"  # e.g., "independent", "family", "shared"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # NEW: Environmental limitations
    indoor_only: bool = False
    small_space: bool = False
    silent_required: bool = False
    shared_room: bool = False
    equipment_available: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Forecast(BaseModel):
    """Forecast data for future planning."""
    period: str = "week"  # "week", "month", "quarter"
    predicted_energy_level: float = Field(ge=0, le=100)
    expected_disruptions: List[str] = Field(default_factory=list)
    opportunity_windows: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1, default=0.5)
    # NEW: Fields for Constraint Forecast Engine
    upcoming_constraints: List[str] = Field(default_factory=list)
    predicted_energy_dips: List[str] = Field(default_factory=list)
    predicted_schedule_disruptions: List[str] = Field(default_factory=list)
    forecast_confidence: float = Field(ge=0, le=1, default=0.5)
    forecast_window_days: int = Field(gt=0, default=7)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow())

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Plan(BaseModel):
    """Generated wellness plan."""
    id: str
    user_id: str
    version: int = 1
    period: str = "week"
    constraints_addressed: List[str] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    micro_wins: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Insight(BaseModel):
    """Generated insights about user patterns."""
    id: str
    category: str  # e.g., "pattern", "opportunity", "risk", "success"
    title: str
    description: str
    evidence: List[str] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserHistory(BaseModel):
    """User interaction history."""
    total_plans_generated: int = 0
    plans_completed: int = 0
    micro_wins_achieved: int = 0
    days_active: int = 0
    last_interaction: datetime = Field(default_factory=datetime.utcnow)
    feedback_provided: int = 0
    average_plan_completion: float = Field(ge=0, le=1, default=0.5)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ConstraintAnalysisResult(BaseModel):
    """Results from constraint analysis."""
    constraint_summary: Dict[str, Any] = Field(default_factory=dict)
    constraint_score: float = Field(ge=0, le=10, default=0.0)
    constraint_clusters: Dict[str, List[str]] = Field(default_factory=dict)
    constraint_conflicts: List[str] = Field(default_factory=list)
    constraint_pressure_level: str = "LOW"  # LOW, MODERATE, HIGH, CRITICAL
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    constraint_count: int = 0
    constraint_categories_present: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SystemFlags(BaseModel):
    """System-level flags for control flow."""
    is_onboarded: bool = False
    requires_replan: bool = False
    emergency_mode: bool = False
    data_sync_pending: bool = False
    last_sync: datetime = Field(default_factory=datetime.utcnow)
    # NEW: Orchestration control signals
    reentry_required: bool = False
    overload_detected: bool = False
    simulation_mode: bool = False
    plan_locked: bool = False
    forecast_stale: bool = False
    # NEW: Constraint analysis flags
    constraint_pressure_level: str = "LOW"  # LOW, MODERATE, HIGH, CRITICAL

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentState(BaseModel):
    """
    Core LangGraph Agent State Schema
    
    This is the central state object that all nodes read and write.
    All fields must be JSON serializable.
    """
    # Identity
    user_id: str
    session_id: str = Field(default_factory=lambda: "")
    
    # Core planning data
    constraints: List[Constraint] = Field(default_factory=list)
    constraint_analysis: ConstraintAnalysisResult = Field(default_factory=ConstraintAnalysisResult)
    forecast_data: Forecast = Field(default_factory=Forecast)
    energy_budget: EnergyBudget = Field(
        default_factory=lambda: EnergyBudget(
            daily_total=100, morning=30, afternoon=40, evening=20, contingency=10
        )
    )
    environment_context: EnvironmentContext = Field(default_factory=EnvironmentContext)
    
    # User profile
    life_mode: LifeMode = LifeMode.MAINTENANCE
    motivation_style: MotivationStyle = MotivationStyle.PROGRESS_TRACKING
    user_history: UserHistory = Field(default_factory=UserHistory)
    
    # Generated outputs - RENAMED: current_plan -> plan
    plan: Optional[Plan] = None
    recent_insights: List[Insight] = Field(default_factory=list)
    
    # System
    system_flags: SystemFlags = Field(default_factory=SystemFlags)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    # NEW: State versioning for concurrency control
    state_version: int = 0
    # NEW: Graph debug metadata
    last_node_executed: Optional[str] = None
    execution_trace: List[str] = Field(default_factory=list)

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        """Validate user_id is not empty."""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v

    def dict_for_langgraph(self) -> Dict[str, Any]:
        """
        Convert state to dict compatible with LangGraph.
        Ensures datetime objects are serialized.
        """
        return self.dict(exclude_unset=False, by_alias=False)

    def json_serializable(self) -> str:
        """
        Get JSON serializable version of state.
        """
        return self.json(exclude_unset=False)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# LangGraph TypedDict for type hints in graph definitions
class AgentStateDict(TypedDict, total=False):
    """TypedDict version for LangGraph node signatures."""
    user_id: str
    session_id: str
    constraints: List[Dict[str, Any]]
    constraint_analysis: Dict[str, Any]
    forecast_data: Dict[str, Any]
    energy_budget: Dict[str, Any]
    environment_context: Dict[str, Any]
    life_mode: str
    motivation_style: str
    plan: Optional[Dict[str, Any]]  # RENAMED: current_plan -> plan
    recent_insights: List[Dict[str, Any]]
    user_history: Dict[str, Any]
    system_flags: Dict[str, Any]
    last_updated: str
    version: int
    state_version: int  # NEW: Concurrency control
    last_node_executed: Optional[str]  # NEW: Debug metadata
    execution_trace: List[str]  # NEW: Debug metadata
