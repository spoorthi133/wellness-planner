"""
Energy Budget Manager Utilities

Provides calculation and helper functions for energy budget management.
Handles conversions, validations, and specific computations.

Module: Energy Budget Manager
Part of: Constraint-First Wellness Agent (Module A)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from energy_models import (
    ConstraintPressureLevel,
    EnergyDipSeverity,
    TaskCategory,
    BaseEnergyBudget,
    TaskEnergyCost,
    ConstraintAdjustment,
    ForecastAdjustment,
)

logger = logging.getLogger(__name__)

# Constants
MINIMUM_DAILY_BUDGET = 20
MAXIMUM_DAILY_BUDGET = 200
DEFAULT_BUFFER_PERCENTAGE = 0.05  # 5% buffer
CRITICAL_ENERGY_THRESHOLD = 15  # Alert when below this


# ============================================================================
# Base Energy Budget Calculations
# ============================================================================

def get_base_energy_budget_by_life_mode(life_mode: str) -> int:
    """
    Calculate base daily energy budget based on life mode.
    
    Args:
        life_mode: One of "maintenance", "growth", "recovery", "crisis"
        
    Returns:
        Base energy units (20-200)
    """
    base_budgets = {
        "maintenance": 100,
        "growth": 110,
        "recovery": 70,
        "crisis": 50,
    }
    
    budget = base_budgets.get(life_mode, 100)
    return max(MINIMUM_DAILY_BUDGET, min(MAXIMUM_DAILY_BUDGET, budget))


def estimate_base_from_user_history(user_history: Dict[str, Any]) -> Optional[int]:
    """
    Estimate baseline energy from user's historical performance.
    
    Args:
        user_history: User history dict with performance metrics
        
    Returns:
        Estimated base energy, or None if insufficient data
    """
    # Track completion rate and days active
    total_plans = user_history.get("total_plans_generated", 0)
    completed_plans = user_history.get("plans_completed", 0)
    days_active = user_history.get("days_active", 0)
    
    if total_plans == 0 or days_active == 0:
        return None
    
    completion_rate = completed_plans / total_plans
    
    # Higher completion = higher baseline capacity assumption
    if completion_rate > 0.9:
        return 120
    elif completion_rate > 0.7:
        return 110
    elif completion_rate > 0.5:
        return 100
    else:
        return 85


# ============================================================================
# Constraint-Based Adjustments
# ============================================================================

def calculate_constraint_pressure_adjustment(
    constraint_score: float,
    pressure_level: str,
    base_budget: int
) -> Tuple[int, str]:
    """
    Calculate energy reduction based on constraint pressure.
    
    Args:
        constraint_score: Score from constraint analyzer (0-10)
        pressure_level: "LOW", "MODERATE", "HIGH", "CRITICAL"
        base_budget: Base energy before adjustment
        
    Returns:
        Tuple of (adjusted_budget, reason)
    """
    pressure_map = {
        "LOW": (0.00, "Low constraint pressure - no reduction"),
        "MODERATE": (0.10, "Moderate constraint pressure - 10% reduction"),
        "HIGH": (0.25, "High constraint pressure - 25% reduction"),
        "CRITICAL": (0.40, "Critical constraint pressure - 40% reduction"),
    }
    
    reduction_pct, reason = pressure_map.get(pressure_level, (0.0, "Unknown pressure - no change"))
    adjusted = int(base_budget * (1 - reduction_pct))
    adjusted = max(MINIMUM_DAILY_BUDGET, adjusted)
    
    logger.debug(f"Constraint adjustment: {base_budget} → {adjusted} ({reason})")
    
    return adjusted, reason


def analyze_constraint_conflicts(
    constraints: List[Dict[str, Any]],
    conflict_density: int = 0
) -> Dict[str, Any]:
    """
    Analyze conflicts between constraints to identify energy drains.
    
    Args:
        constraints: List of constraint dicts
        conflict_density: Number of detected conflicts
        
    Returns:
        Dict with conflict analysis
    """
    analysis = {
        "total_constraints": len(constraints),
        "conflict_count": conflict_density,
        "conflict_severity": "LOW",
        "recommended_energy_reduction": 0,
    }
    
    conflict_ratio = conflict_density / max(len(constraints), 1)
    
    if conflict_ratio > 0.5:
        analysis["conflict_severity"] = "CRITICAL"
        analysis["recommended_energy_reduction"] = 30
    elif conflict_ratio > 0.3:
        analysis["conflict_severity"] = "HIGH"
        analysis["recommended_energy_reduction"] = 20
    elif conflict_ratio > 0.15:
        analysis["conflict_severity"] = "MODERATE"
        analysis["recommended_energy_reduction"] = 10
    
    return analysis


# ============================================================================
# Forecast-Based Adjustments
# ============================================================================

def apply_energy_dip_adjustments(
    base_budget: int,
    predicted_dips: List[Dict[str, Any]]
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Reduce energy budget based on predicted energy dips.
    
    Args:
        base_budget: Base budget before forecast adjustments
        predicted_dips: List of predicted dip dicts (from forecast engine)
        
    Returns:
        Tuple of (adjusted_budget, applied_adjustments)
    """
    total_reduction = 0
    applied_adjustments = []
    
    dip_severity_map = {
        "low": 5,
        "moderate": 10,
        "high": 20,
        "critical": 30,
    }
    
    for dip in predicted_dips:
        severity = dip.get("severity", "low").lower()
        confidence = dip.get("confidence", 0.5)
        
        # Adjust reduction by confidence
        base_reduction = dip_severity_map.get(severity, 5)
        confidence_adjusted = int(base_reduction * confidence)
        
        total_reduction += confidence_adjusted
        
        applied_adjustments.append({
            "cause": dip.get("primary_cause", "unknown"),
            "severity": severity,
            "confidence": confidence,
            "energy_reduction": confidence_adjusted,
            "day_offset": dip.get("day_offset", 0),
        })
    
    adjusted_budget = max(
        MINIMUM_DAILY_BUDGET,
        base_budget - total_reduction
    )
    
    logger.debug(f"Forecast adjustments: {base_budget} → {adjusted_budget} (reduction: {total_reduction})")
    
    return adjusted_budget, applied_adjustments


