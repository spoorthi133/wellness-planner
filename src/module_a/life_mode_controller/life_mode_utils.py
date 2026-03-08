"""
Life Mode Controller Utilities

Core algorithms for life mode detection, resolution, and scoring.
Implements detection rules, priority resolution, confidence calculation, and explanations.

Module: Life Mode Controller
Part of: Constraint-First Wellness Agent (Module A)
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime

from life_mode_models import (
    LifeModeName,
    ModeDetectionSignal,
    ModeProfile,
    PlanComplexity,
    ActivityIntensity,
    RecoveryPriority,
    LifeModeDetectionResult,
    LifeModeContext,
    LifeModeResolution,
    ModePriorityMap,
    ConfidenceFactors,
)

logger = logging.getLogger(__name__)


# ============================================================================
# MODE PRIORITY MAP (Hard-coded priority hierarchy)
# ============================================================================

def get_mode_priority_map() -> ModePriorityMap:
    """
    Returns the priority map for life mode conflict resolution.
    
    Priority hierarchy (highest to lowest):
    1. crisis
    2. recovery
    3. exam_mode
    4. work_crunch_mode
    5. travel_mode
    6. social_week_mode
    7. growth
    8. maintenance
    
    Returns:
        ModePriorityMap with priority ordering
    """
    priority_order = [
        LifeModeName.CRISIS,
        LifeModeName.RECOVERY,
        LifeModeName.EXAM_MODE,
        LifeModeName.WORK_CRUNCH_MODE,
        LifeModeName.TRAVEL_MODE,
        LifeModeName.SOCIAL_WEEK_MODE,
        LifeModeName.GROWTH,
        LifeModeName.MAINTENANCE,
    ]
    
    priority_values = {mode.value: idx for idx, mode in enumerate(priority_order)}
    
    return ModePriorityMap(
        priority_order=priority_order,
        priority_values=priority_values,
    )


# ============================================================================
# MODE PROFILES (Behavior configuration for each mode)
# ============================================================================

def get_mode_profiles() -> Dict[str, ModeProfile]:
    """
    Returns behavior profiles for all supported life modes.
    
    Each profile defines:
    - plan_complexity: How complex/ambitious the plan should be
    - activity_intensity: Recommended activity difficulty
    - recovery_priority: How much to prioritize recovery
    - focus_areas: What to emphasize
    - avoid_areas: What to minimize
    
    Returns:
        Dictionary mapping mode names to their profiles
    """
    return {
        LifeModeName.MAINTENANCE.value: ModeProfile(
            mode=LifeModeName.MAINTENANCE,
            plan_complexity=PlanComplexity.NORMAL,
            activity_intensity=ActivityIntensity.MODERATE,
            recovery_priority=RecoveryPriority.NORMAL,
            description="Default balanced state - normal planning and activity levels",
            focus_areas=["stability", "routine", "balance", "gradual_progress"],
            avoid_areas=["major_disruptions", "excessive_commitments"],
            energy_protection=False,
        ),
        LifeModeName.GROWTH.value: ModeProfile(
            mode=LifeModeName.GROWTH,
            plan_complexity=PlanComplexity.AMBITIOUS,
            activity_intensity=ActivityIntensity.HIGH,
            recovery_priority=RecoveryPriority.MODERATE,
            description="User is pushing progress - allow ambitious goals and higher intensity",
            focus_areas=["challenge", "skill_building", "momentum", "achievement"],
            avoid_areas=["maintenance_only", "excessive_rest"],
            energy_protection=False,
        ),
        LifeModeName.RECOVERY.value: ModeProfile(
            mode=LifeModeName.RECOVERY,
            plan_complexity=PlanComplexity.SIMPLE,
            activity_intensity=ActivityIntensity.LOW,
            recovery_priority=RecoveryPriority.HIGH,
            description="User is rebuilding energy - minimize load, emphasize recovery",
            focus_areas=["rest", "restoration", "gentle_movement", "self_care"],
            avoid_areas=["ambitious_goals", "high_intensity", "new_commitments"],
            energy_protection=True,
        ),
        LifeModeName.CRISIS.value: ModeProfile(
            mode=LifeModeName.CRISIS,
            plan_complexity=PlanComplexity.MINIMAL,
            activity_intensity=ActivityIntensity.VERY_LOW,
            recovery_priority=RecoveryPriority.MAXIMUM,
            description="System protection mode - absolutely minimal planning, maximum recovery",
            focus_areas=["survival", "critical_only", "emergency_response", "protection"],
            avoid_areas=["all_nonessential", "any_risk"],
            energy_protection=True,
        ),
        LifeModeName.EXAM_MODE.value: ModeProfile(
            mode=LifeModeName.EXAM_MODE,
            plan_complexity=PlanComplexity.SIMPLE,
            activity_intensity=ActivityIntensity.LOW,
            recovery_priority=RecoveryPriority.HIGH,
            description="Academic pressure - simplify life, prioritize exam prep and recovery",
            focus_areas=["exam_preparation", "focus_time", "sleep", "stress_management"],
            avoid_areas=["social_overcommitment", "new_projects", "high_intensity"],
            energy_protection=True,
        ),
        LifeModeName.TRAVEL_MODE.value: ModeProfile(
            mode=LifeModeName.TRAVEL_MODE,
            plan_complexity=PlanComplexity.FLEXIBLE,
            activity_intensity=ActivityIntensity.LOW,
            recovery_priority=RecoveryPriority.MODERATE,
            description="Environment disruption - adapt plans flexibly, lower intensity",
            focus_areas=["adaptability", "self_care_while_traveling", "rest_opportunities"],
            avoid_areas=["fixed_schedule", "complex_routines", "high_intensity"],
            energy_protection=True,
        ),
        LifeModeName.WORK_CRUNCH_MODE.value: ModeProfile(
            mode=LifeModeName.WORK_CRUNCH_MODE,
            plan_complexity=PlanComplexity.MINIMAL,
            activity_intensity=ActivityIntensity.LOW,
            recovery_priority=RecoveryPriority.MODERATE,
            description="High professional workload - focus on work, protect personal recovery",
            focus_areas=["work_support", "efficient_self_care", "stress_relief"],
            avoid_areas=["new_commitments", "time_consuming_hobbies", "complex_planning"],
            energy_protection=True,
        ),
        LifeModeName.SOCIAL_WEEK_MODE.value: ModeProfile(
            mode=LifeModeName.SOCIAL_WEEK_MODE,
            plan_complexity=PlanComplexity.FLEXIBLE,
            activity_intensity=ActivityIntensity.MODERATE,
            recovery_priority=RecoveryPriority.MODERATE,
            description="Heavy social commitments - allow flexibility, balance social and personal",
            focus_areas=["social_energy", "meaningful_connections", "downtime_between_events"],
            avoid_areas=["intensive_solo_projects", "rigid_schedules"],
            energy_protection=False,
        ),
    }


# ============================================================================
# MODE DETECTION (Signal generation)
# ============================================================================

def detect_life_mode(state: Dict[str, Any]) -> LifeModeDetectionResult:
    """
    Detect candidate life modes based on signals from system state.
    
    Evaluates all detection rules and generates signals for triggered modes.
    
    Input signals evaluated:
    - constraint_pressure_level
    - overload_detected
    - daily_budget
    - remaining_energy
    - environment_stability_score
    - predicted_energy_dips
    - constraint_analysis data
    - user_history patterns
    
    Returns:
        LifeModeDetectionResult with all triggered signals grouped by mode
    """
    logger.info("Starting life mode detection")
    
    mode_signals: Dict[str, List[ModeDetectionSignal]] = {}
    triggered_modes: Set[LifeModeName] = set()
    
    # Extract relevant state
    constraint_pressure = state.get("system_flags", {}).get("constraint_pressure_level", "LOW")
    overload_detected = state.get("system_flags", {}).get("overload_detected", False)
    
    energy_budget = state.get("energy_budget", {})
    daily_budget = energy_budget.get("daily_budget", 100)
    remaining_energy = energy_budget.get("remaining_energy", 100)
    
    environment = state.get("environment_context", {})
    env_stability = environment.get("environment_stability_score", 1.0)
    
    forecast = state.get("forecast_data", {})
    predicted_dips = forecast.get("predicted_energy_dips", [])
    
    constraints = state.get("constraints", [])
    user_history = state.get("user_history", {})
    
    constraint_analysis = state.get("constraint_analysis", {})
    constraint_categories = constraint_analysis.get("constraint_categories_present", [])
    
    # ========================================================================
    # RULE 1: CRITICAL constraint pressure → CRISIS
    # ========================================================================
    if constraint_pressure == "CRITICAL":
        signal = ModeDetectionSignal(
            signal_name="critical_constraint_pressure",
            triggered_mode=LifeModeName.CRISIS,
            signal_strength=0.95,
            signal_evidence="System experiencing critical constraint pressure requiring protection mode",
            contributing_factors=["constraint_pressure_level=CRITICAL"],
        )
        _add_signal(mode_signals, LifeModeName.CRISIS, signal)
        triggered_modes.add(LifeModeName.CRISIS)
        logger.info("Signal triggered: CRISIS (critical constraint pressure)")
    
    # ========================================================================
    # RULE 2: overload_detected = True → RECOVERY
    # ========================================================================
    if overload_detected:
        signal = ModeDetectionSignal(
            signal_name="system_overload_detected",
            triggered_mode=LifeModeName.RECOVERY,
            signal_strength=0.90,
            signal_evidence="System overload flag detected - requires recovery and deload",
            contributing_factors=["overload_detected=True"],
        )
        _add_signal(mode_signals, LifeModeName.RECOVERY, signal)
        triggered_modes.add(LifeModeName.RECOVERY)
        logger.info("Signal triggered: RECOVERY (overload detected)")
    
    # ========================================================================
    # RULE 3: daily_budget < 50 → RECOVERY
    # ========================================================================
    if daily_budget < 50:
        signal = ModeDetectionSignal(
            signal_name="critically_low_energy_budget",
            triggered_mode=LifeModeName.RECOVERY,
            signal_strength=0.85,
            signal_evidence=f"Energy budget is critically low ({daily_budget} units)",
            contributing_factors=[f"daily_budget={daily_budget}"],
        )
        _add_signal(mode_signals, LifeModeName.RECOVERY, signal)
        triggered_modes.add(LifeModeName.RECOVERY)
        logger.info(f"Signal triggered: RECOVERY (low budget: {daily_budget})")
    
    # ========================================================================
    # RULE 4: remaining_energy < 30 → RECOVERY
    # ========================================================================
    if remaining_energy < 30:
        signal = ModeDetectionSignal(
            signal_name="remaining_energy_depleted",
            triggered_mode=LifeModeName.RECOVERY,
            signal_strength=0.80,
            signal_evidence=f"Remaining energy critically low ({remaining_energy} units)",
            contributing_factors=[f"remaining_energy={remaining_energy}"],
        )
        _add_signal(mode_signals, LifeModeName.RECOVERY, signal)
        triggered_modes.add(LifeModeName.RECOVERY)
        logger.info(f"Signal triggered: RECOVERY (depleted: {remaining_energy})")
    
    # ========================================================================
    # RULE 5: Multiple energy dips forecast → RECOVERY
    # ========================================================================
    if len(predicted_dips) >= 2:
        signal = ModeDetectionSignal(
            signal_name="multiple_energy_dips_predicted",
            triggered_mode=LifeModeName.RECOVERY,
            signal_strength=0.70,
            signal_evidence=f"Forecast predicts multiple energy dips ({len(predicted_dips)} events)",
            contributing_factors=[f"predicted_energy_dips={len(predicted_dips)}"],
        )
        _add_signal(mode_signals, LifeModeName.RECOVERY, signal)
        triggered_modes.add(LifeModeName.RECOVERY)
        logger.info(f"Signal triggered: RECOVERY (dips: {len(predicted_dips)})")
    
    # ========================================================================
    # RULE 6: HIGH constraint pressure + academic constraint → EXAM_MODE
    # ========================================================================
    has_academic = "academic" in constraint_categories or any(
        c.get("category", "").lower() == "academic" for c in constraints
    )
    if constraint_pressure in ["HIGH", "CRITICAL"] and has_academic:
        signal = ModeDetectionSignal(
            signal_name="high_academic_pressure",
            triggered_mode=LifeModeName.EXAM_MODE,
            signal_strength=0.85,
            signal_evidence="High constraint pressure + academic constraints detected",
            contributing_factors=[f"pressure={constraint_pressure}", "academic_constraint=present"],
        )
        _add_signal(mode_signals, LifeModeName.EXAM_MODE, signal)
        triggered_modes.add(LifeModeName.EXAM_MODE)
        logger.info("Signal triggered: EXAM_MODE (high academic pressure)")
    
    # ========================================================================
    # RULE 7: environment_stability < 0.3 → TRAVEL_MODE
    # ========================================================================
    if env_stability < 0.3:
        signal = ModeDetectionSignal(
            signal_name="low_environment_stability",
            triggered_mode=LifeModeName.TRAVEL_MODE,
            signal_strength=0.75,
            signal_evidence=f"Environment stability critically low ({env_stability:.2f})",
            contributing_factors=[f"environment_stability_score={env_stability:.2f}"],
        )
        _add_signal(mode_signals, LifeModeName.TRAVEL_MODE, signal)
        triggered_modes.add(LifeModeName.TRAVEL_MODE)
        logger.info(f"Signal triggered: TRAVEL_MODE (stability: {env_stability:.2f})")
    
    # ========================================================================
    # RULE 8: HIGH social obligations → SOCIAL_WEEK_MODE
    # ========================================================================
    social_obligations = environment.get("social_obligations_weekly", 0)
    has_social = "social" in constraint_categories or social_obligations > 5
    if has_social and constraint_pressure in ["MODERATE", "HIGH"]:
        signal = ModeDetectionSignal(
            signal_name="high_social_obligations",
            triggered_mode=LifeModeName.SOCIAL_WEEK_MODE,
            signal_strength=0.70,
            signal_evidence=f"High social obligations ({social_obligations} weekly)",
            contributing_factors=[f"social_obligations={social_obligations}"],
        )
        _add_signal(mode_signals, LifeModeName.SOCIAL_WEEK_MODE, signal)
        triggered_modes.add(LifeModeName.SOCIAL_WEEK_MODE)
        logger.info("Signal triggered: SOCIAL_WEEK_MODE (high social obligations)")
    
    # ========================================================================
    # RULE 9: HIGH energy + LOW constraints → GROWTH
    # ========================================================================
    if (
        remaining_energy > 70
        and constraint_pressure == "LOW"
        and not overload_detected
        and env_stability > 0.6
    ):
        signal = ModeDetectionSignal(
            signal_name="high_capacity_available",
            triggered_mode=LifeModeName.GROWTH,
            signal_strength=0.75,
            signal_evidence="Good energy, low constraints, stable environment - opportunity for growth",
            contributing_factors=[
                f"remaining_energy={remaining_energy}",
                f"constraint_pressure={constraint_pressure}",
            ],
        )
        _add_signal(mode_signals, LifeModeName.GROWTH, signal)
        triggered_modes.add(LifeModeName.GROWTH)
        logger.info("Signal triggered: GROWTH (high capacity)")
    
    # ========================================================================
    # RULE 10: MODERATE constraint pressure + work constraint → WORK_CRUNCH_MODE
    # ========================================================================
    has_work = "work" in constraint_categories or any(
        c.get("category", "").lower() == "work" for c in constraints
    )
    if constraint_pressure == "HIGH" and has_work:
        signal = ModeDetectionSignal(
            signal_name="high_work_pressure",
            triggered_mode=LifeModeName.WORK_CRUNCH_MODE,
            signal_strength=0.80,
            signal_evidence="High work-related constraint pressure detected",
            contributing_factors=[f"pressure={constraint_pressure}", "work_constraint=present"],
        )
        _add_signal(mode_signals, LifeModeName.WORK_CRUNCH_MODE, signal)
        triggered_modes.add(LifeModeName.WORK_CRUNCH_MODE)
        logger.info("Signal triggered: WORK_CRUNCH_MODE (high work pressure)")
    
    # ========================================================================
    # If no signals triggered, maintenance is always available
    # ========================================================================
    if not triggered_modes:
        signal = ModeDetectionSignal(
            signal_name="no_special_signals",
            triggered_mode=LifeModeName.MAINTENANCE,
            signal_strength=0.50,
            signal_evidence="No special conditions detected - maintenance mode applies",
            contributing_factors=["default_fallback"],
        )
        _add_signal(mode_signals, LifeModeName.MAINTENANCE, signal)
        triggered_modes.add(LifeModeName.MAINTENANCE)
        logger.info("Signal triggered: MAINTENANCE (default fallback)")
    
    # Ensure maintenance is always a fallback option
    elif LifeModeName.MAINTENANCE not in triggered_modes:
        signal = ModeDetectionSignal(
            signal_name="maintenance_fallback",
            triggered_mode=LifeModeName.MAINTENANCE,
            signal_strength=0.30,
            signal_evidence="Available as fallback option",
            contributing_factors=["always_available"],
        )
        _add_signal(mode_signals, LifeModeName.MAINTENANCE, signal)
        triggered_modes.add(LifeModeName.MAINTENANCE)
    
    result = LifeModeDetectionResult(
        candidate_modes=sorted(list(triggered_modes), key=lambda m: m.value),
        mode_signals=mode_signals,
        num_triggered_signals=sum(len(v) for v in mode_signals.values()),
        conflicting_signals_count=_count_conflicting_signals(mode_signals),
    )
    
    logger.info(
        f"Life mode detection complete: "
        f"candidates={len(result.candidate_modes)}, "
        f"signals={result.num_triggered_signals}, "
        f"conflicts={result.conflicting_signals_count}"
    )
    
    return result


def _add_signal(
    mode_signals: Dict[str, List[ModeDetectionSignal]],
    mode: LifeModeName,
    signal: ModeDetectionSignal,
) -> None:
    """Helper to add a signal to the mode_signals dictionary."""
    mode_key = mode.value
    if mode_key not in mode_signals:
        mode_signals[mode_key] = []
    mode_signals[mode_key].append(signal)


def _count_conflicting_signals(mode_signals: Dict[str, List[ModeDetectionSignal]]) -> int:
    """
    Count pairs of signals that contradict each other.
    
    For example: GROWTH and RECOVERY signals are conflicting.
    """
    conflicting_pairs = [
        (LifeModeName.GROWTH, LifeModeName.RECOVERY),
        (LifeModeName.GROWTH, LifeModeName.CRISIS),
        (LifeModeName.CRISIS, LifeModeName.MAINTENANCE),
    ]
    
    count = 0
    for mode1, mode2 in conflicting_pairs:
        if mode1.value in mode_signals and mode2.value in mode_signals:
            count += min(len(mode_signals[mode1.value]), len(mode_signals[mode2.value]))
    
    return count


# ============================================================================
# MODE PRIORITY RESOLUTION (Conflict resolution)
# ============================================================================

def resolve_mode_priority(
    candidate_modes: List[LifeModeName],
    mode_signals: Dict[str, List[ModeDetectionSignal]],
) -> LifeModeResolution:
    """
    Resolve multiple candidate modes using priority hierarchy.
    
    When multiple modes trigger simultaneously, selects the highest-priority one.
    
    Priority hierarchy (highest to lowest):
    1. crisis → recovery → exam_mode → work_crunch_mode → travel_mode → 
       social_week_mode → growth → maintenance
    
    Args:
        candidate_modes: List of modes that triggered detection
        mode_signals: Signals grouped by mode
        
    Returns:
        LifeModeResolution with selected mode and explanation
    """
    logger.info(f"Resolving {len(candidate_modes)} candidate modes")
    
    priority_map = get_mode_priority_map()
    
    # Sort by priority (lower priority value = higher priority)
    sorted_candidates = sorted(
        candidate_modes,
        key=lambda m: priority_map.priority_values.get(m.value, 999),
    )
    
    selected_mode = sorted_candidates[0]
    selected_priority = priority_map.priority_values.get(selected_mode.value, 999)
    
    competing_modes = sorted_candidates[1:] if len(sorted_candidates) > 1 else []
    
    logger.info(f"Selected mode: {selected_mode} (priority={selected_priority})")
    
    # Build resolution reason
    if len(candidate_modes) == 1:
        reason = f"Single candidate: {selected_mode}"
    else:
        competing_str = ", ".join(m.value for m in competing_modes[:2])
        reason = (
            f"Multiple modes triggered ({len(candidate_modes)} total). "
            f"{selected_mode.value} selected as highest priority. "
            f"Deprioritized: {competing_str}"
        )
    
    return LifeModeResolution(
        selected_mode=selected_mode,
        priority_rank=selected_priority + 1,  # 1-indexed
        resolution_reason=reason,
        competing_modes=competing_modes,
    )


# ============================================================================
# MODE PROFILE LOOKUP
# ============================================================================

def get_mode_profile(mode: LifeModeName) -> ModeProfile:
    """
    Get the behavior profile for a specific life mode.
    
    Args:
        mode: The life mode to get profile for
        
    Returns:
        ModeProfile defining behavior for that mode
    """
    profiles = get_mode_profiles()
    profile = profiles.get(mode.value)
    
    if profile is None:
        logger.warning(f"Profile not found for mode {mode}, returning maintenance")
        profile = profiles[LifeModeName.MAINTENANCE.value]
    
    return profile


# ============================================================================
# CONFIDENCE SCORING
# ============================================================================

def calculate_mode_confidence(
    mode: LifeModeName,
    signals: List[ModeDetectionSignal],
    user_history: Dict[str, Any],
) -> Tuple[float, ConfidenceFactors]:
    """
    Calculate confidence score for a detected mode.
    
    Factors:
    - Number of contributing signals (more = higher confidence)
    - Consistency among signals (conflicting signals lower confidence)
    - Historical match against user patterns
    - Adjustment for signal strength variance
    
    Range: 0.0 – 1.0
    
    Args:
        mode: The life mode being scored
        signals: Detection signals for this mode
        user_history: User history data
        
    Returns:
        Tuple of (confidence_score, factors)
    """
    # Factor 1: Number of contributing signals
    num_signals = len(signals)
    if num_signals == 0:
        signal_contribution = 0.3  # Very weak
    elif num_signals == 1:
        signal_contribution = 0.5  # Weak
    elif num_signals <= 2:
        signal_contribution = 0.7  # Moderate
    else:
        signal_contribution = 0.85  # Strong
    
    # Factor 2: Signal consistency (all signals have similar strength)
    if num_signals <= 1:
        consistency = 1.0
    else:
        strengths = [s.signal_strength for s in signals]
        min_strength = min(strengths)
        max_strength = max(strengths)
        consistency = 1.0 - (max_strength - min_strength)
        consistency = max(0.0, consistency)
    
    # Factor 3: Historical pattern match
    # Check if this mode appears frequently in user history
    total_plans = user_history.get("total_plans_generated", 1)
    plans_completed = user_history.get("plans_completed", 0)
    completion_rate = plans_completed / total_plans if total_plans > 0 else 0.5
    
    # Higher completion rate = user's plan-detection probably accurate
    historical_match = 0.3 + (completion_rate * 0.7)
    historical_match = min(1.0, historical_match)
    
    # Factor 4: Baseline confidence from signal strengths
    if num_signals > 0:
        baseline = sum(s.signal_strength for s in signals) / num_signals
    else:
        baseline = 0.5
    
    # Factor 5: Adjustment for signal variance
    if num_signals > 1:
        # Multiple signals pointing to same mode = more stable
        adjustment_factor = 1.0 + (consistency * 0.2)  # Up to 1.2x
    else:
        # Single signal = less stable
        adjustment_factor = 0.8
    
    adjustment_factor = max(0.5, min(1.5, adjustment_factor))
    
    # Combine factors
    final_confidence = (
        signal_contribution * 0.35
        + consistency * 0.20
        + historical_match * 0.20
        + (baseline * 0.25)
    ) * adjustment_factor
    
    final_confidence = max(0.0, min(1.0, final_confidence))
    
    factors = ConfidenceFactors(
        num_contributing_signals=num_signals,
        signal_consistency=consistency,
        historical_pattern_match=historical_match,
        baseline_confidence=baseline,
        adjustment_factor=adjustment_factor,
    )
    
    logger.info(
        f"Confidence for {mode}: {final_confidence:.2f} "
        f"(signals={num_signals}, consistency={consistency:.2f}, historical={historical_match:.2f})"
    )
    
    return final_confidence, factors


# ============================================================================
# MODE EXPLANATION / REASONING
# ============================================================================

def generate_mode_reason(
    mode: LifeModeName,
    signals: List[ModeDetectionSignal],
    confidence: float,
) -> str:
    """
    Generate human-readable explanation for why a mode was selected.
    
    Example output:
    "Recovery mode activated due to low energy budget and recent overload periods."
    
    Args:
        mode: Selected mode
        signals: Contributing signals
        confidence: Confidence score (used to qualify the statement)
        
    Returns:
        Human-readable explanation string
    """
    if not signals:
        return f"Default mode: {mode.value}"
    
    # Build signal summary
    signal_names = [s.signal_name for s in signals]
    main_signals = signal_names[:2]  # Top 2 signals
    
    signal_desc = ", ".join(main_signals)
    if len(signal_names) > 2:
        signal_desc += f", and {len(signal_names) - 2} others"
    
    # Confidence qualifier
    if confidence >= 0.85:
        confidence_qualifier = "strongly"
    elif confidence >= 0.70:
        confidence_qualifier = "clearly"
    elif confidence >= 0.50:
        confidence_qualifier = "indicates"
    else:
        confidence_qualifier = "suggests"
    
    # Build reason
    reason = (
        f"{mode.value.capitalize()} mode {confidence_qualifier} indicated "
        f"by: {signal_desc}. "
        f"Confidence: {confidence:.0%}."
    )
    
    return reason


# ============================================================================
# MODE STABILITY (How likely the mode is to change soon)
# ============================================================================

def calculate_mode_stability(
    mode: LifeModeName,
    signals: List[ModeDetectionSignal],
    constraint_pressure: str,
) -> float:
    """
    Calculate how stable/persistent a mode is likely to be.
    
    Returns 0.0-1.0 where 1.0 = very stable, 0.0 = unstable
    
    Args:
        mode: The selected mode
        signals: Contributing signals
        constraint_pressure: Current constraint pressure level
        
    Returns:
        Stability score (0.0-1.0)
    """
    if not signals:
        return 0.5
    
    # Crisis and recovery modes are typically temporary
    if mode in [LifeModeName.CRISIS, LifeModeName.RECOVERY]:
        stability = 0.4  # Low stability, expects change
    # Growth and maintenance are typically more stable
    elif mode in [LifeModeName.GROWTH, LifeModeName.MAINTENANCE]:
        stability = 0.7  # Higher stability
    # Situational modes depend on circumstance
    else:
        stability = 0.55
    
    # If multiple consistent signals, increase stability
    if len(signals) > 2:
        signal_strengths = [s.signal_strength for s in signals]
        avg_strength = sum(signal_strengths) / len(signal_strengths)
        stability += avg_strength * 0.2  # Up to +0.2
    
    stability = min(1.0, stability)
    
    return stability


def estimate_mode_duration(
    mode: LifeModeName,
    signals: List[ModeDetectionSignal],
    forecast_window_days: int = 7,
) -> Optional[int]:
    """
    Estimate how long the mode is likely to persist (in hours).
    
    Returns None if duration is indeterminate.
    
    Args:
        mode: The selected mode
        signals: Contributing signals
        forecast_window_days: Forecast period length
        
    Returns:
        Estimated duration in hours, or None
    """
    # Crisis mode: typically hours to maybe 1 day
    if mode == LifeModeName.CRISIS:
        return 24
    
    # Recovery: typically 1-3 days
    if mode == LifeModeName.RECOVERY:
        return 48 if len(signals) <= 1 else 72
    
    # Exam mode: typically duration of exam period (days)
    if mode == LifeModeName.EXAM_MODE:
        return forecast_window_days * 24
    
    # Travel: duration of trip
    if mode == LifeModeName.TRAVEL_MODE:
        return None  # Depends on trip length
    
    # Growth: typically stable while conditions permit
    if mode == LifeModeName.GROWTH:
        return None
    
    # Default
    return None
