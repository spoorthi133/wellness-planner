"""
Plan Parser Models

Pydantic models for plan parsing, converting raw LLM response to structured plans.

Module: Plan Parser (Module 8)
Part of: Constraint-First Wellness Agent (Module A - Deterministic Reasoning)

This module defines data structures for:
- Parsed plan candidates
- Daily wellness plans
- Parsing error tracking
- Plan structure validation results

All models use Pydantic v2 for validation and serialization.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class ParseStatus(str, Enum):
    """Status of parsing operation."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ParsingErrorType(str, Enum):
    """Types of parsing errors encountered."""
    JSON_NOT_FOUND = "json_not_found"
    JSON_MALFORMED = "json_malformed"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_FIELD_TYPE = "invalid_field_type"
    INVALID_FIELD_VALUE = "invalid_field_value"
    MISSING_ACTIVITY_LIST = "missing_activity_list"
    INVALID_ACTIVITY_STRUCTURE = "invalid_activity_structure"
    INVALID_ENERGY_VALUE = "invalid_energy_value"
    EMPTY_PLAN = "empty_plan"
    UNKNOWN = "unknown"


# ============================================================================
# Activity Models
# ============================================================================

class ParsedActivity(BaseModel):
    """A single activity in a parsed plan."""
    activity: str = Field(..., min_length=1, description="Activity name/description")
    duration_minutes: int = Field(..., ge=1, description="Duration in minutes (must be > 0)")
    energy_cost: int = Field(..., ge=0, description="Energy cost in units (must be >= 0)")
    description: Optional[str] = Field(default=None, description="Optional activity description")

    @field_validator("activity")
    @classmethod
    def validate_activity_not_empty(cls, v):
        """Ensure activity is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Activity name cannot be empty")
        return v.strip()

    def to_timeblock(self) -> "ParsedActivityTimeblock":
        """Convert to timeblock format for plan."""
        return ParsedActivityTimeblock(
            activity=self.activity,
            duration_minutes=self.duration_minutes,
            energy_cost=self.energy_cost,
            description=self.description,
        )


class ParsedActivityTimeblock(BaseModel):
    """Activity in standardized timeblock format."""
    activity: str = Field(..., description="Activity name")
    duration_minutes: int = Field(..., ge=1, description="Duration in minutes")
    energy_cost: int = Field(..., ge=0, description="Energy units required")
    description: Optional[str] = Field(default=None, description="Activity description")
    modifications: Optional[List[str]] = Field(
        default=None, description="Applied modifications for fit"
    )


# ============================================================================
# Daily Wellness Plan
# ============================================================================

class ParsedDailyWellnessPlan(BaseModel):
    """Parsed daily wellness plan with activities."""
    plan_id: str = Field(..., description="Unique plan identifier")
    morning_activities: List[ParsedActivityTimeblock] = Field(
        default_factory=list, description="Morning activities"
    )
    afternoon_activities: List[ParsedActivityTimeblock] = Field(
        default_factory=list, description="Afternoon activities"
    )
    evening_activities: List[ParsedActivityTimeblock] = Field(
        default_factory=list, description="Evening activities"
    )
    recovery_blocks: List[ParsedActivityTimeblock] = Field(
        default_factory=list, description="Recovery/rest periods"
    )
    total_energy_allocated: int = Field(ge=0, description="Total energy allocated")
    plan_rationale: Optional[str] = Field(
        default=None, max_length=1000, description="Rationale for plan choices"
    )
    adaptability_score: float = Field(
        default=0.5, ge=0, le=1, description="Plan adaptability 0-1"
    )

    def get_all_activities(self) -> List[ParsedActivityTimeblock]:
        """Get all activities across all timeblocks."""
        return (
            self.morning_activities
            + self.afternoon_activities
            + self.evening_activities
            + self.recovery_blocks
        )

    def get_activity_count(self) -> int:
        """Count total activities."""
        return len(self.get_all_activities())

    def validate_structure(self) -> tuple[bool, List[str]]:
        """Validate plan structure. Returns (is_valid, errors)."""
        errors = []

        # Check for empty plan
        if self.get_activity_count() == 0:
            errors.append("Plan has no activities")

        # Check for at least timeblock structure
        has_timeblocks = any(
            [
                self.morning_activities,
                self.afternoon_activities,
                self.evening_activities,
            ]
        )
        if not has_timeblocks:
            errors.append("Plan must have at least one timeblock (morning/afternoon/evening)")

        # Check energy allocation is reasonable
        total_activity_energy = sum(
            act.energy_cost for act in self.get_all_activities()
        )
        if total_activity_energy != self.total_energy_allocated:
            errors.append(
                f"Activity energy sum ({total_activity_energy}) doesn't match "
                f"total_energy_allocated ({self.total_energy_allocated})"
            )

        # Check durations are positive
        for act in self.get_all_activities():
            if act.duration_minutes <= 0:
                errors.append(
                    f"Activity '{act.activity}' has invalid duration: {act.duration_minutes}"
                )

        return len(errors) == 0, errors


# ============================================================================
# Parsing Error
# ============================================================================

class ParsingError(BaseModel):
    """Error encountered during parsing."""
    error_type: ParsingErrorType = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(default=None, description="Field where error occurred")
    severity: int = Field(
        default=1, ge=1, le=10, description="Error severity 1-10 (1=warning, 10=critical)"
    )
    raw_value: Optional[str] = Field(default=None, description="Value that caused error")


# ============================================================================
# Plan Candidate (Parsed Result)
# ============================================================================

class ParsedPlanCandidate(BaseModel):
    """Result of parsing an LLM response into a structured plan."""
    candidate_id: str = Field(..., description="Unique candidate identifier")
    plan: Optional[ParsedDailyWellnessPlan] = Field(
        default=None, description="Parsed plan (None if parsing failed)"
    )
    raw_response: str = Field(..., description="Original raw LLM response text")
    parsing_status: ParseStatus = Field(
        default=ParseStatus.SUCCESS, description="Success/partial/failed status"
    )
    parsing_errors: List[ParsingError] = Field(
        default_factory=list, description="Errors encountered during parsing"
    )
    parsing_warnings: List[str] = Field(
        default_factory=list, description="Non-critical warnings"
    )
    json_extracted: Optional[str] = Field(
        default=None, description="Raw JSON text extracted from response"
    )
    extraction_method: str = Field(
        default="json_search", description="How JSON was extracted"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When parsing occurred"
    )
    parsing_time_ms: int = Field(default=0, description="Time to parse in milliseconds")

    def has_errors(self) -> bool:
        """Check if parsing had critical errors."""
        return any(err.severity >= 8 for err in self.parsing_errors)

    def has_warnings(self) -> bool:
        """Check if parsing had warnings."""
        return bool(self.parsing_warnings or any(
            err.severity < 8 for err in self.parsing_errors
        ))

    def get_error_count(self) -> int:
        """Count parsing errors."""
        return len(self.parsing_errors)

    def get_warning_count(self) -> int:
        """Count warnings."""
        return len(self.parsing_warnings)

    def is_usable(self) -> bool:
        """Check if plan is usable for validation."""
        return self.plan is not None and not self.has_errors()


# ============================================================================
# Execution Trace Entry
# ============================================================================

class PlanParserExecutionTrace(BaseModel):
    """Execution trace for plan parser node."""
    node: str = Field(default="plan_parser", description="Node name")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution time")
    user_id: str = Field(..., description="User identifier")
    candidate_id: str = Field(..., description="Candidate being parsed")

    # Parsing results
    raw_response_size_bytes: int = Field(default=0, description="Size of raw response")
    parsing_status: ParseStatus = Field(..., description="Parsing success/partial/failed")
    success: bool = Field(..., description="Did parsing succeed?")
    parsing_errors: List[str] = Field(
        default_factory=list, description="List of error messages"
    )
    parsing_warnings: List[str] = Field(
        default_factory=list, description="List of warnings"
    )
    error_count: int = Field(default=0, description="Number of errors")
    warning_count: int = Field(default=0, description="Number of warnings")

    # Plan metrics (if successful)
    json_found: bool = Field(default=False, description="Was JSON found in response?")
    plan_generated: bool = Field(default=False, description="Was plan successfully parsed?")
    activity_count: int = Field(default=0, description="Number of activities parsed")
    total_energy_allocated: int = Field(default=0, description="Total energy in plan")

    # Performance
    parsing_time_ms: int = Field(default=0, description="Time taken to parse")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
