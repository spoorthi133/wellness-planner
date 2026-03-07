"""
Constraint Engine Models

Defines data models for constraint analysis and processing.
Provides typed structures for constraint operations.

Module: Constraint Analysis & Processing
Part of: Constraint-First Wellness Agent
"""

from typing import Dict, List, Optional, Set, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class ConstraintCategory(str, Enum):
    """Standard constraint categories."""
    TIME = "time"
    ENERGY = "energy"
    ENVIRONMENT = "environment"
    SOCIAL = "social"
    MENTAL = "mental"
    PHYSICAL = "physical"
    LOGISTICAL = "logistical"


class ConstraintSeverityLevel(str, Enum):
    """Qualitative pressure levels based on constraint score."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NormalizedConstraint(BaseModel):
    """Internal normalized constraint representation."""
    id: str
    name: str
    category: ConstraintCategory
    description: str
    severity: int = Field(ge=1, le=10)
    flexible: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    original_severity: int = Field(ge=1, le=10)  # Track original for audit
    adjustment_factor: float = Field(ge=0.5, le=1.5, default=1.0)  # Applied adjustments
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('severity')
    @classmethod
    def clamp_severity(cls, v):
        """Ensure severity is within valid range."""
        return max(1, min(10, v))

    def __hash__(self):
        """Make constraint hashable for set operations."""
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, NormalizedConstraint):
            return self.id == other.id
        return False


class ConstraintCluster(BaseModel):
    """Represents a cluster of related constraints."""
    cluster_id: str
    cluster_name: str
    category: ConstraintCategory
    constraints: List[str] = Field(default_factory=list)  # IDs of grouped constraints
    description: str = ""
    severity_average: float = Field(ge=0, le=10, default=5.0)
    flexibility_index: float = Field(ge=0, le=1, default=0.5)  # 0=rigid, 1=flexible
    interaction_factor: float = Field(ge=1.0, le=2.0, default=1.0)  # Multiplier for combined effect


class ConstraintConflict(BaseModel):
    """Represents an incompatibility between constraints."""
    conflict_id: str
    constraint_ids: List[str] = Field(min_items=2, max_items=2)  # Pair of conflicting constraints
    conflict_type: str  # e.g., "incompatible_time", "energy_drain", "environment_mismatch"
    severity: int = Field(ge=1, le=10)
    description: str
    mitigation_strategy: Optional[str] = None
    confidence: float = Field(ge=0, le=1, default=0.7)


class ConstraintScoringMetrics(BaseModel):
    """Metrics used in constraint scoring."""
    base_severity_score: float = Field(ge=0, le=10)
    life_mode_multiplier: float = Field(ge=0.5, le=2.0)
    recent_overload_factor: float = Field(ge=0, le=1, default=0.0)
    constraint_count_factor: float = Field(ge=0, le=0.5, default=0.0)
    conflict_penalty: float = Field(ge=0, le=2.0, default=0.0)
    final_score: float = Field(ge=0, le=10)
    confidence: float = Field(ge=0, le=1)


class ConstraintAnalysisContext(BaseModel):
    """Context data used during constraint analysis."""
    user_id: str
    session_id: str
    life_mode: str
    recent_plans_count: int = 0
    days_since_last_analysis: int = 0
    has_emergency_flag: bool = False
    environment_is_restrictive: bool = False
    user_adaptive_capacity: float = Field(ge=0, le=1, default=0.5)  # How well user adapts


class ConstraintAnalysisResult(BaseModel):
    """Complete analysis result from constraint processing."""
    constraint_summary: Dict[str, Any] = Field(default_factory=dict)
    constraint_score: float = Field(ge=0, le=10)
    constraint_clusters: Dict[str, List[str]] = Field(default_factory=dict)
    constraint_conflicts: List[str] = Field(default_factory=list)
    constraint_pressure_level: ConstraintSeverityLevel = ConstraintSeverityLevel.LOW
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    constraint_count: int = 0
    constraint_categories_present: List[str] = Field(default_factory=list)
    # Extended fields
    normalized_constraints: List[Dict[str, Any]] = Field(default_factory=list)
    scoring_metrics: Optional[ConstraintScoringMetrics] = None
    cluster_details: List[Dict[str, Any]] = Field(default_factory=list)
    conflict_details: List[Dict[str, Any]] = Field(default_factory=list)
    flexibility_score: float = Field(ge=0, le=1)
    adaptability_rating: str = "moderate"


class ConstraintValidationResult(BaseModel):
    """Result of constraint validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    duplicate_ids: List[str] = Field(default_factory=list)
    missing_categories: List[str] = Field(default_factory=list)
    invalid_severities: List[str] = Field(default_factory=list)
