"""
Plan Validator - Main Orchestrator

Main class for validating parsed plans against system constraints.

Module: Plan Validator (Module 9)
Part of: Constraint-First Wellness Agent (Module A - Deterministic Reasoning)

Responsibilities:
1. Validate energy budget compliance
2. Validate environment restrictions
3. Validate user constraints
4. Validate life mode suitability
5. Validate plan structure
6. Aggregate results into ValidationResult
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from plan_validator_models import (
    ValidationResult,
    ValidationError,
    ValidationWarning,
    ValidationErrorType,
    ValidationSummary,
)
from plan_validator_utils import (
    validate_energy,
    validate_environment,
    validate_user_constraints,
    validate_life_mode_suitability,
    validate_plan_structure,
    aggregate_validation_results,
)

logger = logging.getLogger(__name__)


class PlanValidator:
    """
    Orchestrates plan validation against system constraints.

    Validation workflow:
    1. Energy validation - budget compliance
    2. Environment validation - restriction compliance
    3. Constraint validation - user constraint compliance
    4. Life mode validation - mode suitability
    5. Structure validation - basic plan structure
    6. Result aggregation - create ValidationResult
    """

    def __init__(self):
        """Initialize plan validator."""
        self.logger = logging.getLogger(__name__)

    def validate_plan(
        self,
        parsed_plan: Dict[str, Any],
        energy_budget: Optional[Dict[str, Any]] = None,
        environment_context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        life_mode: Optional[str] = None,
        candidate_id: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a parsed plan against all system constraints.

        Args:
            parsed_plan: Parsed DailyWellnessPlan data (as dict)
            energy_budget: Energy budget context
            environment_context: Environment constraints
            constraints: User constraints
            life_mode: Current life mode
            candidate_id: Candidate being validated

        Returns:
            ValidationResult with validation status and errors
        """
        start_time = time.time()

        if not candidate_id:
            candidate_id = f"candidate_{uuid.uuid4().hex[:12]}"

        logger.info(f"Starting plan validation for {candidate_id}")

        # ====================================================================
        # Initialize
        # ====================================================================
        energy_budget = energy_budget or {}
        environment_context = environment_context or {}
        constraints = constraints or {}

        daily_budget = energy_budget.get("daily_budget", 100)
        activity_restrictions = environment_context.get("activity_restrictions", [])
        available_activity_types = environment_context.get(
            "available_activity_types", []
        )

        logger.debug(f"Energy budget: {daily_budget}")
        logger.debug(f"Activity restrictions: {len(activity_restrictions)}")

        # Collect all activities
        morning_acts = parsed_plan.get("morning_activities", [])
        afternoon_acts = parsed_plan.get("afternoon_activities", [])
        evening_acts = parsed_plan.get("evening_activities", [])
        recovery_acts = parsed_plan.get("recovery_blocks", [])

        all_activities = morning_acts + afternoon_acts + evening_acts + recovery_acts

        total_energy = parsed_plan.get("total_energy_allocated", 0)

        logger.debug(f"Activities: {len(all_activities)} total")
        logger.debug(f"Total energy allocated: {total_energy}")

        # ====================================================================
        # STEP 1: Energy Validation
        # ====================================================================
        logger.info("Step 1: Energy validation...")

        energy_valid, energy_errors = validate_energy(
            total_energy_allocated=total_energy,
            daily_budget=daily_budget,
            activities=all_activities,
        )

        logger.debug(
            f"✓ Energy validation complete: "
            f"valid={energy_valid}, "
            f"errors={len(energy_errors)}"
        )

        # ====================================================================
        # STEP 2: Environment Validation
        # ====================================================================
        logger.info("Step 2: Environment validation...")

        environment_valid, environment_errors = validate_environment(
            activities=all_activities,
            environment_context=environment_context,
            activity_restrictions=activity_restrictions,
            available_activity_types=available_activity_types,
        )

        logger.debug(
            f"✓ Environment validation complete: "
            f"valid={environment_valid}, "
            f"errors={len(environment_errors)}"
        )

        # ====================================================================
        # STEP 3: Constraint Validation
        # ====================================================================
        logger.info("Step 3: User constraint validation...")

        user_constraints_list = constraints.get("constraints", [])
        constraint_valid, constraint_errors = validate_user_constraints(
            activities=all_activities,
            user_constraints=user_constraints_list,
        )

        logger.debug(
            f"✓ Constraint validation complete: "
            f"valid={constraint_valid}, "
            f"errors={len(constraint_errors)}"
        )

        # ====================================================================
        # STEP 4: Life Mode Validation
        # ====================================================================
        logger.info("Step 4: Life mode suitability validation...")

        life_mode_valid, life_mode_errors = validate_life_mode_suitability(
            activities=morning_acts + afternoon_acts + evening_acts,
            recovery_blocks=recovery_acts,
            life_mode=life_mode or "maintenance",
            total_energy=total_energy,
            daily_budget=daily_budget,
        )

        logger.debug(
            f"✓ Life mode validation complete: "
            f"valid={life_mode_valid}, "
            f"errors={len(life_mode_errors)}"
        )

        # ====================================================================
        # STEP 5: Plan Structure Validation
        # ====================================================================
        logger.info("Step 5: Plan structure validation...")

        structure_valid, structure_errors = validate_plan_structure(
            morning_activities=morning_acts,
            afternoon_activities=afternoon_acts,
            evening_activities=evening_acts,
        )

        logger.debug(
            f"✓ Structure validation complete: "
            f"valid={structure_valid}, "
            f"errors={len(structure_errors)}"
        )

        # ====================================================================
        # STEP 6: Aggregate Results
        # ====================================================================
        logger.info("Step 6: Aggregating validation results...")

        overall_valid, all_errors = aggregate_validation_results(
            energy_valid=energy_valid,
            energy_errors=energy_errors,
            environment_valid=environment_valid,
            environment_errors=environment_errors,
            constraint_valid=constraint_valid,
            constraint_errors=constraint_errors,
            life_mode_valid=life_mode_valid,
            life_mode_errors=life_mode_errors,
            structure_valid=structure_valid,
            structure_errors=structure_errors,
        )

        # ====================================================================
        # STEP 7: Calculate Metrics
        # ====================================================================
        validation_time_ms = int((time.time() - start_time) * 1000)

        energy_remaining = daily_budget - total_energy
        energy_violation_percent = 0.0
        if total_energy > daily_budget:
            energy_violation_percent = ((total_energy - daily_budget) / daily_budget) * 100

        restricted_activities = len(
            [e for e in all_errors if e.error_type == ValidationErrorType.ACTIVITY_RESTRICTED]
        )
        conflicting_activities = len(
            [e for e in all_errors if e.error_type == ValidationErrorType.CONSTRAINT_VIOLATED]
        )

        # ====================================================================
        # Create Result
        # ====================================================================
        logger.info("Step 7: Creating validation result...")

        # Determine validation status
        if overall_valid:
            validation_status = "validated"
        else:
            # Check if there are critical energy/structure errors
            critical_errors = [e for e in all_errors if e.severity >= 9]
            if critical_errors:
                validation_status = "rejected"
            elif len(all_errors) <= 2:
                validation_status = "partial"
            else:
                validation_status = "rejected"

        result = ValidationResult(
            candidate_id=candidate_id,
            is_valid=overall_valid,
            validation_status=validation_status,
            validation_errors=all_errors,
            validation_warnings=[],
            energy_validation_passed=energy_valid,
            environment_validation_passed=environment_valid,
            constraint_validation_passed=constraint_valid,
            life_mode_validation_passed=life_mode_valid,
            structure_validation_passed=structure_valid,
            total_energy_used=total_energy,
            energy_budget_available=daily_budget,
            energy_remaining_after_plan=energy_remaining,
            energy_violation_percent=energy_violation_percent,
            activities_restricted=restricted_activities,
            activities_conflicting=conflicting_activities,
            activities_problematic=len(all_errors),
            validated_at=datetime.utcnow(),
            validation_time_ms=validation_time_ms,
        )

        logger.info(
            f"✓ Validation result created: "
            f"is_valid={overall_valid}, "
            f"status={validation_status}, "
            f"errors={result.error_count()}"
        )

        # ====================================================================
        # Final Logging
        # ====================================================================
        logger.info("=" * 80)
        logger.info("PLAN VALIDATION COMPLETE")
        logger.info(f"Candidate: {candidate_id}")
        logger.info(f"Valid: {overall_valid}")
        logger.info(f"Status: {validation_status}")
        logger.info(f"Errors: {result.error_count()} (critical: {result.critical_error_count()})")
        logger.info(f"Energy: {total_energy}/{daily_budget} ({energy_violation_percent:+.1f}%)")
        logger.info(f"Time: {validation_time_ms}ms")
        logger.info("=" * 80)

        return result

    def validate_batch(
        self,
        plans: Dict[str, Dict[str, Any]],
        energy_budget: Optional[Dict[str, Any]] = None,
        environment_context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        life_mode: Optional[str] = None,
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple plans.

        Args:
            plans: Dict mapping candidate_id to plan data
            energy_budget: Energy budget context
            environment_context: Environment constraints
            constraints: User constraints
            life_mode: Current life mode

        Returns:
            Dict of ValidationResult objects keyed by candidate_id
        """
        logger.info(f"Starting batch validation for {len(plans)} plans")
        results = {}

        for candidate_id, plan_data in plans.items():
            try:
                result = self.validate_plan(
                    parsed_plan=plan_data,
                    energy_budget=energy_budget,
                    environment_context=environment_context,
                    constraints=constraints,
                    life_mode=life_mode,
                    candidate_id=candidate_id,
                )
                results[candidate_id] = result
            except Exception as e:
                logger.error(f"Error validating {candidate_id}: {str(e)}", exc_info=True)
                # Create error result
                error = ValidationError(
                    error_type=ValidationErrorType.UNKNOWN,
                    message=f"Validation exception: {str(e)}",
                    severity=10,
                )
                results[candidate_id] = ValidationResult(
                    candidate_id=candidate_id,
                    is_valid=False,
                    validation_status="failed",
                    validation_errors=[error],
                )

        logger.info(f"Batch validation complete: {len(results)} results")
        return results

    def create_summary(
        self,
        validation_results: Dict[str, ValidationResult],
    ) -> ValidationSummary:
        """
        Create summary of batch validation results.

        Args:
            validation_results: Dict of ValidationResult objects

        Returns:
            ValidationSummary
        """
        valid_count = sum(1 for r in validation_results.values() if r.is_valid)
        rejected_count = sum(
            1 for r in validation_results.values() if r.validation_status == "rejected"
        )
        partial_count = sum(
            1 for r in validation_results.values() if r.validation_status == "partial"
        )

        total_errors = sum(r.error_count() for r in validation_results.values())
        total_warnings = sum(r.warning_count() for r in validation_results.values())
        critical_errors = sum(r.critical_error_count() for r in validation_results.values())

        # Find most common error type
        error_counts = {}
        for result in validation_results.values():
            for error in result.validation_errors:
                error_type = error.error_type.value
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        most_common_error = None
        if error_counts:
            most_common_type = max(error_counts, key=error_counts.get)
            most_common_error = ValidationErrorType(most_common_type)

        return ValidationSummary(
            candidates_validated=len(validation_results),
            candidates_valid=valid_count,
            candidates_rejected=rejected_count,
            candidates_partial=partial_count,
            total_errors=total_errors,
            total_warnings=total_warnings,
            critical_error_count=critical_errors,
            most_common_error=most_common_error,
            error_frequency=error_counts,
        )
