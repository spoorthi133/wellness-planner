"""
Plan Parser Node - LangGraph Integration

LangGraph node for plan parser.

Position in workflow:
Plan Request Node (gets LLM response)
   ↓
Plan Parser Node (this node)  ← Converts raw response to structured plan
   ↓
Plan Validator Node (validates plan)

Module: Plan Parser (Module 8)
Part of: Constraint-First Wellness Agent (Module A - Deterministic Reasoning)

Schema Compliance Notes:
- Input: state.raw_llm_response (set by plan_request_node)
- Output: Updates state.plan_candidates list
- Also updates: execution_trace, last_node_executed
- No new top-level state fields created
"""

import logging
import time
from typing import Dict, Any
from datetime import datetime
from copy import deepcopy

from plan_parser import PlanParser
from plan_parser_models import PlanParserExecutionTrace

logger = logging.getLogger(__name__)


def plan_parser_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Plan Parser.

    Converts raw LLM response into structured plan candidates.

    Input state requirements:
    - user_id
    - raw_llm_response (str): Raw text from LLM
    - execution_trace (list, optional)

    Output state mutations:
    - plan_candidates: List appended with new candidate
    - last_node_executed: Set to 'plan_parser'
    - execution_trace: Appended with parser trace entry

    Args:
        state: Current state dictionary

    Returns:
        Updated state with parsed plan candidate(s)

    Raises:
        ValueError: If critical state fields are missing
    """
    start_time = time.time()

    logger.info("=" * 80)
    logger.info("PLAN PARSER NODE START")
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

        raw_response = updated_state.get("raw_llm_response")
        if not raw_response:
            logger.error("raw_llm_response required in state")
            raise ValueError("raw_llm_response is required in state")

        if not isinstance(raw_response, str):
            logger.error(f"raw_llm_response must be string, got {type(raw_response)}")
            raise ValueError("raw_llm_response must be a string")

        logger.debug("✓ State validation passed")
        logger.debug(f"  User: {user_id}")
        logger.debug(f"  Response size: {len(raw_response)} bytes")

        # ====================================================================
        # STEP 2: Initialize parser
        # ====================================================================
        logger.info("Step 2: Initializing plan parser...")

        parser = PlanParser()
        logger.debug("✓ Parser initialized")

        # ====================================================================
        # STEP 3: Parse response
        # ====================================================================
        logger.info("Step 3: Parsing LLM response...")

        parsed_candidate = parser.parse_response(raw_response)

        logger.info(
            f"✓ Parsing complete: {parsed_candidate.candidate_id} "
            f"(status={parsed_candidate.parsing_status.value}, "
            f"errors={parsed_candidate.get_error_count()})"
        )

        if parsed_candidate.plan:
            logger.info(
                f"  Plan ID: {parsed_candidate.plan.plan_id} "
                f"({parsed_candidate.plan.get_activity_count()} activities)"
            )
        else:
            logger.warning(f"  No plan object created (parsing failed)")

        # ====================================================================
        # STEP 4: Append to plan_candidates list
        # ====================================================================
        logger.info("Step 4: Appending candidate to state...")

        if "plan_candidates" not in updated_state:
            updated_state["plan_candidates"] = []

        updated_state["plan_candidates"].append(parsed_candidate)
        logger.debug(
            f"✓ Candidate appended (total candidates: {len(updated_state['plan_candidates'])})"
        )

        # ====================================================================
        # STEP 5: Create execution trace
        # ====================================================================
        logger.info("Step 5: Creating execution trace...")

        trace_entry = _create_trace_entry(user_id, parsed_candidate)

        # Append to execution_trace
        if "execution_trace" not in updated_state:
            updated_state["execution_trace"] = []

        updated_state["execution_trace"].append(trace_entry.dict())
        logger.debug("✓ Trace entry appended")

        # ====================================================================
        # STEP 6: Update last_node_executed
        # ====================================================================
        logger.info("Step 6: Updating last_node_executed...")

        updated_state["last_node_executed"] = "plan_parser"
        logger.debug("✓ Flag updated")

        # ====================================================================
        # STEP 7: Calculate execution time
        # ====================================================================
        elapsed_time = time.time() - start_time

        # ====================================================================
        # Final logging
        # ====================================================================
        logger.info("=" * 80)
        logger.info("PLAN PARSER NODE COMPLETE")
        logger.info(f"Candidate: {parsed_candidate.candidate_id}")
        logger.info(f"Status: {parsed_candidate.parsing_status.value}")
        logger.info(f"Errors: {parsed_candidate.get_error_count()}")
        logger.info(f"Warnings: {parsed_candidate.get_warning_count()}")
        logger.info(f"Usable: {parsed_candidate.is_usable()}")
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
        logger.error(f"Unexpected error in plan_parser_node: {e}", exc_info=True)
        raise


def _create_trace_entry(
    user_id: str,
    candidate: "ParsedPlanCandidate",  # type: ignore
) -> PlanParserExecutionTrace:
    """
    Create execution trace entry for parser node.

    Args:
        user_id: User identifier
        candidate: Parsed plan candidate

    Returns:
        PlanParserExecutionTrace entry
    """
    return PlanParserExecutionTrace(
        node="plan_parser",
        timestamp=datetime.utcnow(),
        user_id=user_id,
        candidate_id=candidate.candidate_id,
        raw_response_size_bytes=len(candidate.raw_response),
        parsing_status=candidate.parsing_status,
        success=candidate.is_usable(),
        parsing_errors=[err.message for err in candidate.parsing_errors],
        parsing_warnings=candidate.parsing_warnings,
        error_count=candidate.get_error_count(),
        warning_count=candidate.get_warning_count(),
        json_found=candidate.json_extracted is not None,
        plan_generated=candidate.plan is not None,
        activity_count=candidate.plan.get_activity_count() if candidate.plan else 0,
        total_energy_allocated=(
            candidate.plan.total_energy_allocated if candidate.plan else 0
        ),
        parsing_time_ms=candidate.parsing_time_ms,
    )
