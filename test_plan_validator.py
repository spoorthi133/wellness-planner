"""
Test Plan Validator Module

Tests for MODULE 9: Plan Validator

Tests validation of parsed plans against system constraints.

Usage:
    pytest test_plan_validator.py -v
"""

import sys
import pytest
from datetime import datetime

sys.path.insert(0, "src/module_a/plan_validator")

from plan_validator_models import (
    ValidationErrorType,
    ValidationError,
    ValidationResult,
)
from plan_validator import PlanValidator
from plan_validator_utils import (
    validate_energy,
    validate_environment,
    validate_life_mode_suitability,
    validate_plan_structure,
)


# ============================================================================
# Test Data
# ============================================================================

VALID_PLAN = {
    "plan_id": "plan_valid_001",
    "morning_activities": [
        {"activity": "stretching", "duration_minutes": 15, "energy_cost": 5},
        {"activity": "breakfast", "duration_minutes": 20, "energy_cost": 3},
    ],
    "afternoon_activities": [
        {"activity": "focused work", "duration_minutes": 120, "energy_cost": 20},
    ],
    "evening_activities": [
        {"activity": "dinner", "duration_minutes": 30, "energy_cost": 5},
    ],
    "recovery_blocks": [
        {"activity": "meditation", "duration_minutes": 20, "energy_cost": 2},
    ],
    "total_energy_allocated": 35,
    "plan_rationale": "A balanced plan",
}

ENERGY_OVER_BUDGET_PLAN = {
    "plan_id": "plan_over_budget",
    "morning_activities": [
        {"activity": "intense workout", "duration_minutes": 60, "energy_cost": 50},
    ],
    "afternoon_activities": [
        {"activity": "deep work", "duration_minutes": 180, "energy_cost": 60},
    ],
    "evening_activities": [
        {"activity": "social event", "duration_minutes": 120, "energy_cost": 30},
    ],
    "recovery_blocks": [],
    "total_energy_allocated": 140,
    "plan_rationale": "Intense day",
}

EMPTY_PLAN = {
    "plan_id": "plan_empty",
    "morning_activities": [],
    "afternoon_activities": [],
    "evening_activities": [],
    "recovery_blocks": [],
    "total_energy_allocated": 0,
}

RECOVERY_MODE_PLAN = {
    "plan_id": "plan_recovery",
    "morning_activities": [
        {"activity": "gentle stretching", "duration_minutes": 10, "energy_cost": 2},
    ],
    "afternoon_activities": [],
    "evening_activities": [
        {"activity": "light reading", "duration_minutes": 30, "energy_cost": 1},
    ],
    "recovery_blocks": [
        {"activity": "rest", "duration_minutes": 120, "energy_cost": 0},
        {"activity": "meditation", "duration_minutes": 30, "energy_cost": 1},
    ],
    "total_energy_allocated": 4,
}


# ============================================================================
# Test Energy Validation
# ============================================================================

class TestEnergyValidation:
    """Test energy validation checks."""

    def test_energy_within_budget(self):
        """Valid energy within budget."""
        is_valid, errors = validate_energy(
            total_energy_allocated=35,
            daily_budget=100,
            activities=VALID_PLAN["morning_activities"]
            + VALID_PLAN["afternoon_activities"],
        )
        assert is_valid
        assert len(errors) == 0

    def test_energy_exceeds_budget(self):
        """Energy exceeds budget."""
        is_valid, errors = validate_energy(
            total_energy_allocated=140,
            daily_budget=100,
            activities=ENERGY_OVER_BUDGET_PLAN["morning_activities"]
            + ENERGY_OVER_BUDGET_PLAN["afternoon_activities"],
        )
        assert not is_valid
        assert len(errors) > 0
        assert any(
            e.error_type == ValidationErrorType.ENERGY_EXCEEDS_BUDGET for e in errors
        )

    def test_energy_negative_cost(self):
        """Negative energy cost detected."""
        is_valid, errors = validate_energy(
            total_energy_allocated=10,
            daily_budget=100,
            activities=[{"activity": "test", "duration_minutes": 10, "energy_cost": -5}],
        )
        assert not is_valid
        assert any(e.error_type == ValidationErrorType.NEGATIVE_ENERGY_COST for e in errors)

    def test_energy_invalid_duration(self):
        """Invalid (zero/negative) duration detected."""
        is_valid, errors = validate_energy(
            total_energy_allocated=5,
            daily_budget=100,
            activities=[{"activity": "test", "duration_minutes": 0, "energy_cost": 5}],
        )
        assert not is_valid
        assert any(e.error_type == ValidationErrorType.INVALID_DURATION for e in errors)