def apply_overload_adjustments(
    budget: int,
    overload_detected: bool,
    recent_overload_count: int = 0
) -> Tuple[int, str]:
    """
    Further reduce budget if recent overload detected.
    
    Args:
        budget: Current budget
        overload_detected: Whether system detected overload
        recent_overload_count: Count of recent overload periods
        
    Returns:
        Tuple of (adjusted_budget, reason)
    """
    if not overload_detected and recent_overload_count == 0:
        return budget, "No recent overload detected"
    
    # Stack reductions for multiple overloads
    reduction_pct = 0.15 + (recent_overload_count * 0.10)
    reduction_pct = min(0.40, reduction_pct)  # Cap at 40%
    
    adjusted = int(budget * (1 - reduction_pct))
    adjusted = max(MINIMUM_DAILY_BUDGET, adjusted)
    
    reason = f"Recent overload protection: {recent_overload_count} overloads detected"
    logger.debug(f"Overload adjustment: {budget} → {adjusted}")
    
    return adjusted, reason


# ============================================================================
# Energy Breakdown & Volatility
# ============================================================================

def calculate_energy_breakdown(
    base_budget: int,
    constraint_adjusted: int,
    constraint_pressure_level: str,
    forecast_adjusted: int,
    overload_adjusted: int,
    final_budget: int,
) -> Dict[str, Any]:
    """
    Calculate detailed energy breakdown at each step.
    
    Shows exactly how much energy was removed at each stage for debugging.
    
    Args:
        base_budget: Starting budget from life mode
        constraint_adjusted: After constraint reduction
        constraint_pressure_level: Pressure level applied
        forecast_adjusted: After forecast reduction
        overload_adjusted: After overload reduction
        final_budget: Final budget after all adjustments
        
    Returns:
        Dict with breakdown information
    """
    constraint_adj = base_budget - constraint_adjusted
    forecast_adj = constraint_adjusted - forecast_adjusted
    overload_adj = forecast_adjusted - overload_adjusted
    total_adj = base_budget - final_budget
    
    breakdown = {
        "base_budget": base_budget,
        "constraint_adjustment": constraint_adj,
        "constraint_pressure_level": constraint_pressure_level,
        "forecast_adjustment": forecast_adj,
        "overload_adjustment": overload_adj,
        "final_budget": final_budget,
        "total_adjustments": total_adj,
    }
    
    logger.debug(f"Energy breakdown: {breakdown}")
    return breakdown


