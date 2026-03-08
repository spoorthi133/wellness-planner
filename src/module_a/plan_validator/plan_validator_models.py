"""
Plan Validator Models

Pydantic models for plan validation against system constraints.

Module: Plan Validator (Module 9)
Part of: Constraint-First Wellness Agent (Module A - Deterministic Reasoning)

This module defines data structures for:
- Validation results and error tracking
- Validation error types and severity
- Constraint violation reporting
- Validation metrics and summaries

All models use Pydantic v2 for validation and serialization.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class ValidationErrorType(str, Enum):
    """Types of validation errors."""
    # Energy validation
    ENERGY_EXCEEDS_BUDGET = "energy_exceeds_budget"
    NEGATIVE_ENERGY_COST = "negative_energy_cost"
    INVALID_ACTIVITY_ENERGY = "invalid_activity_energy"

    # Duration validation
    INVALID_DURATION = "invalid_duration"
    ZERO_OR_NEGATIVE_DURATION = "zero_or_negative_duration"

    # Activity restriction validation
    ACTIVITY_RESTRICTED = "activity_restricted"
    ACTIVITY_TYPE_NOT_AVAILABLE = "activity_type_not_available"
    INDOOR_ONLY_VIOLATED = "indoor_only_violated"
    SILENT_REQUIRED_VIOLATED = "silent_required_violated"

    # Constraint validation
    CONSTRAINT_VIOLATED = "constraint_violated"
    CONFLICTING_ACTIVITY = "conflicting_activity"

    # Life mode validation
    ACTIVITY_INTENSITY_MISMATCH = "activity_intensity_mismatch"
    RECOVERY_MODE_INSUFFICIENT_RECOVERY = "recovery_mode_insufficient_recovery"

    # Plan structure validation
    MISSING_TIMEBLOCKS = "missing_timeblocks"
    EMPTY_PLAN = "empty_plan"
    INSUFFICIENT_ACTIVITIES = "insufficient_activities"

    # Unknown
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    """Severity levels of validation errors."""
    WARNING = "warning"  # Severity 1-3
    MODERATE = "moderate"  # Severity 4-6
    HIGH = "high"  # Severity 7-8
    CRITICAL = "critical"  # Severity 9-10


# ============================================================================
# Validation Error
# ============================================================================

class ValidationError(BaseModel):
    """A single validation error."""
    error_type: ValidationErrorType = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    activity: Optional[str] = Field(
        default=None, description="Activity involved (if applicable)"
    )
    constraint: Optional[str] = Field(
        default=None, description="Constraint involved (if applicable)"
    )
    severity: int = Field(
        default=5, ge=1, le=10, description="Severity level 1-10"
    )
    field: Optional[str] = Field(
        default=None, description="Field where error occurred"
    )
    actual_value: Optional[Any] = Field(
        default=None, description="Actual value that failed validation"
    )
    expected_value: Optional[Any] = Field(
        default=None, description="Expected/allowed value"
    )

    def severity_category(self) -> ErrorSeverity:
        """Get severity category."""
        if self.severity <= 3:
            return ErrorSeverity.WARNING
        elif self.severity <= 6:
            return ErrorSeverity.MODERATE
        elif self.severity <= 8:
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.CRITICAL


class ValidationWarning(BaseModel):
    """A non-error validation concern."""
    warning_type: str = Field(..., description="Type of warning")
    message: str = Field(..., description="Warning message")
    activity: Optional[str] = Field(default=None, description="Activity involved")
    recommendation: Optional[str] = Field(
        default=None, description="Suggested resolution"
    )


# ============================================================================
# Validation Result
# ============================================================================

class ValidationResult(BaseModel):
    """Result of validating a parsed plan."""
    candidate_id: str = Field(..., description="Candidate being validated")
    is_valid: bool = Field(..., description="Whether plan is valid")
    validation_status: str = Field(
        default="validated",
        description="Status: validated, rejected, partial, skipped",
    )

    # Errors and warnings
    validation_errors: List[ValidationError] = Field(
        default_factory=list, description="Validation errors found"
    )
    validation_warnings: List[ValidationWarning] = Field(
        default_factory=list, description="Validation warnings"
    )

    # Breakdown by check type
    energy_validation_passed: bool = Field(
        default=True, description="Energy budget check passed"
    )
    environment_validation_passed: bool = Field(
        default=True, description="Environment restrictions check passed"
    )
    constraint_validation_passed: bool = Field(
        default=True, description="User constraints check passed"
    )
    life_mode_validation_passed: bool = Field(
        default=True, description="Life mode suitability check passed"
    )
    structure_validation_passed: bool = Field(
        default=True, description="Plan structure check passed"
    )

    # Detailed metrics
    total_energy_used: int = Field(ge=0, description="Total energy in plan")
    energy_budget_available: int = Field(ge=0, description="Energy budget")
    energy_remaining_after_plan: int = Field(description="Remaining energy")
    energy_violation_percent: float = Field(
        default=0.0, description="% over budget (if any)"
    )

    activities_restricted: int = Field(default=0, description="Restricted activities")
    activities_conflicting: int = Field(default=0, description="Conflicting activities")
    activities_problematic: int = Field(default=0, description="Any issue activities")

    # Timestamps
    validated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Validation time"
    )
    validation_time_ms: int = Field(default=0, description="Time to validate")

    def error_count(self) -> int:
        """Count validation errors."""
        return len(self.validation_errors)

    def warning_count(self) -> int:
        """Count validation warnings."""
        return len(self.validation_warnings)

    def critical_error_count(self) -> int:
        """Count critical errors (severity >= 9)."""
        return sum(1 for e in self.validation_errors if e.severity >= 9)

    def high_error_count(self) -> int:
        """Count high severity errors (severity >= 7)."""
        return sum(1 for e in self.validation_errors if e.severity >= 7)

    def get_errors_by_type(self, error_type: ValidationErrorType) -> List[ValidationError]:
        """Get all errors of a specific type."""
        return [e for e in self.validation_errors if e.error_type == error_type]

    def get_critical_errors(self) -> List[ValidationError]:
        """Get all critical errors."""
        return [e for e in self.validation_errors if e.severity >= 9]

    def should_reject_plan(self) -> bool:
        """Determine if plan should be rejected based on errors."""
        # Reject if any critical errors
        if self.critical_error_count() > 0:
            return True

        # Reject if multiple high errors
        if self.high_error_count() >= 2:
            return True

        # Reject if energy massively over budget
        if self.energy_violation_percent > 20:
            return True

        return False


# ============================================================================
# Validation Summary
# ============================================================================

class ValidationSummary(BaseModel):
    """Summary of validation across multiple candidates."""
    candidates_validated: int = Field(..., description="Number validated")
    candidates_valid: int = Field(..., description="Number passing validation")
    candidates_rejected: int = Field(..., description="Number rejected")
    candidates_partial: int = Field(..., description="Number with warnings")

    total_errors: int = Field(..., description="Total errors across all")
    total_warnings: int = Field(..., description="Total warnings across all")
    critical_error_count: int = Field(..., description="Total critical errors")

    most_common_error: Optional[ValidationErrorType] = Field(
        default=None, description="Most frequently occurring error"
    )
    error_frequency: Dict[str, int] = Field(
        default_factory=dict, description="Count by error type"
    )

    validation_time_ms: int = Field(default=0, description="Total validation time")


# ============================================================================
# Execution Trace Entry
# ============================================================================

class PlanValidatorExecutionTrace(BaseModel):
    """Execution trace for plan validator node."""
    node: str = Field(default="plan_validator", description="Node name")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution time")
    user_id: str = Field(..., description="User identifier")
    candidate_id: str = Field(..., description="Candidate being validated")

    # Validation results
    is_valid: bool = Field(..., description="Plan is valid")
    validation_status: str = Field(..., description="validated/rejected/partial/skipped")
    success: bool = Field(..., description="Did validation complete successfully?")

    # Breakdown
    energy_check_passed: bool = Field(default=True, description="Energy check passed")
    environment_check_passed: bool = Field(default=True, description="Environment check passed")
    constraint_check_passed: bool = Field(default=True, description="Constraint check passed")
    life_mode_check_passed: bool = Field(default=True, description="Life mode check passed")
    structure_check_passed: bool = Field(default=True, description="Structure check passed")

    # Error metrics
    error_count: int = Field(default=0, description="Number of errors")
    critical_error_count: int = Field(default=0, description="Critical errors")
    warning_count: int = Field(default=0, description="Number of warnings")

    # Energy metrics
    total_energy_used: int = Field(default=0, description="Total energy in plan")
    energy_violation_percent: float = Field(default=0.0, description="% over budget")

    # Activity metrics
    activities_restricted: int = Field(default=0, description="Restricted activities")
    activities_conflicting: int = Field(default=0, description="Conflicting activities")

    # Performance
    validation_time_ms: int = Field(default=0, description="Time to validate")
    error_messages: List[str] = Field(
        default_factory=list, description="Top error messages"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