# ============================================================================
# Test Environment Validation
# ============================================================================

class TestEnvironmentValidation:
    """Test environment validation checks."""

    def test_activity_restriction(self):
        """Restricted activity detected."""
        is_valid, errors = validate_environment(
            activities=[{"activity": "loud_workout", "duration_minutes": 30, "energy_cost": 20}],
            environment_context={"indoor_only": True, "silent_required": True},
            activity_restrictions=["loud_workout"],
            available_activity_types=[],
        )
        assert not is_valid
        assert any(e.error_type == ValidationErrorType.ACTIVITY_RESTRICTED for e in errors)

    def test_silent_required_violation(self):
        """Silent requirement violated."""
        is_valid, errors = validate_environment(
            activities=[
                {"activity": "loud exercise", "duration_minutes": 30, "energy_cost": 20}
            ],
            environment_context={"silent_required": True},
            activity_restrictions=[],
            available_activity_types=[],
        )
        assert not is_valid
        assert any(
            e.error_type == ValidationErrorType.SILENT_REQUIRED_VIOLATED for e in errors
        )

    def test_indoor_only_violation(self):
        """Indoor-only violation."""
        is_valid, errors = validate_environment(
            activities=[{"activity": "outdoor hiking", "duration_minutes": 90, "energy_cost": 30}],
            environment_context={"indoor_only": True},
            activity_restrictions=[],
            available_activity_types=[],
        )
        assert not is_valid
        assert any(e.error_type == ValidationErrorType.INDOOR_ONLY_VIOLATED for e in errors)


# ============================================================================
# Test Plan Structure Validation
# ============================================================================

class TestStructureValidation:
    """Test plan structure validation."""

    def test_valid_structure(self):
        """Valid plan structure."""
        is_valid, errors = validate_plan_structure(
            morning_activities=VALID_PLAN["morning_activities"],
            afternoon_activities=VALID_PLAN["afternoon_activities"],
            evening_activities=VALID_PLAN["evening_activities"],
        )
        assert is_valid
        assert len(errors) == 0

    def test_empty_plan(self):
        """Empty plan structure."""
        is_valid, errors = validate_plan_structure(
            morning_activities=[],
            afternoon_activities=[],
            evening_activities=[],
        )
        assert not is_valid
        assert any(e.error_type == ValidationErrorType.EMPTY_PLAN for e in errors)


# ============================================================================
# Test Life Mode Validation
# ============================================================================

class TestLifeModeValidation:
    """Test life mode suitability validation."""

    def test_recovery_mode_with_recovery_blocks(self):
        """Recovery mode with adequate recovery blocks."""
        is_valid, errors = validate_life_mode_suitability(
            activities=RECOVERY_MODE_PLAN["morning_activities"]
            + RECOVERY_MODE_PLAN["evening_activities"],
            recovery_blocks=RECOVERY_MODE_PLAN["recovery_blocks"],
            life_mode="recovery",
            total_energy=RECOVERY_MODE_PLAN["total_energy_allocated"],
            daily_budget=100,
        )
        # Should have few/no errors for recovery mode with recovery blocks
        assert len([e for e in errors if e.severity >= 9]) == 0

    def test_crisis_mode_too_many_activities(self):
        """Crisis mode with too many activities."""
        is_valid, errors = validate_life_mode_suitability(
            activities=VALID_PLAN["morning_activities"]
            + VALID_PLAN["afternoon_activities"]
            + VALID_PLAN["evening_activities"],
            recovery_blocks=[],
            life_mode="crisis",
            total_energy=35,
            daily_budget=100,
        )
        # May have warnings about complexity
        assert is_valid  # Not a critical failure, just warning