def calculate_energy_volatility(base_budget: int, final_budget: int) -> float:
    """
    Calculate energy volatility indicator.
    
    Volatility = total_adjustments / base_budget
    
    Range: 0.0 (stable, no adjustments) to ~1.0 (highly volatile)
    
    Example:
        base = 100, final = 60 → volatility = 0.40
        base = 100, final = 95 → volatility = 0.05
        base = 100, final = 20 → volatility = 0.80
    
    Usage:
        High volatility (>0.5) → generate simpler plans
        Low volatility (<0.2) → can generate complex plans
    
    Args:
        base_budget: Starting budget from life mode
        final_budget: Final budget after all adjustments
        
    Returns:
        Volatility ratio (0.0-1.0+)
    """
    if base_budget <= 0:
        return 0.0
    
    total_adjustments = base_budget - final_budget
    volatility = total_adjustments / base_budget
    
    # Clamp to 0-1 range (can go above 1 if guardrails kick in heavily)
    volatility = max(0.0, min(1.0, volatility))
    
    logger.debug(f"Energy volatility: {volatility:.2f} (base={base_budget}, final={final_budget})")
    
    return volatility


def interpret_energy_volatility(volatility: float) -> str:
    """
    Interpret volatility level for human-readable output.
    
    Args:
        volatility: Energy volatility score (0.0-1.0)
        
    Returns:
        Interpretation string
    """
    if volatility < 0.1:
        return "VERY_STABLE"
    elif volatility < 0.25:
        return "STABLE"
    elif volatility < 0.5:
        return "MODERATE"
    elif volatility < 0.75:
        return "VOLATILE"
    else:
        return "HIGHLY_VOLATILE"


# ============================================================================
# Recovery Factor Calculations
# ============================================================================

