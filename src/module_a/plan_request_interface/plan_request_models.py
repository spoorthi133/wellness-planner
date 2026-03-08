"""
Plan Request Interface Models

Pydantic models for LLM planning request construction and response handling.
Part of Module A (Orchestration) - Constraint-First Wellness Agent.

This module defines the data structures for:
- Planning context aggregation
- Compressed context summary
- LLM prompt structure
- Plan candidate responses
- Request/response tracking

All models use Pydantic v2 for validation and serialization.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class PlanningApproach(str, Enum):
    """Approach for plan generation based on context."""
    SIMPLE = "simple"
    STANDARD = "standard"
    INTENSIVE = "intensive"
    RECOVERY = "recovery"


class ActivityTimeblock(str, Enum):
    """Time blocks in daily wellness plan."""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    RECOVERY_BLOCK = "recovery_block"


class PlanStatus(str, Enum):
    """Status of a plan candidate."""
    PENDING = "pending"
    GENERATED = "generated"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ACTIVE = "active"


class LLMProvider(str, Enum):
    """LLM provider options."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    CLAUDE = "claude"
    LOCAL = "local"


# ============================================================================
# Planning Context Models
# ============================================================================

class EnergyContextSnapshot(BaseModel):
    """Energy budget information for planning."""
    daily_budget: int = Field(..., description="Total daily energy budget in units")
    remaining_energy: int = Field(..., description="Currently available energy")
    budget_allocation: Optional[Dict[str, int]] = Field(
        default=None, 
        description="Allocated energy by category"
    )
    energy_volatility: Optional[float] = Field(
        default=None,
        description="Energy stability measure (0.0-1.0)"
    )
    constraint_impact: Optional[int] = Field(
        default=None,
        description="Units lost to constraint pressure"
    )

    @field_validator('daily_budget', 'remaining_energy')
    @classmethod
    def validate_budget_positive(cls, v):
        if v is None or v < 0:
            raise ValueError("Budget must be non-negative")
        return v

    @field_validator('remaining_energy')
    @classmethod
    def validate_remaining_le_daily(cls, v, info):
        """Remaining energy should not exceed daily budget."""
        if 'daily_budget' in info.data and v > info.data['daily_budget']:
            return info.data['daily_budget']
        return v


class ConstraintContextSnapshot(BaseModel):
    """Constraint information for planning."""
    pressure_level: str = Field(..., description="LOW, MODERATE, HIGH, CRITICAL")
    constraint_score: float = Field(..., description="Numeric constraint score 0-10")
    active_constraints: List[str] = Field(
        default_factory=list,
        description="List of active constraint names"
    )
    constraint_count: int = Field(default=0, description="Number of active constraints")
    dominant_constraint: Optional[str] = Field(
        default=None,
        description="Primary limiting constraint"
    )

    @field_validator('constraint_score')
    @classmethod
    def validate_score(cls, v):
        if not (0 <= v <= 10):
            raise ValueError("Constraint score must be 0-10")
        return v


class EnvironmentContextSnapshot(BaseModel):
    """Environment information for planning."""
    environment_complexity: int = Field(..., description="Environment complexity 0-10")
    activity_restrictions: List[str] = Field(
        default_factory=list,
        description="Blocked activities"
    )
    activity_modifiers: Dict[str, str] = Field(
        default_factory=dict,
        description="Activity adaptations"
    )
    available_activity_types: List[str] = Field(
        default_factory=list,
        description="Available activity categories"
    )
    environment_stability: float = Field(
        default=1.0,
        description="Environment stability measure 0-1"
    )

    @field_validator('environment_complexity')
    @classmethod
    def validate_complexity(cls, v):
        if not (0 <= v <= 10):
            raise ValueError("Complexity must be 0-10")
        return v


class ForecastContextSnapshot(BaseModel):
    """Forecast information for planning."""
    predicted_energy_dips: List[str] = Field(
        default_factory=list,
        description="Predicted energy dip events"
    )
    disruption_risk: float = Field(
        default=0.0,
        description="Risk of disruption 0-1"
    )
    recovery_opportunity: Optional[str] = Field(
        default=None,
        description="Identified recovery opportunity"
    )
    forecast_confidence: float = Field(
        default=1.0,
        description="Confidence in forecast 0-1"
    )

    @field_validator('disruption_risk', 'forecast_confidence')
    @classmethod
    def validate_range(cls, v):
        if not (0 <= v <= 1):
            raise ValueError("Value must be 0-1")
        return v


class LifemodeContextSnapshot(BaseModel):
    """Life mode information for planning."""
    life_mode: str = Field(..., description="maintenance, growth, recovery, crisis")
    mode_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="Life mode characteristics"
    )
    mode_adjustments: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context-specific adjustments"
    )
    planning_approach: PlanningApproach = Field(
        default=PlanningApproach.STANDARD,
        description="Recommended planning approach"
    )


# ============================================================================
# Aggregated Context
# ============================================================================

class PlanningContext(BaseModel):
    """Complete planning context from all upstream modules."""
    user_id: str = Field(..., description="User identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Context creation time")
    
    # Aggregated signals from modules
    energy: EnergyContextSnapshot = Field(..., description="Energy budget info")
    constraints: ConstraintContextSnapshot = Field(..., description="Constraint info")
    environment: EnvironmentContextSnapshot = Field(..., description="Environment info")
    forecast: ForecastContextSnapshot = Field(..., description="Forecast info")
    lifemode: LifemodeContextSnapshot = Field(..., description="Life mode info")
    
    # Metadata
    planning_precision: float = Field(
        default=0.5,
        description="Precision level for plan generation 0-1"
    )
    additional_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional user-provided context"
    )


# ============================================================================
# Compressed Context
# ============================================================================

