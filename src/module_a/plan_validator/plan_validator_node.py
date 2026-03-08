"""
Plan Validator Node - LangGraph Integration

LangGraph node for plan validator.

Position in workflow:
Plan Parser Node (creates parsed plan)
   ↓
Plan Validator Node (this node)  ← Validates plan against constraints
   ↓
Plan Selection/Ranking Node (chooses best plan)

Module: Plan Validator (Module 9)
Part of: Constraint-First Wellness Agent (Module A - Deterministic Reasoning)

Schema Compliance Notes:
- Input: Latest plan_candidate in state.plan_candidates list
- Input: Energy budget, environment, constraints from state
- Output: Updates candidate.status in state.plan_candidates list
- Also updates: execution_trace, last_node_executed
- No new top-level state fields created
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from copy import deepcopy

from plan_validator import PlanValidator
from plan_validator_models import PlanValidatorExecutionTrace

logger = logging.getLogger(__name__)


def plan_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Plan Validator.

    Validates parsed plan candidates against system constraints.

    Input state requirements:
    - user_id
    - plan_candidates (list): Should have at least one candidate
    - energy_budget (dict)
    - environment_context (dict)
    - constraints (dict)
    - life_mode (str or dict)
    - execution_trace (list, optional)

    Output state mutations:
    - plan_candidates: Latest candidate's status updated to validated/rejected
    - last_node_executed: Set to 'plan_validator'
    - execution_trace: Appended with validator trace entry

    Args:
        state: Current state dictionary

    Returns:
        Updated state with validated plan

    Raises:
        ValueError: If critical state fields are missing
    """
    start_time = time.time()

    logger.info("=" * 80)
    logger.info("PLAN VALIDATOR NODE START")
    logger.info("=" * 80)

    try:
        # Make a copy to avoid mutating original state outside of this function
        updated_state = deepcopy(state)

        # ====================================================================
        # STEP 1: Validation
        # ====================================================================
        logger.info("Step 1: Validating state inputs...")

        user_id = updated_state.get("user_id")
        if not user_id:
            logger.error("user_id required in state")
            raise ValueError("user_id is required in state")

        plan_candidates = updated_state.get("plan_candidates", [])
        if not plan_candidates:
            logger.error("plan_candidates list is empty")
            raise ValueError("plan_candidates list is empty - no plan to validate")

        # Get latest candidate
        latest_candidate = plan_candidates[-1]
        if not latest_candidate:
            logger.error("Latest candidate is None")
            raise ValueError("Latest candidate is None")

        # Check if plan exists
        if not latest_candidate.get("plan"):
            logger.warning("Latest candidate has no plan object (parsing failed)")
            # Still need to mark as rejected in validation
            latest_candidate = _mark_candidate_rejected(
                latest_candidate,
                "Plan object missing - parsing failed"
            )
            updated_state["plan_candidates"][-1] = latest_candidate
            updated_state["last_node_executed"] = "plan_validator"
            return updated_state

        candidate_id = latest_candidate.get("candidate_id")
        plan_data = latest_candidate.get("plan")

        logger.debug(f"✓ State validation passed")
        logger.debug(f"  User: {user_id}")
        logger.debug(f"  Candidate: {candidate_id}")
        logger.debug(f"  Activities: {_count_activities(plan_data)}")

        # ====================================================================
        # STEP 2: Extract context from state
        # ====================================================================
        logger.info("Step 2: Extracting context from state...")

        energy_budget = updated_state.get("energy_budget", {})
        environment_context = updated_state.get("environment_context", {})
        constraints = updated_state.get("constraints", {})
        life_mode_obj = updated_state.get("life_mode", {})

        # Handle both dict and LifeMode object
        life_mode = None
        if isinstance(life_mode_obj, dict):
            life_mode = life_mode_obj.get("mode")
        elif isinstance(life_mode_obj, str):
            life_mode = life_mode_obj
        else:
            life_mode = "maintenance"

        logger.debug(f"✓ Context extracted")
        logger.debug(f"  Energy budget: {energy_budget.get('daily_budget', 100)}")
        logger.debug(f"  Life mode: {life_mode}")

        # ====================================================================
        # STEP 3: Initialize validator
        # ====================================================================
        logger.info("Step 3: Initializing plan validator...")

        validator = PlanValidator()
        logger.debug("✓ Validator initialized")

        # ====================================================================
        # STEP 4: Validate plan
        # ====================================================================
        logger.info("Step 4: Validating plan...")

        validation_result = validator.validate_plan(
            parsed_plan=plan_data,
            energy_budget=energy_budget,
            environment_context=environment_context,
            constraints=constraints,
            life_mode=life_mode,
            candidate_id=candidate_id,
        )

        logger.info(
            f"✓ Validation complete: "
            f"is_valid={validation_result.is_valid}, "
            f"status={validation_result.validation_status}, "
            f"errors={validation_result.error_count()}"
        )

        # ====================================================================
        # STEP 5: Update candidate status
        # ====================================================================
        logger.info("Step 5: Updating candidate status...")

        if validation_result.is_valid:
            status = "validated"
        else:
            status = "rejected"

        latest_candidate["validation_result"] = validation_result.dict()
        latest_candidate["status"] = status
        latest_candidate["validated_at"] = datetime.utcnow().isoformat()

        updated_state["plan_candidates"][-1] = latest_candidate
        logger.debug(f"✓ Candidate status updated: {status}")

        # ====================================================================
        # STEP 6: Create execution trace
        # ====================================================================
        logger.info("Step 6: Creating execution trace...")

        trace_entry = _create_trace_entry(
            user_id=user_id,
            candidate_id=candidate_id,
            validation_result=validation_result,
        )

        # Append to execution_trace
        if "execution_trace" not in updated_state:
            updated_state["execution_trace"] = []

        updated_state["execution_trace"].append(trace_entry.dict())
        logger.debug("✓ Trace entry appended")

        # ====================================================================
        # STEP 7: Update last_node_executed
        # ====================================================================
        logger.info("Step 7: Updating last_node_executed...")

        updated_state["last_node_executed"] = "plan_validator"
        logger.debug("✓ Flag updated")

        # ====================================================================
        # STEP 8: Calculate execution time
        # ====================================================================
        elapsed_time = time.time() - start_time

        # ====================================================================
        # Final logging
        # ====================================================================
        logger.info("=" * 80)
        logger.info("PLAN VALIDATOR NODE COMPLETE")
        logger.info(f"Candidate: {candidate_id}")
        logger.info(f"Valid: {validation_result.is_valid}")
        logger.info(f"Status: {validation_result.validation_status}")
        logger.info(f"Errors: {validation_result.error_count()}")
        logger.info(f"Critical Errors: {validation_result.critical_error_count()}")
        logger.info(
            f"Energy: {validation_result.total_energy_used}/"
            f"{validation_result.energy_budget_available}"
        )
        logger.info(f"Processing Time: {elapsed_time:.3f}s")
        logger.info("=" * 80)

        return updated_state

    except ValueError as e:
        logger.error(f"State validation error: {e}")
        raise
    except KeyError as e:
        logger.error(f"Missing state field: {e}")
        raise ValueError(f"Required state field missing: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in plan_validator_node: {e}", exc_info=True)
        raise