def calculate_recovery_factor(
    sleep_constraint: Optional[Dict[str, Any]] = None,
    physical_constraints: Optional[List[Dict[str, Any]]] = None,
    recent_overload_periods: int = 0,
    user_history: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Calculate recovery factor (0.3-1.0) indicating speed of energy recovery.
    
    Args:
        sleep_constraint: Sleep-related constraint if exists
        physical_constraints: List of physical constraints
        recent_overload_periods: Count of recent overloads
        user_history: User historical data
        
    Returns:
        Recovery factor (0.3-1.0)
    """
    recovery_factor = 0.8  # Baseline
    
    # Sleep constraints reduce recovery
    if sleep_constraint:
        severity = sleep_constraint.get("severity", 5)
        if severity >= 8:
            recovery_factor -= 0.25
        elif severity >= 6:
            recovery_factor -= 0.15
        elif severity >= 4:
            recovery_factor -= 0.05
    
    # Physical constraints reduce recovery
    if physical_constraints:
        for constraint in physical_constraints:
            severity = constraint.get("severity", 5)
            if severity >= 8:
                recovery_factor -= 0.20
            elif severity >= 6:
                recovery_factor -= 0.10
    
    # Recent overload periods further reduce recovery
    if recent_overload_periods > 0:
        reduction = min(0.30, recent_overload_periods * 0.15)
        recovery_factor -= reduction
    
    # Clamp to valid range
    return max(0.3, min(1.0, recovery_factor))


def estimate_recovery_per_hour(recovery_factor: float) -> float:
    """
    Estimate energy units recovered per hour of rest.
    
    Args:
        recovery_factor: Recovery factor (0.3-1.0)
        
    Returns:
        Energy units per hour (0.5-2.0)
    """
    # Maps recovery_factor to units per hour
    # 0.3 → 0.5 units/hour (poor recovery)
    # 1.0 → 2.0 units/hour (excellent recovery)
    return 0.5 + (recovery_factor * 1.5)


# ============================================================================
# Task Energy Cost Model
# ============================================================================

def build_standard_task_energy_costs() -> Dict[str, int]:
    """
    Build standard energy cost mapping for common tasks.
    
    Returns:
        Dict mapping task names to energy units required
    """
    return {
        "light_movement": 5,
        "focus_work": 15,
        "exercise": 20,
        "deep_work": 25,
        "social_activity": 10,
        "creative_work": 18,
        "care_giving": 12,
        "administrative": 8,
        "recovery": -10,  # Recovers energy
        "leisure": 5,
    }


def adjust_task_costs_for_context(
    base_costs: Dict[str, int],
    life_mode: str,
    environment_restrictive: bool = False,
) -> Dict[str, int]:
    """
    Adjust task energy costs based on context.
    
    Args:
        base_costs: Base cost mapping
        life_mode: Current life mode
        environment_restrictive: Whether environment limits activities
        
    Returns:
        Adjusted cost mapping
    """
    adjusted_costs = base_costs.copy()
    
    # Life mode adjustments
    if life_mode == "recovery":
        # Make high-energy tasks more expensive
        for key in ["deep_work", "exercise", "social_activity"]:
            if key in adjusted_costs:
                adjusted_costs[key] = int(adjusted_costs[key] * 1.5)
    elif life_mode == "crisis":
        # Penalize all activities heavily
        for key in adjusted_costs:
            if adjusted_costs[key] > 0:
                adjusted_costs[key] = int(adjusted_costs[key] * 1.3)
    
    # Environment adjustments
    if environment_restrictive:
        # Limited options make available activities more important/expensive
        adjusted_costs["light_movement"] = int(adjusted_costs["light_movement"] * 1.2)
        adjusted_costs["focus_work"] = int(adjusted_costs["focus_work"] * 1.1)
    
    return adjusted_costs


def estimate_daily_allocations(
    task_costs: Dict[str, int],
    total_budget: int,
    buffer_pct: float = 0.1
) -> Dict[str, int]:
    """
    Estimate how much energy can be allocated to each task type.
    
    Args:
        task_costs: Map of task→cost
        total_budget: Daily budget
        buffer_pct: Percentage to reserve as buffer
        
    Returns:
        Dict of task→allocated_energy
    """
    buffer = int(total_budget * buffer_pct)
    available = total_budget - buffer
    
    allocations = {}
    for task, base_cost in task_costs.items():
        if base_cost > 0:
            max_allowable = min(base_cost * 2, available // 3)
            allocations[task] = max(0, max_allowable)
    
    return allocations


# ============================================================================
# Validation & Boundary Checks
# ============================================================================

def validate_energy_budget(daily_budget: int, allocated: int, remaining: int) -> List[str]:
    """
    Validate energy budget numbers for consistency.
    
    Args:
        daily_budget: Total daily budget
        allocated: Allocated energy
        remaining: Remaining energy
        
    Returns:
        List of warning/error messages (empty if valid)
    """
    issues = []
    
    if daily_budget < MINIMUM_DAILY_BUDGET:
        issues.append(f"Budget ({daily_budget}) below minimum ({MINIMUM_DAILY_BUDGET})")
    
    if daily_budget > MAXIMUM_DAILY_BUDGET:
        issues.append(f"Budget ({daily_budget}) exceeds maximum ({MAXIMUM_DAILY_BUDGET})")
    
    if allocated > daily_budget:
        issues.append(f"Allocated ({allocated}) exceeds budget ({daily_budget})")
    
    if remaining < 0:
        issues.append(f"Remaining energy ({remaining}) is negative")
    
    calculated_remaining = daily_budget - allocated
    if remaining != calculated_remaining:
        issues.append(f"Remaining mismatch: {remaining} != {daily_budget} - {allocated}")
    
    return issues


def apply_safety_guardrails(budget: int) -> int:
    """
    Ensure budget respects safety boundaries.
    
    Args:
        budget: Proposed budget
        
    Returns:
        Guardrailed budget
    """
    return max(MINIMUM_DAILY_BUDGET, min(MAXIMUM_DAILY_BUDGET, budget))


# ============================================================================
# Debug & Logging Utilities
# ============================================================================

def format_energy_budget_summary(budget_dict: Dict[str, Any]) -> str:
    """
    Format energy budget for logging/display.
    
    Args:
        budget_dict: Energy budget dict
        
    Returns:
        Formatted string
    """
    return (
        f"Budget: {budget_dict.get('daily_budget', 0)} units | "
        f"Allocated: {budget_dict.get('allocated_energy', 0)} | "
        f"Remaining: {budget_dict.get('remaining_energy', 0)} | "
        f"Recovery: {budget_dict.get('recovery_factor', 0.8):.2f}"
    )


def log_budget_calculation_trace(
    life_mode: str,
    base_budget: int,
    constraint_adjusted: int,
    forecast_adjusted: int,
    overload_adjusted: int,
    final_budget: int,
) -> Dict[str, Any]:
    """
    Create a detailed trace of budget calculation steps.
    
    Args:
        life_mode: Starting life mode
        base_budget: After life mode calc
        constraint_adjusted: After constraint adjustment
        forecast_adjusted: After forecast adjustment
        overload_adjusted: After overload adjustment
        final_budget: Final calculated budget
        
    Returns:
        Trace dict for logging
    """
    return {
        "life_mode": life_mode,
        "step1_base": base_budget,
        "step2_constraint_adjusted": constraint_adjusted,
        "step3_forecast_adjusted": forecast_adjusted,
        "step4_overload_adjusted": overload_adjusted,
        "step5_final": final_budget,
        "total_reduction": base_budget - final_budget,
    }
