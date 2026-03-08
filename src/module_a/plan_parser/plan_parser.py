"""
Plan Parser - Main Orchestrator

Main class for parsing raw LLM responses into structured plan candidates.

Module: Plan Parser (Module 8)
Part of: Constraint-First Wellness Agent (Module A - Deterministic Reasoning)

Responsibilities:
1. Extract JSON from raw LLM response
2. Parse JSON to dictionary
3. Extract and normalize plan fields
4. Handle errors gracefully
5. Create PlanCandidate with full metadata
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from plan_parser_models import (
    ParsedPlanCandidate,
    ParsedDailyWellnessPlan,
    ParsingError,
    ParsingErrorType,
    ParseStatus,
)
from plan_parser_utils import (
    extract_json_from_text,
    parse_json_to_dict,
    extract_plan_fields,
    validate_plan_structure,
)

logger = logging.getLogger(__name__)


class PlanParser:
    """
    Orchestrates plan parsing from raw LLM response to structured candidate.

    Workflow:
    1. Extract JSON from raw text
    2. Parse JSON to dictionary
    3. Extract plan fields
    4. Validate plan structure
    5. Create structured DailyWellnessPlan
    6. Package as ParsedPlanCandidate with metadata
    """

    def __init__(self):
        """Initialize plan parser."""
        self.logger = logging.getLogger(__name__)

    def parse_response(
        self,
        raw_response: str,
        candidate_id: Optional[str] = None,
    ) -> ParsedPlanCandidate:
        """
        Parse raw LLM response into a plan candidate.

        Implements robust error handling - never crashes on malformed input.

        Args:
            raw_response: Raw text response from LLM
            candidate_id: Optional specific candidate ID to use

        Returns:
            ParsedPlanCandidate with plan or error details
        """
        start_time = time.time()
        
        # Generate candidate ID if not provided
        if not candidate_id:
            candidate_id = f"candidate_{uuid.uuid4().hex[:12]}"

        logger.info(f"Starting plan parsing for candidate {candidate_id}")
        logger.debug(f"Raw response length: {len(raw_response)} bytes")

        parsing_errors = []
        parsing_warnings = []
        json_extracted = None
        parsed_plan = None
        parse_status = ParseStatus.SUCCESS

        # Step 1: Extract JSON from raw text
        try:
            json_text, json_found = extract_json_from_text(raw_response)

            if not json_found or not json_text:
                error = ParsingError(
                    error_type=ParsingErrorType.JSON_NOT_FOUND,
                    message="No valid JSON object found in LLM response",
                    severity=10,
                )
                parsing_errors.append(error)
                parse_status = ParseStatus.FAILED
                logger.warning("JSON extraction failed")

            else:
                json_extracted = json_text
                logger.debug(f"JSON extracted successfully ({len(json_text)} bytes)")

        except Exception as e:
            error = ParsingError(
                error_type=ParsingErrorType.UNKNOWN,
                message=f"Error during JSON extraction: {str(e)}",
                severity=10,
            )
            parsing_errors.append(error)
            parse_status = ParseStatus.FAILED
            logger.exception("Unexpected error during JSON extraction")

        # Step 2: Parse JSON to dictionary
        if json_extracted:
            try:
                plan_dict, json_error = parse_json_to_dict(json_extracted)

                if json_error:
                    error = ParsingError(
                        error_type=ParsingErrorType.JSON_MALFORMED,
                        message=json_error,
                        severity=10,
                    )
                    parsing_errors.append(error)
                    parse_status = ParseStatus.FAILED
                    logger.warning(f"JSON parsing failed: {json_error}")

                elif plan_dict is None:
                    error = ParsingError(
                        error_type=ParsingErrorType.JSON_MALFORMED,
                        message="JSON parsed but resulted in None",
                        severity=10,
                    )
                    parsing_errors.append(error)
                    parse_status = ParseStatus.FAILED
                    logger.warning("JSON parse result was None")

                else:
                    logger.debug("JSON successfully parsed to dictionary")

            except Exception as e:
                error = ParsingError(
                    error_type=ParsingErrorType.UNKNOWN,
                    message=f"Unexpected error during JSON parsing: {str(e)}",
                    severity=10,
                )
                parsing_errors.append(error)
                parse_status = ParseStatus.FAILED
                logger.exception("Unexpected error during JSON parsing")
                plan_dict = None

        else:
            plan_dict = None

        # Step 3: Extract plan fields
        if plan_dict:
            try:
                fields, field_errors = extract_plan_fields(plan_dict)
                parsing_errors.extend(field_errors)

                # Update status if we found field errors
                if field_errors:
                    parse_status = ParseStatus.PARTIAL
                    logger.debug(f"Plan field extraction had {len(field_errors)} errors")

                logger.debug(
                    f"Plan fields extracted: "
                    f"{len(fields['morning_activities'])} morning, "
                    f"{len(fields['afternoon_activities'])} afternoon, "
                    f"{len(fields['evening_activities'])} evening, "
                    f"{len(fields['recovery_blocks'])} recovery"
                )

            except Exception as e:
                error = ParsingError(
                    error_type=ParsingErrorType.UNKNOWN,
                    message=f"Error during field extraction: {str(e)}",
                    severity=9,
                )
                parsing_errors.append(error)
                parse_status = ParseStatus.FAILED
                logger.exception("Unexpected error during field extraction")
                fields = None

        else:
            fields = None

        # Step 4: Validate plan structure
        if fields:
            try:
                is_valid, validation_errors = validate_plan_structure(fields)
                parsing_errors.extend(validation_errors)

                if not is_valid:
                    parse_status = ParseStatus.FAILED
                    logger.warning(
                        f"Plan structure validation failed: {len(validation_errors)} errors"
                    )
                else:
                    logger.debug("Plan structure validation passed")

            except Exception as e:
                error = ParsingError(
                    error_type=ParsingErrorType.UNKNOWN,
                    message=f"Error during structure validation: {str(e)}",
                    severity=8,
                )
                parsing_errors.append(error)
                parse_status = ParseStatus.FAILED
                logger.exception("Unexpected error during validation")
                is_valid = False

        else:
            is_valid = False

        # Step 5: Create structured plan object
        if fields and is_valid:
            try:
                # Generate plan_id if not in response
                plan_id = fields.get("plan_id") or f"plan_{uuid.uuid4().hex[:12]}"

                parsed_plan = ParsedDailyWellnessPlan(
                    plan_id=plan_id,
                    morning_activities=fields.get("morning_activities", []),
                    afternoon_activities=fields.get("afternoon_activities", []),
                    evening_activities=fields.get("evening_activities", []),
                    recovery_blocks=fields.get("recovery_blocks", []),
                    total_energy_allocated=fields.get("total_energy_allocated", 0),
                    plan_rationale=fields.get("plan_rationale"),
                    adaptability_score=fields.get("adaptability_score", 0.5),
                )

                logger.info(
                    f"Plan successfully created: {plan_id} "
                    f"({parsed_plan.get_activity_count()} activities)"
                )

            except Exception as e:
                error = ParsingError(
                    error_type=ParsingErrorType.UNKNOWN,
                    message=f"Error creating plan object: {str(e)}",
                    severity=10,
                )
                parsing_errors.append(error)
                parse_status = ParseStatus.FAILED
                logger.exception("Error creating plan object")
                parsed_plan = None

        # Step 6: Create candidate
        parsing_time_ms = int((time.time() - start_time) * 1000)

        candidate = ParsedPlanCandidate(
            candidate_id=candidate_id,
            plan=parsed_plan,
            raw_response=raw_response,
            parsing_status=parse_status,
            parsing_errors=parsing_errors,
            parsing_warnings=parsing_warnings,
            json_extracted=json_extracted,
            extraction_method="json_search",
            created_at=datetime.utcnow(),
            parsing_time_ms=parsing_time_ms,
        )

        logger.info(
            f"Parsing complete for {candidate_id}: "
            f"status={parse_status.value}, "
            f"errors={len(parsing_errors)}, "
            f"plan_generated={parsed_plan is not None}, "
            f"time_ms={parsing_time_ms}"
        )

        return candidate

    def parse_batch(
        self,
        responses: Dict[str, str],
    ) -> Dict[str, ParsedPlanCandidate]:
        """
        Parse multiple LLM responses.

        Args:
            responses: Dict mapping candidate_id to raw_response

        Returns:
            Dict of ParsedPlanCandidate objects keyed by candidate_id
        """
        logger.info(f"Starting batch parsing for {len(responses)} responses")
        candidates = {}

        for candidate_id, raw_response in responses.items():
            try:
                candidate = self.parse_response(raw_response, candidate_id)
                candidates[candidate_id] = candidate
            except Exception as e:
                logger.error(f"Error parsing {candidate_id}: {str(e)}", exc_info=True)
                # Create error candidate
                error = ParsingError(
                    error_type=ParsingErrorType.UNKNOWN,
                    message=f"Parsing exception: {str(e)}",
                    severity=10,
                )
                candidates[candidate_id] = ParsedPlanCandidate(
                    candidate_id=candidate_id,
                    plan=None,
                    raw_response=raw_response,
                    parsing_status=ParseStatus.FAILED,
                    parsing_errors=[error],
                    json_extracted=None,
                    created_at=datetime.utcnow(),
                )

        logger.info(f"Batch parsing complete: {len(candidates)} results")
        return candidates
