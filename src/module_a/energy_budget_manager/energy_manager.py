"""
Energy Budget Manager

Main orchestrator for energy budget calculations and management.
Integrates all components to build the complete energy budget state.

Module: Energy Budget Manager
Part of: Constraint-First Wellness Agent (Module A)
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from copy import deepcopy

from energy_models import (
    EnergyBudgetState,
    EnergyBudgetMetrics,
    ConstraintPressureLevel,
    TaskCategory,
)
from energy_utils import (
    get_base_energy_budget_by_life_mode,
    estimate_base_from_user_history,
    calculate_constraint_pressure_adjustment,
    apply_energy_dip_adjustments,
    apply_overload_adjustments,
    analyze_constraint_conflicts,
    calculate_recovery_factor,
    estimate_recovery_per_hour,
    build_standard_task_energy_costs,
    adjust_task_costs_for_context,
    validate_energy_budget,
    apply_safety_guardrails,
    format_energy_budget_summary,
    log_budget_calculation_trace,
    calculate_energy_breakdown,
    calculate_energy_volatility,
    interpret_energy_volatility,
)

logger = logging.getLogger(__name__)

MINIMUM_DAILY_BUDGET = 20


class EnergyBudgetManager:
    """
    Manages energy budget calculation and updates.
    
    Responsibilities:
    1. Calculate base energy from life mode
    2. Apply constraint adjustments
    3. Apply forecast adjustments
    4. Calculate recovery factor
    5. Build task energy cost model
    6. Generate complete energy budget
    """

    def __init__(self):
        """Initialize energy budget manager."""
        self.logger = logging.getLogger(__name__)

    def calculate_energy_budget(
        self,
        life_mode: str,
        constraints: List[Dict[str, Any]],
        constraint_score: float,
        constraint_pressure_level: str,
        forecast_data: Dict[str, Any],
        environment_context: Dict[str, Any],
        user_history: Dict[str, Any],
        system_flags: Dict[str, Any],
    ) -> EnergyBudgetState:
        """
        Calculate complete energy budget based on multiple factors.
        
        Args:
            life_mode: Current life mode (maintenance, growth, recovery, crisis)
            constraints: List of constraint dicts
            constraint_score: Overall constraint score (0-10)
            constraint_pressure_level: Pressure level (LOW, MODERATE, HIGH, CRITICAL)
            forecast_data: Dict containing predicted_energy_dips and related data
            environment_context: Dict with environment restrictions
            user_history: Dict with user performance history
            system_flags: System flags including overload_detected
            
        Returns:
            Complete EnergyBudgetState
        """
        logger.info(f"Calculating energy budget for life_mode={life_mode}")
        
        # Step 1: Calculate base energy
        base_budget = self._calculate_base_energy(life_mode, user_history)
        logger.debug(f"Step 1 - Base budget: {base_budget}")
        
        # Step 2: Apply constraint adjustments
        constraint_adjusted, constraint_reason = calculate_constraint_pressure_adjustment(
            constraint_score=constraint_score,
            pressure_level=constraint_pressure_level,
            base_budget=base_budget
        )
        logger.debug(f"Step 2 - Constraint adjusted: {constraint_adjusted} ({constraint_reason})")
        
        # Step 3: Apply forecast adjustments
        predicted_dips = forecast_data.get("predicted_energy_dips", [])
        forecast_adjusted, applied_dips = apply_energy_dip_adjustments(
            base_budget=constraint_adjusted,
            predicted_dips=predicted_dips
        )
        logger.debug(f"Step 3 - Forecast adjusted: {forecast_adjusted}")
        
        # Step 4: Apply overload adjustments
        overload_detected = system_flags.get("overload_detected", False)
        recent_overloads = self._estimate_recent_overloads(user_history)
        overload_adjusted, overload_reason = apply_overload_adjustments(
            budget=forecast_adjusted,
            overload_detected=overload_detected,
            recent_overload_count=recent_overloads
        )
        logger.debug(f"Step 4 - Overload adjusted: {overload_adjusted} ({overload_reason})")
        
        # Step 5: Apply safety guardrails
        final_budget = apply_safety_guardrails(overload_adjusted)
        logger.debug(f"Step 5 - Final budget (guardrailed): {final_budget}")
        
        # Calculate recovery factor
        recovery_factor = self._calculate_recovery_factor(
            constraints=constraints,
            life_mode=life_mode,
            user_history=user_history,
            recent_overloads=recent_overloads,
        )
        recovery_per_hour = estimate_recovery_per_hour(recovery_factor)
        
        # Build task energy cost model
        task_costs = build_standard_task_energy_costs()
        task_costs = adjust_task_costs_for_context(
            base_costs=task_costs,
            life_mode=life_mode,
            environment_restrictive=self._is_environment_restrictive(environment_context)
        )
        
        # Initialize allocated energy (0 until tasks are added)
        allocated_energy = 0
        remaining_energy = final_budget - allocated_energy
        
        # Create trace entry data
        trace_data = log_budget_calculation_trace(
            life_mode=life_mode,
            base_budget=base_budget,
            constraint_adjusted=constraint_adjusted,
            forecast_adjusted=forecast_adjusted,
            overload_adjusted=overload_adjusted,
            final_budget=final_budget,
        )
        
        # Calculate energy breakdown for debugging
        energy_breakdown = calculate_energy_breakdown(
            base_budget=base_budget,
            constraint_adjusted=constraint_adjusted,
            constraint_pressure_level=constraint_pressure_level,
            forecast_adjusted=forecast_adjusted,
            overload_adjusted=overload_adjusted,
            final_budget=final_budget,
        )
        
        # Calculate energy volatility indicator
        energy_volatility = calculate_energy_volatility(base_budget, final_budget)
        volatility_interpretation = interpret_energy_volatility(energy_volatility)
        
        logger.debug(
            f"Energy volatility: {energy_volatility:.3f} ({volatility_interpretation}) - "
            f"suggests {'simpler' if energy_volatility > 0.5 else 'standard'} planning"
        )
        
        # Build energy budget state
        energy_budget = EnergyBudgetState(
            daily_budget=final_budget,
            allocated_energy=allocated_energy,
            remaining_energy=remaining_energy,
            recovery_factor=recovery_factor,
            task_energy_costs=task_costs,
            buffer_energy=max(5, int(final_budget * 0.05)),
            estimated_recovery_per_hour=recovery_per_hour,
            predicted_energy_dips=applied_dips,
            overload_detected=overload_detected,
            constraint_pressure_applied=constraint_pressure_level,
            energy_volatility=energy_volatility,
            metadata={
                "life_mode": life_mode,
                "constraint_score": constraint_score,
                "recent_overload_count": recent_overloads,
                "calculation_trace": trace_data,
                "base_budget_source": "identified via life_mode",
                "energy_breakdown": energy_breakdown,
                "energy_volatility": round(energy_volatility, 3),
                "energy_volatility_level": volatility_interpretation,
            }
        )
        
        # Validate
        warnings = validate_energy_budget(final_budget, allocated_energy, remaining_energy)
        if warnings:
            logger.warning(f"Energy budget validation warnings: {warnings}")
            energy_budget.metadata["validation_warnings"] = warnings
        
        logger.info(f"Energy budget calculated: {format_energy_budget_summary(energy_budget.dict())}")
        
        return energy_budget

    def _calculate_base_energy(
        self,
        life_mode: str,
        user_history: Dict[str, Any]
    ) -> int:
        """
        Calculate base energy from life mode and history.
        
        Args:
            life_mode: Current life mode
            user_history: User history dict
            
        Returns:
            Base energy units
        """
        # Try historical estimate first
        historical_estimate = estimate_base_from_user_history(user_history)
        
        if historical_estimate:
            logger.debug(f"Using historical estimate for base energy: {historical_estimate}")
            return historical_estimate
        
        # Fall back to life mode
        base_from_mode = get_base_energy_budget_by_life_mode(life_mode)
        logger.debug(f"Using life_mode-based base energy: {base_from_mode}")
        return base_from_mode

    def _calculate_recovery_factor(
        self,
        constraints: List[Dict[str, Any]],
        life_mode: str,
        user_history: Dict[str, Any],
        recent_overloads: int,
    ) -> float:
        """
        Calculate recovery factor from constraints and context.
        
        Args:
            constraints: List of constraints
            life_mode: Current life mode
            user_history: User history
            recent_overloads: Count of recent overloads
            
        Returns:
            Recovery factor (0.3-1.0)
        """
        # Extract sleep and physical constraints
        sleep_constraint = None
        physical_constraints = []
        
        for constraint in constraints:
            category = constraint.get("category", "").lower()
            if category == "sleep":
                sleep_constraint = constraint
            elif category == "physical":
                physical_constraints.append(constraint)
        
        recovery_factor = calculate_recovery_factor(
            sleep_constraint=sleep_constraint,
            physical_constraints=physical_constraints,
            recent_overload_periods=recent_overloads,
            user_history=user_history,
        )
        
        return recovery_factor

    def _estimate_recent_overloads(self, user_history: Dict[str, Any]) -> int:
        """
        Estimate number of recent overload periods.
        
        Args:
            user_history: User history dict
            
        Returns:
            Count of recent overloads (0+)
        """
        # Check if history has overload tracking
        if "recent_overload_count" in user_history:
            return user_history.get("recent_overload_count", 0)
        
        # Heuristic: if completion rate is low, likely experiencing overload
        plans_generated = user_history.get("total_plans_generated", 1)
        plans_completed = user_history.get("plans_completed", 0)
        
        if plans_generated == 0:
            return 0
        
        completion_rate = plans_completed / plans_generated
        if completion_rate < 0.4:
            return 2  # Likely experiencing overload
        elif completion_rate < 0.6:
            return 1  # Some overload
        
        return 0  # No detected overload

    def _is_environment_restrictive(self, environment_context: Dict[str, Any]) -> bool:
        """
        Determine if environment is restrictive.
        
        Args:
            environment_context: Environment context dict
            
        Returns:
            True if restrictions present
        """
        restrictions = [
            environment_context.get("indoor_only", False),
            environment_context.get("small_space", False),
            environment_context.get("silent_required", False),
            environment_context.get("shared_room", False),
        ]
        
        return any(restrictions)

    def allocate_task(
        self,
        energy_budget: EnergyBudgetState,
        task_name: str,
        task_category: str,
    ) -> Tuple[EnergyBudgetState, bool]:
        """
        Attempt to allocate energy for a task.
        
        Args:
            energy_budget: Current energy budget state
            task_name: Name/ID of task
            task_category: Category of task (must be in task_energy_costs)
            
        Returns:
            Tuple of (updated_budget, success)
        """
        task_cost = energy_budget.task_energy_costs.get(task_category, 0)
        
        if task_cost <= 0:
            logger.warning(f"Task category '{task_category}' not found or has invalid cost")
            return energy_budget, False
        
        if task_cost > energy_budget.remaining_energy:
            logger.warning(
                f"Insufficient energy for task '{task_name}' "
                f"(need {task_cost}, have {energy_budget.remaining_energy})"
            )
            return energy_budget, False
        
        # Allocate
        updated_budget = energy_budget.copy(deep=True)
        updated_budget.allocated_energy += task_cost
        updated_budget.remaining_energy -= task_cost
        
        logger.debug(
            f"Task '{task_name}' allocated {task_cost} units. "
            f"Remaining: {updated_budget.remaining_energy}"
        )
        
        return updated_budget, True

    def apply_recovery(
        self,
        energy_budget: EnergyBudgetState,
        recovery_hours: float,
    ) -> EnergyBudgetState:
        """
        Apply recovery over specified hours.
        
        Args:
            energy_budget: Current budget
            recovery_hours: Hours of recovery
            
        Returns:
            Updated budget with recovered energy
        """
        recovery_units = int(energy_budget.estimated_recovery_per_hour * recovery_hours)
        
        updated_budget = energy_budget.copy(deep=True)
        updated_budget.allocated_energy = max(0, updated_budget.allocated_energy - recovery_units)
        updated_budget.remaining_energy = min(
            updated_budget.daily_budget,
            updated_budget.remaining_energy + recovery_units
        )
        
        logger.debug(f"Recovery applied: {recovery_units} units over {recovery_hours} hours")
        
        return updated_budget

    def generate_metrics(self, energy_budget: EnergyBudgetState) -> EnergyBudgetMetrics:
        """
        Generate metrics from energy budget.
        
        Args:
            energy_budget: Energy budget state
            
        Returns:
            Energy budget metrics
        """
        return EnergyBudgetMetrics(
            daily_budget=energy_budget.daily_budget,
            allocated_energy=energy_budget.allocated_energy,
            remaining_energy=energy_budget.remaining_energy,
            buffer_energy=energy_budget.buffer_energy,
            recovery_capacity=energy_budget.recovery_factor,
            energy_dips_detected=energy_budget.predicted_energy_dips,
        )