class CompressedContextSummary(BaseModel):
    """Compressed representation of planning context."""
    summary_text: str = Field(..., description="Compressed context as readable text")
    energy_summary: str = Field(..., description="Energy budget summary")
    constraint_summary: str = Field(..., description="Constraint summary")
    environment_summary: str = Field(..., description="Environment summary")
    forecast_summary: str = Field(..., description="Forecast summary")
    lifemode_summary: str = Field(..., description="Life mode summary")
    
    # For reference
    original_context_size: int = Field(default=0, description="Original context size in bytes")
    compressed_size: int = Field(default=0, description="Compressed size in bytes")
    compression_ratio: float = Field(default=0.0, description="Compression ratio")


# ============================================================================
# LLM Prompt
# ============================================================================

class PlanningPrompt(BaseModel):
    """Structured prompt for LLM plan generation."""
    system_prompt: str = Field(..., description="System role/instructions")
    user_prompt: str = Field(..., description="User context and task")
    context_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data for reference"
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Hard constraints for plan"
    )
    preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="User preferences"
    )
    output_format: str = Field(
        default="structured",
        description="Expected output format"
    )


# ============================================================================
# Plan Candidates
# ============================================================================

class PlanTimeblock(BaseModel):
    """Activity within a timeblock."""
    activity: str = Field(..., description="Activity name")
    duration_minutes: int = Field(..., description="Duration in minutes")
    energy_cost: int = Field(..., description="Energy units required")
    description: Optional[str] = Field(default=None, description="Activity description")
    modifications: Optional[List[str]] = Field(default=None, description="Applied modifications")


class DailyWellnessPlan(BaseModel):
    """Generated wellness plan."""
    plan_id: str = Field(..., description="Unique plan identifier")
    morning_activities: List[PlanTimeblock] = Field(
        default_factory=list,
        description="Morning timeblock activities"
    )
    afternoon_activities: List[PlanTimeblock] = Field(
        default_factory=list,
        description="Afternoon timeblock activities"
    )
    evening_activities: List[PlanTimeblock] = Field(
        default_factory=list,
        description="Evening timeblock activities"
    )
    recovery_blocks: List[PlanTimeblock] = Field(
        default_factory=list,
        description="Recovery/rest blocks"
    )
    total_energy_allocated: int = Field(default=0, description="Total energy allocated")
    plan_rationale: Optional[str] = Field(default=None, description="Why this plan was chosen")
    adaptability_score: float = Field(default=0.5, description="How adaptable is plan 0-1")


class PlanCandidate(BaseModel):
    """Plan candidate from LLM."""
    candidate_id: str = Field(..., description="Unique candidate identifier")
    source: str = Field(default="llm", description="Source of plan (llm, fallback, user)")
    plan: Optional[DailyWellnessPlan] = Field(default=None, description="The actual plan")
    raw_response: str = Field(..., description="Raw LLM response text")
    status: PlanStatus = Field(default=PlanStatus.GENERATED, description="Plan status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    generated_at: Optional[datetime] = Field(default=None, description="Generation time")
    validated_at: Optional[datetime] = Field(default=None, description="Validation time")
    
    # Metadata
    generation_time_ms: int = Field(default=0, description="Generation time in milliseconds")
    llm_model: Optional[str] = Field(default=None, description="LLM model used")
    confidence_score: float = Field(default=0.5, description="LLM confidence 0-1")
    validation_errors: List[str] = Field(default_factory=list, description="Any validation errors")


# ============================================================================
# LLM Request/Response
# ============================================================================

class LLMRequest(BaseModel):
    """Request to LLM."""
    user_id: str = Field(..., description="User identifier")
    prompt: PlanningPrompt = Field(..., description="The prompt")
    model: str = Field(default="mistral", description="LLM model name")
    temperature: float = Field(default=0.7, description="Generation temperature 0-1")
    max_tokens: int = Field(default=2000, description="Max response tokens")
    timeout_seconds: int = Field(default=30, description="Request timeout")
    fallback_on_error: bool = Field(default=True, description="Use fallback if LLM fails")

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not (0 <= v <= 1):
            raise ValueError("Temperature must be 0-1")
        return v


class LLMResponse(BaseModel):
    """Response from LLM."""
    request_id: str = Field(..., description="Request identifier")
    model: str = Field(..., description="Model used")
    response_text: str = Field(..., description="Full response text")
    finish_reason: str = Field(default="stop", description="Why generation stopped")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    generation_time_ms: int = Field(default=0, description="Generation time")
    is_fallback: bool = Field(default=False, description="Is this a fallback response?")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# ============================================================================
# Execution Trace Entry
# ============================================================================

class PlanRequestExecutionTrace(BaseModel):
    """Execution trace for plan request node."""
    node: str = Field(default="plan_request_interface", description="Node name")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution time")
    user_id: str = Field(..., description="User identifier")
    
    # Context info
    life_mode: str = Field(..., description="Life mode used")
    energy_budget: int = Field(..., description="Energy budget used")
    constraint_pressure: str = Field(..., description="Constraint pressure level")
    environment_complexity: int = Field(..., description="Environment complexity")
    
    # Request info
    planning_approach: str = Field(..., description="Approach taken")
    prompt_size_bytes: int = Field(default=0, description="Prompt size")
    compression_ratio: float = Field(default=0.0, description="Compression achieved")
    
    # Response info
    llm_model: str = Field(default="", description="LLM model used")
    generation_time_ms: int = Field(default=0, description="Generation time")
    is_fallback: bool = Field(default=False, description="Used fallback?")
    candidate_generated: bool = Field(default=False, description="Plan candidate created?")
    
    # Status
    success: bool = Field(default=True, description="Did request succeed?")
    error_message: Optional[str] = Field(default=None, description="Error if any")
