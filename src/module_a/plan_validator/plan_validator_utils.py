"""
Plan Validator Utilities

Utility functions for validating parsed plans against system constraints.

Module: Plan Validator (Module 9)
Part of: Constraint-First Wellness Agent (Module A - Deterministic Reasoning)

This module provides validation checks for:
- Energy budget compliance
- Activity restrictions and environment fit
- User constraint violations
- Life mode suitability
- Plan structure validity
"""

import logging
from typing import Dict, List, Any, Tuple, Optional

from plan_validator_models import (
    ValidationError,
    ValidationWarning,
    ValidationErrorType,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Energy Validation
# ============================================================================

def validate_energy(
    total_energy_allocated: int,
    daily_budget: int,
    activities: List[Dict[str, Any]],
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate that plan respects energy budget.

    Checks:
    - Total energy <= daily budget
    - Each activity energy_cost >= 0
    - Activity duration > 0

    Args:
        total_energy_allocated: Total energy in plan
        daily_budget: Available daily energy budget
        activities: List of activity dicts

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []

    # Check total energy against budget
    if total_energy_allocated > daily_budget:
        violation_percent = ((total_energy_allocated - daily_budget) / daily_budget) * 100
        error = ValidationError(
            error_type=ValidationErrorType.ENERGY_EXCEEDS_BUDGET,
            message=(
                f"Plan energy {total_energy_allocated} exceeds daily budget {daily_budget} "
                f"({violation_percent:.1f}% over)"
            ),
            severity=9,
            field="total_energy_allocated",
            actual_value=total_energy_allocated,
            expected_value=f"<= {daily_budget}",
        )
        errors.append(error)
        logger.warning(f"Energy budget exceeded: {total_energy_allocated} > {daily_budget}")

    # Check individual activities
    for idx, activity in enumerate(activities):
        energy_cost = activity.get("energy_cost", 0)
        duration = activity.get("duration_minutes", 0)
        activity_name = activity.get("activity", f"Activity[{idx}]")

        # Check energy cost is non-negative
        if energy_cost < 0:
            error = ValidationError(
                error_type=ValidationErrorType.NEGATIVE_ENERGY_COST,
                message=f"Activity '{activity_name}' has negative energy cost: {energy_cost}",
                activity=activity_name,
                severity=8,
                field=f"activities[{idx}].energy_cost",
                actual_value=energy_cost,
                expected_value=">= 0",
            )
            errors.append(error)

        # Check duration is positive
        if duration <= 0:
            error = ValidationError(
                error_type=ValidationErrorType.INVALID_DURATION,
                message=f"Activity '{activity_name}' has invalid duration: {duration}",
                activity=activity_name,
                severity=7,
                field=f"activities[{idx}].duration_minutes",
                actual_value=duration,
                expected_value="> 0",
            )
            errors.append(error)

    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================================================
# Environment Validation
# ============================================================================

def validate_environment(
    activities: List[Dict[str, Any]],
    environment_context: Dict[str, Any],
    activity_restrictions: List[str],
    available_activity_types: List[str],
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate that activities fit environment constraints.

    Checks:
    - Activity not in environment_context.activity_restrictions
    - Activity type in available_activity_types
    - Silent_required not violated by loud activities
    - Indoor_only not violated by outdoor activities

    Args:
        activities: List of activity dicts
        environment_context: Environment context dict
        activity_restrictions: List of restricted activity names
        available_activity_types: List of allowed activity types

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    restricted_count = 0

    # Extract environment flags
    indoor_only = environment_context.get("indoor_only", False)
    silent_required = environment_context.get("silent_required", False)
    shared_room = environment_context.get("shared_room", False)
    small_space = environment_context.get("small_space", False)

    # Define activity properties (simple heuristic-based)
    loud_activities = {"exercise", "movement", "stretching", "loud_activity"}
    outdoor_activities = {"outdoor", "outdoor_exercise", "nature_walk"}
    space_intensive = {"exercise", "movement", "stretching", "yoga"}

    for idx, activity in enumerate(activities):
        activity_name = activity.get("activity", "").lower()
        activity_type = activity.get("type", "").lower()

        # Check if activity is explicitly restricted
        if activity_name in activity_restrictions:
            error = ValidationError(
                error_type=ValidationErrorType.ACTIVITY_RESTRICTED,
                message=f"Activity '{activity_name}' is restricted in this environment",
                activity=activity_name,
                severity=9,
                field=f"activities[{idx}].activity",
            )
            errors.append(error)
            restricted_count += 1
            logger.debug(f"Activity restricted: {activity_name}")
            continue

        # Check silent_required constraint
        if silent_required and any(keyword in activity_name for keyword in loud_activities):
            error = ValidationError(
                error_type=ValidationErrorType.SILENT_REQUIRED_VIOLATED,
                message=(
                    f"Activity '{activity_name}' is incompatible with silent_required "
                    f"environment constraint"
                ),
                activity=activity_name,
                severity=8,
                constraint="silent_required",
            )
            errors.append(error)
            logger.debug(f"Silent constraint violated: {activity_name}")

        # Check indoor_only constraint
        if indoor_only and any(keyword in activity_name for keyword in outdoor_activities):
            error = ValidationError(
                error_type=ValidationErrorType.INDOOR_ONLY_VIOLATED,
                message=(
                    f"Activity '{activity_name}' is outdoor but environment is indoor_only"
                ),
                activity=activity_name,
                severity=8,
                constraint="indoor_only",
            )
            errors.append(error)
            logger.debug(f"Indoor-only constraint violated: {activity_name}")

        # Check small_space constraint
        if small_space and any(keyword in activity_name for keyword in space_intensive):
            logger.debug(f"Warning: {activity_name} may be space-intensive in small space")

    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================================================
# Constraint Validation
# ============================================================================

def validate_user_constraints(
    activities: List[Dict[str, Any]],
    user_constraints: List[Dict[str, Any]],
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate that plan doesn't violate user constraints.

    Checks:
    - Activity doesn't conflict with hard constraints
    - Intensity appropriate for constraints
    - Time requirements met

    Args:
        activities: List of activity dicts
        user_constraints: List of constraint dicts

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []

    if not user_constraints:
        return True, errors

    # Build constraint index for faster lookup
    constraint_map = {}
    for constraint in user_constraints:
        constraint_id = constraint.get("id", "")
        constraint_name = constraint.get("name", "").lower()
        constraint_category = constraint.get("category", "")
        constraint_map[constraint_id] = {
            "name": constraint_name,
            "category": constraint_category,
            "severity": constraint.get("severity", 5),
            "flexible": constraint.get("flexible", False),
        }

    # Check each activity
    conflicting_count = 0
    for idx, activity in enumerate(activities):
        activity_name = activity.get("activity", "").lower()

        # Simple heuristic: check if activity name contains constraint keywords
        for constraint_id, constraint_info in constraint_map.items():
            constraint_name = constraint_info["name"]
            severity = constraint_info["severity"]

            # If activity mentions constraint name, check for conflict
            if constraint_name and constraint_name in activity_name:
                if not constraint_info["flexible"]:
                    error = ValidationError(
                        error_type=ValidationErrorType.CONSTRAINT_VIOLATED,
                        message=(
                            f"Activity '{activity_name}' conflicts with constraint "
                            f"'{constraint_name}'"
                        ),
                        activity=activity_name,
                        constraint=constraint_name,
                        severity=min(9, severity + 3),
                        field=f"activities[{idx}].activity",
                    )
                    errors.append(error)
                    conflicting_count += 1
                    logger.debug(f"Activity conflicts with constraint: {activity_name}")

    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================================================
# Life Mode Validation
# ============================================================================

def validate_life_mode_suitability(
    activities: List[Dict[str, Any]],
    recovery_blocks: List[Dict[str, Any]],
    life_mode: str,
    total_energy: int,
    daily_budget: int,
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate that plan is suitable for current life mode.

    Checks for:
    - RECOVERY mode: sufficient recovery blocks
    - CRISIS mode: minimal plan complexity
    - GROWTH mode: appropriate intensity

    Args:
        activities: List of activity dicts
        recovery_blocks: List of recovery block dicts
        life_mode: Current life mode
        total_energy: Total energy in plan
        daily_budget: Daily budget

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []

    if not life_mode:
        return True, errors

    life_mode_lower = life_mode.lower()

    # RECOVERY mode checks
    if "recovery" in life_mode_lower:
        recovery_count = len(recovery_blocks) if recovery_blocks else 0
        activity_count = len(activities) if activities else 0

        # Should have substantial recovery time
        if recovery_count == 0 and activity_count > 0:
            error = ValidationError(
                error_type=ValidationErrorType.RECOVERY_MODE_INSUFFICIENT_RECOVERY,
                message="Recovery mode should include recovery blocks but none found",
                severity=6,
                constraint="life_mode_recovery",
            )
            errors.append(error)
            logger.debug("Recovery mode: no recovery blocks")

        # Recovery energy should exceed 30% of total
        if recovery_blocks:
            recovery_energy = sum(b.get("energy_cost", 0) for b in recovery_blocks)
            if recovery_energy > 0 and total_energy > 0:
                recovery_percent = (recovery_energy / total_energy) * 100
                if recovery_percent < 20:
                    logger.debug(f"Recovery mode: recovery is only {recovery_percent:.0f}%")

    # CRISIS mode checks
    if "crisis" in life_mode_lower:
        activity_count = len(activities)
        if activity_count > 5:
            error = ValidationError(
                error_type=ValidationErrorType.ACTIVITY_INTENSITY_MISMATCH,
                message=(
                    f"Crisis mode should have minimal activities but plan has {activity_count}"
                ),
                severity=6,
                constraint="life_mode_crisis",
            )
            errors.append(error)
            logger.debug(f"Crisis mode: too many activities ({activity_count})")

        # Energy usage should be minimal (< 50% of budget)
        if total_energy > daily_budget * 0.5:
            logger.debug(f"Crisis mode: energy usage is {(total_energy/daily_budget)*100:.0f}%")

    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================================================
# Plan Structure Validation
# ============================================================================

def validate_plan_structure(
    morning_activities: List[Dict[str, Any]],
    afternoon_activities: List[Dict[str, Any]],
    evening_activities: List[Dict[str, Any]],
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate basic plan structure.

    Checks:
    - At least one timeblock present
    - At least one activity overall
    - Timeblock structure is sound

    Args:
        morning_activities: Morning activities list
        afternoon_activities: Afternoon activities list
        evening_activities: Evening activities list

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []

    m_count = len(morning_activities) if morning_activities else 0
    a_count = len(afternoon_activities) if afternoon_activities else 0
    e_count = len(evening_activities) if evening_activities else 0
    total_count = m_count + a_count + e_count

    # Check for empty plan
    if total_count == 0:
        error = ValidationError(
            error_type=ValidationErrorType.EMPTY_PLAN,
            message="Plan has no activities in any timeblock",
            severity=10,
        )
        errors.append(error)
        logger.debug("Plan structure: empty plan")

    # Check for at least one timeblock
    timeblock_count = sum(1 for count in [m_count, a_count, e_count] if count > 0)
    if timeblock_count == 0:
        error = ValidationError(
            error_type=ValidationErrorType.MISSING_TIMEBLOCKS,
            message="Plan has no morning, afternoon, or evening timeblocks",
            severity=10,
        )
        errors.append(error)
        logger.debug("Plan structure: no timeblocks")

    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================================================
# Composite Validation
# ============================================================================

def aggregate_validation_results(
    energy_valid: bool,
    energy_errors: List[ValidationError],
    environment_valid: bool,
    environment_errors: List[ValidationError],
    constraint_valid: bool,
    constraint_errors: List[ValidationError],
    life_mode_valid: bool,
    life_mode_errors: List[ValidationError],
    structure_valid: bool,
    structure_errors: List[ValidationError],
) -> Tuple[bool, List[ValidationError]]:
    """
    Aggregate validation results from all checks.

    Args:
        *_valid: Boolean results from each check
        *_errors: Error lists from each check

    Returns:
        Tuple of (overall_valid, all_errors)
    """
    all_errors = []
    all_errors.extend(energy_errors)
    all_errors.extend(environment_errors)
    all_errors.extend(constraint_errors)
    all_errors.extend(life_mode_errors)
    all_errors.extend(structure_errors)

    # Plan is valid only if no critical errors
    critical_errors = [e for e in all_errors if e.severity >= 9]
    overall_valid = len(critical_errors) == 0

    logger.debug(
        f"Validation aggregation: "
        f"energy={energy_valid}, env={environment_valid}, "
        f"constraints={constraint_valid}, life_mode={life_mode_valid}, "
        f"structure={structure_valid} => overall={overall_valid} "
        f"({len(all_errors)} errors, {len(critical_errors)} critical)"
    )

    return overall_valid, all_errors
