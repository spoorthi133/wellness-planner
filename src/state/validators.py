"""
State Validation Module

Validates AgentState schema and enforces data integrity including all Corrections.
Checks for missing fields, type correctness, value ranges, and new model fields.

Module: State Model & Persistence Layer
Part of: Constraint-First Wellness Agent
"""

from typing import Dict, Any, List, Tuple, Optional
from pydantic import ValidationError
from datetime import datetime
from .agent_state import (
    AgentState, Constraint, EnergyBudget, EnvironmentContext,
    Forecast, Plan, Insight, UserHistory, SystemFlags
)


class StateValidationError(ValueError):
    """Custom exception for state validation failures."""
    pass


class StateValidator:
    """
    Validates AgentState instances and detects issues.
    """

    # Required top-level fields
    REQUIRED_FIELDS = {
        'user_id': str,
        'constraints': list,
        'energy_budget': (dict, EnergyBudget),
        'environment_context': (dict, EnvironmentContext),
        'life_mode': str,
        'motivation_style': str,
        'user_history': (dict, UserHistory),
        'system_flags': (dict, SystemFlags),
    }

    # Optional fields with defaults
    OPTIONAL_FIELDS = {
        'session_id': str,
        'forecast_data': (dict, Forecast),
        'plan': (dict, type(None), Plan),
        'recent_insights': list,
        'last_updated': datetime,
        'version': int,
        'state_version': int,
        'last_node_executed': (str, type(None)),
        'execution_trace': list,
    }

    @staticmethod
    def validate_state(state: AgentState) -> Tuple[bool, List[str]]:
        """
        Validate a complete AgentState instance.
        
        Args:
            state: AgentState to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        for field, field_type in StateValidator.REQUIRED_FIELDS.items():
            if not hasattr(state, field):
                errors.append(f"Missing required field: {field}")
            else:
                value = getattr(state, field)
                if value is None:
                    errors.append(f"Required field cannot be None: {field}")

        # Check field types
        type_errors = StateValidator._check_field_types(state)
        errors.extend(type_errors)

        # Check value ranges
        range_errors = StateValidator._check_value_ranges(state)
        errors.extend(range_errors)

        # Check constraints validity
        constraint_errors = StateValidator._validate_constraints(state.constraints)
        errors.extend(constraint_errors)

        # Check energy budget
        budget_errors = StateValidator._validate_energy_budget(state.energy_budget)
        errors.extend(budget_errors)

        # Correction 4: Validate Forecast (expanded fields)
        forecast_errors = StateValidator._validate_forecast(state.forecast_data)
        errors.extend(forecast_errors)

        # Correction 6: Validate EnvironmentContext
        env_errors = StateValidator._validate_environment_context(state.environment_context)
        errors.extend(env_errors)

        # Correction 7: Validate SystemFlags
        flags_errors = StateValidator._validate_system_flags(state.system_flags)
        errors.extend(flags_errors)

        return len(errors) == 0, errors

    @staticmethod
    def _check_field_types(state: AgentState) -> List[str]:
        """Check that fields have correct types."""
        errors = []

        type_checks = {
            'user_id': str,
            'session_id': str,
            'constraints': list,
            'life_mode': str,
            'motivation_style': str,
            'recent_insights': list,
            'version': int,
        }

        for field, expected_type in type_checks.items():
            if hasattr(state, field):
                value = getattr(state, field)
                if value is not None and not isinstance(value, expected_type):
                    errors.append(
                        f"Field '{field}' has incorrect type. "
                        f"Expected {expected_type.__name__}, got {type(value).__name__}"
                    )

        return errors

    @staticmethod
    def _check_value_ranges(state: AgentState) -> List[str]:
        """Check that numeric values are within acceptable ranges."""
        errors = []

        # Check energy budget percentages
        if state.energy_budget:
            budget = state.energy_budget
            total = budget.morning + budget.afternoon + budget.evening + budget.contingency
            if total > budget.daily_total + 1:  # Allow 1 unit rounding error
                errors.append(
                    f"Energy budget components sum to {total}, exceeds daily_total {budget.daily_total}"
                )

        # Check version
        if state.version < 1:
            errors.append("Version must be >= 1")

        # Check life_mode is valid
        valid_modes = ["maintenance", "growth", "recovery", "crisis"]
        if state.life_mode not in valid_modes:
            errors.append(f"Invalid life_mode: {state.life_mode}")

        # Check motivation_style is valid
        valid_styles = [
            "reward_focused", "loss_aversion", 
            "progress_tracking", "social_accountability"
        ]
        if state.motivation_style not in valid_styles:
            errors.append(f"Invalid motivation_style: {state.motivation_style}")

        return errors

    @staticmethod
    def _validate_constraints(constraints: List[Constraint]) -> List[str]:
        """Validate constraint list."""
        errors = []

        if not isinstance(constraints, list):
            errors.append("Constraints must be a list")
            return errors

        for i, constraint in enumerate(constraints):
            if isinstance(constraint, dict):
                try:
                    Constraint(**constraint)
                except ValidationError as e:
                    errors.append(f"Constraint {i} validation failed: {str(e)}")
            elif not isinstance(constraint, Constraint):
                errors.append(f"Constraint {i} is not a valid Constraint object")
            else:
                # Validate severity range
                if not (1 <= constraint.severity <= 10):
                    errors.append(f"Constraint {i} severity must be 1-10")

        return errors

    @staticmethod
    def _validate_forecast(forecast: Forecast) -> List[str]:
        """Validate forecast fields (Correction 4)."""
        errors = []

        if forecast is None:
            errors.append("Forecast cannot be None")
            return errors

        # Validate confidence score
        if not (0 <= forecast.forecast_confidence <= 1):
            errors.append(f"Forecast confidence must be 0-1, got {forecast.forecast_confidence}")

        # Validate window days
        if forecast.forecast_window_days <= 0:
            errors.append(f"Forecast window days must be > 0, got {forecast.forecast_window_days}")

        # Validate confidence_score (original field)
        if not (0 <= forecast.confidence_score <= 1):
            errors.append(f"Forecast confidence_score must be 0-1, got {forecast.confidence_score}")

        return errors

    @staticmethod
    def _validate_environment_context(context: EnvironmentContext) -> List[str]:
        """Validate environment context fields (Correction 6)."""
        errors = []

        if context is None:
            errors.append("Environment context cannot be None")
            return errors

        # Validate boolean fields
        if not isinstance(context.indoor_only, bool):
            errors.append(f"indoor_only must be boolean")
        if not isinstance(context.small_space, bool):
            errors.append(f"small_space must be boolean")
        if not isinstance(context.silent_required, bool):
            errors.append(f"silent_required must be boolean")
        if not isinstance(context.shared_room, bool):
            errors.append(f"shared_room must be boolean")

        # Validate equipment_available list
        if not isinstance(context.equipment_available, list):
            errors.append(f"equipment_available must be a list")

        return errors

    @staticmethod
    def _validate_system_flags(flags: SystemFlags) -> List[str]:
        """Validate system flags fields (Correction 7)."""
        errors = []

        if flags is None:
            errors.append("System flags cannot be None")
            return errors

        # Validate all boolean fields
        boolean_fields = [
            'is_onboarded', 'requires_replan', 'emergency_mode', 'data_sync_pending',
            'reentry_required', 'overload_detected', 'simulation_mode', 'plan_locked',
            'forecast_stale'
        ]

        for field in boolean_fields:
            if hasattr(flags, field):
                value = getattr(flags, field)
                if not isinstance(value, bool):
                    errors.append(f"System flag '{field}' must be boolean, got {type(value).__name__}")

        return errors

    @staticmethod
    def _validate_energy_budget(budget: EnergyBudget) -> List[str]:
        """Validate energy budget allocation (Correction 5, 10)."""
        errors = []

        if budget is None:
            errors.append("Energy budget cannot be None")
            return errors

        # Check all percentages are non-negative
        if budget.daily_total < 0:
            errors.append("Energy budget daily_total cannot be negative")
        if budget.morning < 0:
            errors.append("Energy budget morning cannot be negative")
        if budget.afternoon < 0:
            errors.append("Energy budget afternoon cannot be negative")
        if budget.evening < 0:
            errors.append("Energy budget evening cannot be negative")
        if budget.contingency < 0:
            errors.append("Energy budget contingency cannot be negative")

        # Correction 5 & 10: Validate task-level allocation fields
        if budget.daily_budget < 0:
            errors.append("Energy budget daily_budget cannot be negative")

        if budget.allocated_energy < 0:
            errors.append("Energy budget allocated_energy cannot be negative")

        if budget.allocated_energy > budget.daily_budget:
            errors.append(
                f"Energy budget allocated_energy ({budget.allocated_energy}) "
                f"cannot exceed daily_budget ({budget.daily_budget})"
            )

        if budget.remaining_energy < 0:
            errors.append("Energy budget remaining_energy cannot be negative")

        # Validate remaining = daily - allocated
        expected_remaining = budget.daily_budget - budget.allocated_energy
        if budget.remaining_energy != expected_remaining:
            errors.append(
                f"Energy budget remaining_energy ({budget.remaining_energy}) "
                f"should be {expected_remaining} (daily_budget - allocated_energy)"
            )

        # Validate recovery factor
        if not (0 < budget.recovery_factor <= 1):
            errors.append(f"Energy budget recovery_factor must be 0 < x <= 1, got {budget.recovery_factor}")

        return errors

    @staticmethod
    def validate_state_dict(state_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a dictionary representation before converting to AgentState.
        
        Args:
            state_dict: Dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not isinstance(state_dict, dict):
            return False, ["State must be a dictionary"]

        # Check required keys
        if 'user_id' not in state_dict:
            errors.append("Missing required field: user_id")

        if state_dict.get('user_id') is None or not state_dict.get('user_id').strip():
            errors.append("user_id cannot be empty")

        # Try to construct AgentState to catch Pydantic errors
        try:
            state = AgentState(**state_dict)
            return StateValidator.validate_state(state)
        except ValidationError as e:
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"Field '{field}': {msg}")

        return len(errors) == 0, errors

    @staticmethod
    def assert_valid_state(state: AgentState) -> None:
        """
        Assert that state is valid, raise StateValidationError if not.
        
        Args:
            state: AgentState to validate
            
        Raises:
            StateValidationError: If state is invalid
        """
        is_valid, errors = StateValidator.validate_state(state)
        if not is_valid:
            error_msg = "State validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise StateValidationError(error_msg)

    @staticmethod
    def get_validation_report(state: AgentState) -> str:
        """
        Get a detailed validation report.
        
        Args:
            state: AgentState to validate
            
        Returns:
            Formatted validation report
        """
        is_valid, errors = StateValidator.validate_state(state)

        report = f"{'='*60}\n"
        report += f"STATE VALIDATION REPORT\n"
        report += f"{'='*60}\n"
        report += f"User ID: {state.user_id}\n"
        report += f"Valid: {'✓ YES' if is_valid else '✗ NO'}\n"
        report += f"Errors: {len(errors)}\n\n"

        if errors:
            report += "ISSUES FOUND:\n"
            for i, error in enumerate(errors, 1):
                report += f"  {i}. {error}\n"
        else:
            report += "No issues found.\n"

        report += f"\n{'='*60}\n"
        return report


def validate_state(state: AgentState) -> bool:
    """
    Quick validation function.
    
    Args:
        state: AgentState to validate
        
    Returns:
        True if valid, False otherwise
    """
    is_valid, _ = StateValidator.validate_state(state)
    return is_valid


def assert_valid(state: AgentState) -> None:
    """
    Assert state is valid or raise error.
    
    Args:
        state: AgentState to validate
        
    Raises:
        StateValidationError: If invalid
    """
    StateValidator.assert_valid_state(state)