def _count_activities(plan_data: Dict[str, Any]) -> int:
    """Count activities in a plan."""
    count = 0
    count += len(plan_data.get("morning_activities", []))
    count += len(plan_data.get("afternoon_activities", []))
    count += len(plan_data.get("evening_activities", []))
    count += len(plan_data.get("recovery_blocks", []))
    return count


def _mark_candidate_rejected(
    candidate: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    """Mark a candidate as rejected with reason."""
    candidate["status"] = "rejected"
    candidate["validated_at"] = datetime.utcnow().isoformat()
    if "validation_result" not in candidate:
        candidate["validation_result"] = {
            "candidate_id": candidate.get("candidate_id"),
            "is_valid": False,
            "validation_status": "rejected",
            "validation_errors": [
                {
                    "error_type": "unknown",
                    "message": reason,
                    "severity": 10,
                }
            ],
        }
    return candidate


def _create_trace_entry(
    user_id: str,
    candidate_id: str,
    validation_result: "ValidationResult",  # type: ignore
) -> PlanValidatorExecutionTrace:
    """
    Create execution trace entry for validator node.

    Args:
        user_id: User identifier
        candidate_id: Candidate being validated
        validation_result: Validation result object

    Returns:
        PlanValidatorExecutionTrace entry
    """
    return PlanValidatorExecutionTrace(
        node="plan_validator",
        timestamp=datetime.utcnow(),
        user_id=user_id,
        candidate_id=candidate_id,
        is_valid=validation_result.is_valid,
        validation_status=validation_result.validation_status,
        success=True,
        energy_check_passed=validation_result.energy_validation_passed,
        environment_check_passed=validation_result.environment_validation_passed,
        constraint_check_passed=validation_result.constraint_validation_passed,
        life_mode_check_passed=validation_result.life_mode_validation_passed,
        structure_check_passed=validation_result.structure_validation_passed,
        error_count=validation_result.error_count(),
        critical_error_count=validation_result.critical_error_count(),
        warning_count=validation_result.warning_count(),
        total_energy_used=validation_result.total_energy_used,
        energy_violation_percent=validation_result.energy_violation_percent,
        activities_restricted=validation_result.activities_restricted,
        activities_conflicting=validation_result.activities_conflicting,
        validation_time_ms=validation_result.validation_time_ms,
        error_messages=[err.message for err in validation_result.validation_errors[:5]],
    )
