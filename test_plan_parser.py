"""
Test Plan Parser Module

Tests for MODULE 8: Plan Parser

Tests parsing of raw LLM responses into structured plan candidates.

Usage:
    pytest test_plan_parser.py -v
"""

import sys
import json
import pytest
from datetime import datetime

sys.path.insert(0, "src/module_a/plan_parser")

from plan_parser_models import (
    ParseStatus,
    ParsingErrorType,
    ParsedPlanCandidate,
    ParsedDailyWellnessPlan,
)
from plan_parser import PlanParser
from plan_parser_utils import (
    extract_json_from_text,
    parse_json_to_dict,
    extract_plan_fields,
    validate_plan_structure,
)


# ============================================================================
# Test Data
# ============================================================================

VALID_LLM_RESPONSE = """
Here's a wellness plan based on your constraints:

```json
{
  "plan_id": "plan_demo_001",
  "morning_activities": [
    {"activity": "light stretching", "duration_minutes": 15, "energy_cost": 5},
    {"activity": "breakfast", "duration_minutes": 20, "energy_cost": 3}
  ],
  "afternoon_activities": [
    {"activity": "focused work", "duration_minutes": 120, "energy_cost": 20},
    {"activity": "short walk", "duration_minutes": 15, "energy_cost": 5}
  ],
  "evening_activities": [
    {"activity": "dinner prep", "duration_minutes": 30, "energy_cost": 5},
    {"activity": "light reading", "duration_minutes": 30, "energy_cost": 2}
  ],
  "recovery_blocks": [
    {"activity": "meditation", "duration_minutes": 20, "energy_cost": 2},
    {"activity": "rest", "duration_minutes": 60, "energy_cost": 0}
  ],
  "total_energy_allocated": 42,
  "plan_rationale": "This plan balances work and recovery with appropriate energy management."
}
```

This plan respects your constraints while providing a balanced daily schedule.
"""

MALFORMED_JSON_RESPONSE = """
The plan would be:
{
  "plan_id": "malformed",
  "morning_activities": [
    "this is not a dict",
    {}
  ],
  "total_energy_allocated": "not_an_int"
}
"""

NO_JSON_RESPONSE = """
I recommend the following activities throughout your day:
Morning: light stretching and breakfast
Afternoon: focused work
Evening: dinner and rest

This should help you manage your energy effectively.
"""


# ============================================================================
# Test JSON Extraction
# ============================================================================

class TestJsonExtraction:
    """Test JSON extraction from raw text."""

    def test_extract_json_from_code_block(self):
        """Extract JSON from markdown code block."""
        json_text, found = extract_json_from_text(VALID_LLM_RESPONSE)
        assert found, "Should find JSON"
        assert json_text is not None
        assert "plan_id" in json_text

    def test_extract_json_handles_no_json(self):
        """Handle responses with no JSON."""
        json_text, found = extract_json_from_text(NO_JSON_RESPONSE)
        assert not found, "Should not find JSON"
        assert json_text is None

    def test_extract_json_from_empty_text(self):
        """Handle empty input."""
        json_text, found = extract_json_from_text("")
        assert not found
        assert json_text is None


# ============================================================================
# Test Parser
# ============================================================================

class TestPlanParser:
    """Test main plan parser."""

    def test_parse_valid_response(self):
        """Parse valid LLM response."""
        parser = PlanParser()
        candidate = parser.parse_response(VALID_LLM_RESPONSE)

        assert candidate.candidate_id is not None
        assert candidate.parsing_status == ParseStatus.SUCCESS
        assert candidate.plan is not None
        assert candidate.get_error_count() == 0
        assert candidate.is_usable()

    def test_parsed_plan_structure(self):
        """Verify parsed plan structure."""
        parser = PlanParser()
        candidate = parser.parse_response(VALID_LLM_RESPONSE)

        assert candidate.plan is not None
        plan = candidate.plan

        assert len(plan.morning_activities) == 2
        assert len(plan.afternoon_activities) == 2
        assert len(plan.evening_activities) == 2
        assert len(plan.recovery_blocks) == 2
        assert plan.total_energy_allocated == 42

    def test_parse_malformed_json(self):
        """Handle malformed JSON gracefully."""
        parser = PlanParser()
        candidate = parser.parse_response(MALFORMED_JSON_RESPONSE)

        # Should still create a candidate, but with errors
        assert candidate.candidate_id is not None
        assert candidate.get_error_count() > 0
        # May still partially parse
        if candidate.plan:
            assert not candidate.is_usable()

    def test_parse_no_json(self):
        """Handle response with no JSON."""
        parser = PlanParser()
        candidate = parser.parse_response(NO_JSON_RESPONSE)

        assert candidate.parsing_status == ParseStatus.FAILED
        assert candidate.plan is None
        assert candidate.has_errors()
        assert not candidate.is_usable()

    def test_parse_response_has_metadata(self):
        """Verify parsing metadata."""
        parser = PlanParser()
        candidate = parser.parse_response(VALID_LLM_RESPONSE)

        assert candidate.created_at is not None
        assert candidate.parsing_time_ms >= 0
        assert candidate.raw_response == VALID_LLM_RESPONSE


# ============================================================================
# Test Validation
# ============================================================================

class TestPlanValidation:
    """Test plan structure validation."""

    def test_validate_structure_valid_plan(self):
        """Validate structure of valid plan."""
        parser = PlanParser()
        candidate = parser.parse_response(VALID_LLM_RESPONSE)

        is_valid, errors = candidate.plan.validate_structure()
        assert is_valid
        assert len(errors) == 0

    def test_validate_energy_calculation(self):
        """Verify energy calculations."""
        parser = PlanParser()
        candidate = parser.parse_response(VALID_LLM_RESPONSE)

        plan = candidate.plan
        calculated_energy = sum(
            act.energy_cost
            for acts in [
                plan.morning_activities,
                plan.afternoon_activities,
                plan.evening_activities,
                plan.recovery_blocks,
            ]
            for act in acts
        )

        assert calculated_energy == plan.total_energy_allocated


# ============================================================================
# Test Batch Parsing
# ============================================================================

class TestBatchParsing:
    """Test batch parsing."""

    def test_parse_multiple_responses(self):
        """Parse multiple responses."""
        parser = PlanParser()
        responses = {
            "candidate_1": VALID_LLM_RESPONSE,
            "candidate_2": NO_JSON_RESPONSE,
            "candidate_3": VALID_LLM_RESPONSE,
        }

        results = parser.parse_batch(responses)

        assert len(results) == 3
        assert results["candidate_1"].is_usable()
        assert not results["candidate_2"].is_usable()
        assert results["candidate_3"].is_usable()


# ============================================================================
# Integration Test
# ============================================================================

class TestIntegration:
    """Integration tests."""

    def test_full_parsing_workflow(self):
        """Test complete parsing workflow."""
        parser = PlanParser()

        # Parse response
        candidate = parser.parse_response(VALID_LLM_RESPONSE, "test_candidate_001")

        # Verify candidate
        assert candidate.candidate_id == "test_candidate_001"
        assert candidate.parsing_status == ParseStatus.SUCCESS
        assert candidate.is_usable()

        # Verify plan
        plan = candidate.plan
        assert plan is not None
        assert plan.get_activity_count() == 8
        assert plan.total_energy_allocated == 42

        # Verify structure
        is_valid, errors = plan.validate_structure()
        assert is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
