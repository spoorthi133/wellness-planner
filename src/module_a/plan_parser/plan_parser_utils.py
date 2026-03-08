"""
Plan Parser Utilities

Utility functions for parsing LLM responses and extracting plan data.

Module: Plan Parser (Module 8)
Part of: Constraint-First Wellness Agent (Module A - Deterministic Reasoning)

This module provides:
- JSON extraction from raw text
- JSON validation and parsing
- Field extraction and normalization
- Activity parsing
- Error handling and recovery
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from plan_parser_models import (
    ParsedActivity,
    ParsedActivityTimeblock,
    ParsedDailyWellnessPlan,
    ParsingError,
    ParsingErrorType,
    ParseStatus,
)

logger = logging.getLogger(__name__)


# ============================================================================
# JSON Extraction
# ============================================================================

def extract_json_from_text(raw_text: str) -> Tuple[Optional[str], bool]:
    """
    Extract JSON object from raw LLM response text.

    Tries multiple strategies:
    1. Find complete JSON objects enclosed in {}
    2. Look for markdown code blocks with JSON
    3. Search for JSON-like patterns

    Args:
        raw_text: Raw LLM response text

    Returns:
        Tuple of (extracted_json_string, was_found)
        Returns (None, False) if no valid JSON found
    """
    if not raw_text or not raw_text.strip():
        logger.warning("Raw text is empty")
        return None, False

    # Strategy 1: Look for markdown code blocks
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
    if code_block_match:
        json_text = code_block_match.group(1).strip()
        if _is_valid_json(json_text):
            logger.debug("JSON found in code block")
            return json_text, True

    # Strategy 2: Find JSON object patterns { ... }
    # Start from first { and try to find matching }
    start_idx = raw_text.find("{")
    if start_idx == -1:
        logger.warning("No { found in response")
        return None, False

    # Try to find valid JSON by working backwards from end
    for end_idx in range(len(raw_text), start_idx, -1):
        potential_json = raw_text[start_idx:end_idx].rstrip()
        if _is_valid_json(potential_json):
            logger.debug(f"Valid JSON found at indices {start_idx}:{end_idx}")
            return potential_json, True

    logger.warning("No valid JSON object found in response")
    return None, False


def _is_valid_json(text: str) -> bool:
    """Check if text is valid JSON."""
    if not text or not text.strip():
        return False
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def parse_json_to_dict(json_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parse JSON string to dictionary.

    Args:
        json_text: JSON string

    Returns:
        Tuple of (parsed_dict, error_message)
        Returns (None, error_msg) if parsing fails
    """
    try:
        data = json.loads(json_text)
        if not isinstance(data, dict):
            return None, "JSON root must be an object, not array or primitive"
        logger.debug("JSON successfully parsed")
        return data, None
    except json.JSONDecodeError as e:
        error_msg = f"JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}"
        logger.warning(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error parsing JSON: {str(e)}"
        logger.warning(error_msg)
        return None, error_msg


# ============================================================================
# Activity Parsing
# ============================================================================

def parse_activity_list(
    activities_data: Any, activity_type: str = "activity"
) -> Tuple[List[ParsedActivityTimeblock], List[ParsingError]]:
    """
    Parse list of activity dictionaries into structured objects.

    Args:
        activities_data: List or None from JSON
        activity_type: Type label for error messages

    Returns:
        Tuple of (parsed_activities, parsing_errors)
    """
    errors = []
    activities = []

    if activities_data is None:
        logger.debug(f"No {activity_type} list provided")
        return activities, errors

    if not isinstance(activities_data, list):
        error = ParsingError(
            error_type=ParsingErrorType.INVALID_FIELD_TYPE,
            message=f"Expected list of {activity_type}s, got {type(activities_data).__name__}",
            field="activities",
            severity=7,
        )
        errors.append(error)
        logger.warning(f"Invalid type for activities: {type(activities_data)}")
        return activities, errors

    for idx, activity_data in enumerate(activities_data):
        if not isinstance(activity_data, dict):
            error = ParsingError(
                error_type=ParsingErrorType.INVALID_ACTIVITY_STRUCTURE,
                message=f"{activity_type}[{idx}] is not a dict",
                field=f"activities[{idx}]",
                severity=6,
            )
            errors.append(error)
            continue

        # Parse individual activity
        parsed, act_errors = parse_single_activity(activity_data, idx)
        if parsed:
            activities.append(parsed)
        errors.extend(act_errors)

    logger.debug(f"Parsed {len(activities)} {activity_type}s with {len(errors)} errors")
    return activities, errors


def parse_single_activity(
    activity_dict: Dict[str, Any], index: int = 0
) -> Tuple[Optional[ParsedActivityTimeblock], List[ParsingError]]:
    """
    Parse single activity dictionary.

    Args:
        activity_dict: Activity data
        index: Index in list (for error messages)

    Returns:
        Tuple of (parsed_activity, parsing_errors)
    """
    errors = []
    field_prefix = f"activities[{index}]"

    # Extract required fields
    activity_name = _extract_string_field(activity_dict, "activity", field_prefix, errors)
    duration = _extract_int_field(
        activity_dict, "duration_minutes", field_prefix, errors, min_val=1
    )
    energy_cost = _extract_int_field(
        activity_dict, "energy_cost", field_prefix, errors, min_val=0
    )
    description = _extract_optional_string_field(activity_dict, "description", field_prefix)

    # If required fields are missing, return error
    if activity_name is None or duration is None or energy_cost is None:
        logger.debug(f"Activity[{index}] missing required fields")
        return None, errors

    try:
        activity = ParsedActivityTimeblock(
            activity=activity_name,
            duration_minutes=duration,
            energy_cost=energy_cost,
            description=description,
        )
        return activity, errors
    except Exception as e:
        error = ParsingError(
            error_type=ParsingErrorType.INVALID_ACTIVITY_STRUCTURE,
            message=f"Failed to create activity: {str(e)}",
            field=field_prefix,
            severity=8,
            raw_value=str(activity_dict),
        )
        errors.append(error)
        return None, errors


def _extract_string_field(
    data: Dict[str, Any],
    field_name: str,
    field_prefix: str,
    errors: List[ParsingError],
) -> Optional[str]:
    """Extract and validate string field."""
    if field_name not in data:
        error = ParsingError(
            error_type=ParsingErrorType.MISSING_REQUIRED_FIELD,
            message=f"Missing required field '{field_name}'",
            field=f"{field_prefix}.{field_name}",
            severity=9,
        )
        errors.append(error)
        return None

    value = data[field_name]
    if not isinstance(value, str):
        error = ParsingError(
            error_type=ParsingErrorType.INVALID_FIELD_TYPE,
            message=f"Field '{field_name}' should be string, got {type(value).__name__}",
            field=f"{field_prefix}.{field_name}",
            severity=7,
            raw_value=str(value),
        )
        errors.append(error)
        return None

    if not value.strip():
        error = ParsingError(
            error_type=ParsingErrorType.INVALID_FIELD_VALUE,
            message=f"Field '{field_name}' cannot be empty",
            field=f"{field_prefix}.{field_name}",
            severity=6,
        )
        errors.append(error)
        return None

    return value.strip()


def _extract_optional_string_field(
    data: Dict[str, Any], field_name: str, field_prefix: str
) -> Optional[str]:
    """Extract optional string field."""
    if field_name not in data:
        return None

    value = data[field_name]
    if value is None:
        return None

    if not isinstance(value, str):
        logger.debug(
            f"Optional field {field_prefix}.{field_name} has wrong type, skipping"
        )
        return None

    return value.strip() if value.strip() else None


def _extract_int_field(
    data: Dict[str, Any],
    field_name: str,
    field_prefix: str,
    errors: List[ParsingError],
    min_val: int = 0,
    max_val: Optional[int] = None,
) -> Optional[int]:
    """Extract and validate integer field."""
    if field_name not in data:
        error = ParsingError(
            error_type=ParsingErrorType.MISSING_REQUIRED_FIELD,
            message=f"Missing required field '{field_name}'",
            field=f"{field_prefix}.{field_name}",
            severity=9,
        )
        errors.append(error)
        return None

    value = data[field_name]

    # Try to convert to int
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        error = ParsingError(
            error_type=ParsingErrorType.INVALID_FIELD_TYPE,
            message=f"Field '{field_name}' should be integer, got {type(value).__name__}",
            field=f"{field_prefix}.{field_name}",
            severity=8,
            raw_value=str(value),
        )
        errors.append(error)
        return None

    # Validate range
    if int_value < min_val or (max_val is not None and int_value > max_val):
        constraint_str = f"must be >= {min_val}"
        if max_val is not None:
            constraint_str = f"must be between {min_val} and {max_val}"

        error = ParsingError(
            error_type=ParsingErrorType.INVALID_FIELD_VALUE,
            message=f"Field '{field_name}' {constraint_str}, got {int_value}",
            field=f"{field_prefix}.{field_name}",
            severity=6,
            raw_value=str(value),
        )
        errors.append(error)
        return None

    return int_value


# ============================================================================
# Plan Data Extraction
# ============================================================================

def extract_plan_fields(
    plan_dict: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[ParsingError]]:
    """
    Extract and normalize plan fields from parsed JSON.

    Args:
        plan_dict: Parsed JSON dictionary

    Returns:
        Tuple of (extracted_fields, parsing_errors)
    """
    errors = []
    fields = {
        "plan_id": None,
        "morning_activities": [],
        "afternoon_activities": [],
        "evening_activities": [],
        "recovery_blocks": [],
        "total_energy_allocated": 0,
        "plan_rationale": None,
        "adaptability_score": 0.5,
    }

    # Extract plan_id (can be missing, will generate one)
    if "plan_id" in plan_dict:
        plan_id = plan_dict["plan_id"]
        if isinstance(plan_id, str) and plan_id.strip():
            fields["plan_id"] = plan_id.strip()

    # Extract activities for each timeblock
    morning_acts, morning_errors = parse_activity_list(
        plan_dict.get("morning_activities"), "morning_activity"
    )
    fields["morning_activities"] = morning_acts
    errors.extend(morning_errors)

    afternoon_acts, afternoon_errors = parse_activity_list(
        plan_dict.get("afternoon_activities"), "afternoon_activity"
    )
    fields["afternoon_activities"] = afternoon_acts
    errors.extend(afternoon_errors)

    evening_acts, evening_errors = parse_activity_list(
        plan_dict.get("evening_activities"), "evening_activity"
    )
    fields["evening_activities"] = evening_acts
    errors.extend(evening_errors)

    recovery_acts, recovery_errors = parse_activity_list(
        plan_dict.get("recovery_blocks"), "recovery_block"
    )
    fields["recovery_blocks"] = recovery_acts
    errors.extend(recovery_errors)

    # Extract total energy
    if "total_energy_allocated" in plan_dict:
        total_energy = _extract_int_field(
            plan_dict, "total_energy_allocated", "plan", errors, min_val=0, max_val=1000
        )
        if total_energy is not None:
            fields["total_energy_allocated"] = total_energy

    # Extract plan rationale
    if "plan_rationale" in plan_dict and isinstance(plan_dict["plan_rationale"], str):
        rationale = plan_dict["plan_rationale"].strip()
        if rationale:
            fields["plan_rationale"] = rationale

    # Extract adaptability score
    if "adaptability_score" in plan_dict:
        try:
            score = float(plan_dict["adaptability_score"])
            if 0 <= score <= 1:
                fields["adaptability_score"] = score
        except (ValueError, TypeError):
            logger.debug("Could not parse adaptability_score, using default")

    return fields, errors


# ============================================================================
# Validation
# ============================================================================

def validate_plan_structure(
    fields: Dict[str, Any],
) -> Tuple[bool, List[ParsingError]]:
    """
    Validate that extracted plan fields form a valid structure.

    Args:
        fields: Extracted plan fields

    Returns:
        Tuple of (is_valid, validation_errors)
    """
    errors = []

    # Check that at least one activity exists
    activity_count = (
        len(fields.get("morning_activities", []))
        + len(fields.get("afternoon_activities", []))
        + len(fields.get("evening_activities", []))
        + len(fields.get("recovery_blocks", []))
    )

    if activity_count == 0:
        error = ParsingError(
            error_type=ParsingErrorType.EMPTY_PLAN,
            message="Plan has no activities",
            severity=9,
        )
        errors.append(error)
        return False, errors

    # Check that at least one timeblock exists
    has_timeblock = bool(
        fields.get("morning_activities")
        or fields.get("afternoon_activities")
        or fields.get("evening_activities")
    )

    if not has_timeblock:
        error = ParsingError(
            error_type=ParsingErrorType.MISSING_ACTIVITY_LIST,
            message="Plan must have at least one timeblock (morning/afternoon/evening)",
            severity=8,
        )
        errors.append(error)
        return False, errors

    # Validate total energy matches sum of activities
    calculated_energy = sum(
        act.energy_cost
        for acts in [
            fields.get("morning_activities", []),
            fields.get("afternoon_activities", []),
            fields.get("evening_activities", []),
            fields.get("recovery_blocks", []),
        ]
        for act in acts
    )

    declared_energy = fields.get("total_energy_allocated", 0)
    if calculated_energy > 0 and calculated_energy != declared_energy:
        logger.warning(
            f"Energy mismatch: activities sum to {calculated_energy}, "
            f"but total_energy_allocated is {declared_energy}. Using calculated value."
        )
        fields["total_energy_allocated"] = calculated_energy

    return len([e for e in errors if e.severity >= 8]) == 0, errors