# ============================================================================
# Test Main Validator
# ============================================================================

class TestPlanValidator:
    """Test main plan validator."""

    def test_validate_valid_plan(self):
        """Validate a valid plan."""
        validator = PlanValidator()
        result = validator.validate_plan(
            parsed_plan=VALID_PLAN,
            energy_budget={"daily_budget": 100},
            environment_context={},
            constraints={},
            life_mode="maintenance",
        )

        assert result.is_valid
        assert result.validation_status == "validated"
        assert result.error_count() == 0

    def test_validate_over_budget_plan(self):
        """Validate plan that exceeds budget."""
        validator = PlanValidator()
        result = validator.validate_plan(
            parsed_plan=ENERGY_OVER_BUDGET_PLAN,
            energy_budget={"daily_budget": 100},
            environment_context={},
            constraints={},
            life_mode="maintenance",
        )

        assert not result.is_valid
        assert result.validation_status == "rejected"
        assert result.error_count() > 0
        assert result.energy_violation_percent > 0

    def test_validate_empty_plan(self):
        """Validate empty plan."""
        validator = PlanValidator()
        result = validator.validate_plan(
            parsed_plan=EMPTY_PLAN,
            energy_budget={"daily_budget": 100},
            environment_context={},
            constraints={},
        )

        assert not result.is_valid
        assert result.validation_status == "rejected"

    def test_validation_result_metadata(self):
        """Verify validation result metadata."""
        validator = PlanValidator()
        result = validator.validate_plan(
            parsed_plan=VALID_PLAN,
            energy_budget={"daily_budget": 100},
            environment_context={},
            constraints={},
        )

        assert result.candidate_id is not None
        assert result.validated_at is not None
        assert result.validation_time_ms >= 0
        assert result.total_energy_used == VALID_PLAN["total_energy_allocated"]
        assert result.energy_budget_available == 100


# ============================================================================
# Test Batch Validation
# ============================================================================

class TestBatchValidation:
    """Test batch validation."""

    def test_validate_multiple_plans(self):
        """Validate multiple plans."""
        validator = PlanValidator()
        plans = {
            "plan_1": VALID_PLAN,
            "plan_2": ENERGY_OVER_BUDGET_PLAN,
            "plan_3": EMPTY_PLAN,
        }

        results = validator.validate_batch(
            plans=plans,
            energy_budget={"daily_budget": 100},
            environment_context={},
            constraints={},
        )

        assert len(results) == 3
        assert results["plan_1"].is_valid
        assert not results["plan_2"].is_valid
        assert not results["plan_3"].is_valid


# ============================================================================
# Integration Test
# ============================================================================

class TestIntegration:
    """Integration tests."""

    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        validator = PlanValidator()

        # Validate plan
        result = validator.validate_plan(
            parsed_plan=VALID_PLAN,
            energy_budget={"daily_budget": 100},
            environment_context={"indoor_only": False, "silent_required": False},
            constraints={"constraints": []},
            life_mode="maintenance",
        )

        # Verify result
        assert result.candidate_id is not None
        assert result.is_valid
        assert result.validation_status == "validated"
        assert result.energy_validation_passed
        assert result.structure_validation_passed

        # Verify metrics
        assert result.total_energy_used == 35
        assert result.energy_remaining_after_plan == 65
        assert result.energy_violation_percent == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
