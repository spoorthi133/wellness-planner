"""
Environment Adapter Utilities

Provides functions for environment normalization, restriction detection,
activity modification, and complexity calculation.

Module: Environment Adapter
Part of: Constraint-First Wellness Agent (Module A)
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from environment_models import (
    ActivityRestrictionReason,
    ActivityModifier,
    EnvironmentComplexityFactors,
    ActivityType,
    EnvironmentType,
)

logger = logging.getLogger(__name__)

# Default equipment available in most environments
MINIMUM_EQUIPMENT = ["body_weight"]

# Activity-specific equipment requirements
EQUIPMENT_FOR_ACTIVITY = {
    "yoga": ["yoga_mat"],
    "resistance_training": ["dumbbells", "resistance_bands"],
    "cardio": ["treadmill", "exercise_bike", "rowing_machine"],
    "swimming": ["pool"],
    "outdoor_running": ["outdoor_space"],
    "stretching": ["floor_space"],
    "pilates": ["floor_space", "yoga_mat"],
    "weights": ["dumbbells", "barbell"],
}

# Activity restrictions by environment constraint
ACTIVITY_RESTRICTIONS_BY_CONSTRAINT = {
    "indoor_only": {
        "outdoor_running": "Outdoor activities not available",
        "hiking": "Outdoor activities not available",
        "outdoor_sports": "Outdoor activities not available",
        "swimming": "No access to outdoor pool",
    },
    "small_space": {
        "large_movement": "Insufficient space for full-body movements",
        "strength_training": "Space limitations",
        "dance": "Space limitations",
        "yoga": "Limited space for full routines",
        "boxing": "Insufficient space",
    },
    "silent_required": {
        "loud_exercises": "Noise restrictions",
        "jumping_jacks": "Noise restrictions",
        "boxing": "Noise restrictions",
        "loud_music": "Noise restrictions",
        "high_intensity": "Noise from impact",
    },
    "shared_room": {
        "private_meditation": "Shared space lacks privacy",
        "therapy_sessions": "Need private space",
        "sensitive_routines": "Shared room restricts privacy",
    },
    "limited_equipment": {
        "strength_training": "Equipment not available",
        "weight_training": "Dumbbells not available",
        "resistance_training": "Bands/weights not available",
    },
}

# How to modify activities to fit constraints
ACTIVITY_MODIFICATIONS = {
    "exercise": {
        "small_space": "low-impact indoor routines",
        "silent_required": "silent bodyweight exercises",
        "limited_equipment": "bodyweight exercises",
    },
    "movement": {
        "small_space": "micro-movement routines",
        "silent_required": "quiet movement sequences",
    },
    "focus_work": {
        "shared_room": "focus with headphones",
        "small_space": "minimal-space setup",
    },
    "meditation": {
        "shared_room": "shorter meditation (5-10 min)",
        "silent_required": "silent meditation enhanced",
        "small_space": "seated meditation",
    },
    "stretching": {
        "small_space": "seated/small-space stretches",
        "shared_room": "quiet stretching",
    },
    "deep_work": {
        "shared_room": "deep work with noise-cancelling",
        "small_space": "minimal-space workflow",
    },
}


# ============================================================================
# Environment Normalization
# ============================================================================

def normalize_environment_context(environment_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize environment context, ensuring required fields exist with safe defaults.
    
    Args:
        environment_context: Raw environment dict from state
        
    Returns:
        Normalized environment dict with all required fields
    """
    if not environment_context:
        environment_context = {}
    
    normalized = environment_context.copy()
    
    # Ensure boolean fields
    normalized["indoor_only"] = normalized.get("indoor_only", False)
    normalized["small_space"] = normalized.get("small_space", False)
    normalized["shared_room"] = normalized.get("shared_room", False)
    normalized["silent_required"] = normalized.get("silent_required", False)
    
    # Ensure equipment list
    if "equipment_available" not in normalized:
        normalized["equipment_available"] = MINIMUM_EQUIPMENT.copy()
    elif not normalized["equipment_available"]:
        normalized["equipment_available"] = MINIMUM_EQUIPMENT.copy()
    else:
        # Always include minimum equipment
        normalized["equipment_available"] = list(
            set(normalized["equipment_available"]) | set(MINIMUM_EQUIPMENT)
        )
    
    # Ensure other fields
    normalized["timezone"] = normalized.get("timezone", "UTC")
    normalized["work_hours"] = normalized.get("work_hours", {"start": "09:00", "end": "17:00"})
    normalized["commute_time_minutes"] = normalized.get("commute_time_minutes", 0)
    normalized["social_obligations_weekly"] = normalized.get("social_obligations_weekly", 0)
    normalized["caregiving_hours_weekly"] = normalized.get("caregiving_hours_weekly", 0.0)
    normalized["pets"] = normalized.get("pets", 0)
    normalized["living_situation"] = normalized.get("living_situation", "independent")
    
    logger.debug(f"Environment context normalized with {len(normalized['equipment_available'])} equipment items")
    
    return normalized


def detect_environment_type(environment_context: Dict[str, Any]) -> str:
    """
    Infer environment type from context flags.
    
    Args:
        environment_context: Normalized environment dict
        
    Returns:
        Environment type string
    """
    indoor = environment_context.get("indoor_only", False)
    small = environment_context.get("small_space", False)
    shared = environment_context.get("shared_room", False)
    silent = environment_context.get("silent_required", False)
    living = environment_context.get("living_situation", "independent").lower()
    
    # Match patterns
    if "dorm" in living:
        return "dorm"
    elif "family" in living or "family_home" in living:
        return "family_home"
    elif shared and small and indoor:
        return "single_room"
    elif small:
        return "studio"
    elif "open_office" in living or "office" in living:
        return "open_office"
    elif "home_office" in living or (indoor and not shared and not small):
        return "home_office"
    else:
        return "independent"


# ============================================================================
# Activity Restriction Detection
# ============================================================================

def detect_activity_restrictions(environment_context: Dict[str, Any]) -> List[str]:
    """
    Detect activities that cannot be performed in this environment.
    
    Args:
        environment_context: Normalized environment context
        
    Returns:
        List of restricted activity names
    """
    restrictions = []
    
    # Check each constraint
    if environment_context.get("indoor_only", False):
        restrictions.extend(ACTIVITY_RESTRICTIONS_BY_CONSTRAINT["indoor_only"].keys())
    
    if environment_context.get("small_space", False):
        restrictions.extend(ACTIVITY_RESTRICTIONS_BY_CONSTRAINT["small_space"].keys())
    
    if environment_context.get("silent_required", False):
        restrictions.extend(ACTIVITY_RESTRICTIONS_BY_CONSTRAINT["silent_required"].keys())
    
    if environment_context.get("shared_room", False):
        restrictions.extend(ACTIVITY_RESTRICTIONS_BY_CONSTRAINT["shared_room"].keys())
    
    # Check equipment limitations
    available = set(environment_context.get("equipment_available", []))
    for activity, equipment in EQUIPMENT_FOR_ACTIVITY.items():
        if not any(eq in available for eq in equipment):
            restrictions.append(activity)
    
    # Remove duplicates and sort
    restrictions = sorted(list(set(restrictions)))
    
    logger.debug(f"Detected {len(restrictions)} activity restrictions: {restrictions}")
    
    return restrictions


def get_restriction_details(
    restricted_activity: str,
    environment_context: Dict[str, Any]
) -> Optional[ActivityRestrictionReason]:
    """
    Get detailed reason for why an activity is restricted.
    
    Args:
        restricted_activity: Activity name
        environment_context: Environment context
        
    Returns:
        Restriction reason or None if not restricted
    """
    reasons = []
    
    # Check each constraint
    for constraint_type, restricted_activities in ACTIVITY_RESTRICTIONS_BY_CONSTRAINT.items():
        if restricted_activity in restricted_activities and environment_context.get(constraint_type, False):
            reasons.append((constraint_type, restricted_activities[restricted_activity]))
    
    if not reasons:
        return None
    
    # Use most important reason
    constraint_type, reason_msg = reasons[0]
    
    # Determine severity based on number of restrictions
    severity = min(10, 3 + len(reasons) * 2)
    
    # Suggest alternative
    alternative = suggest_alternative_activity(restricted_activity, environment_context)
    
    return ActivityRestrictionReason(
        activity=restricted_activity,
        reason=reason_msg,
        restriction_type=constraint_type,
        alternative=alternative,
        severity=severity,
    )


# ============================================================================
# Activity Modifier Generation
# ============================================================================

def generate_activity_modifiers(environment_context: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate how to modify activities to fit environment constraints.
    
    Non-blocking adaptations.
    
    Args:
        environment_context: Normalized environment context
        
    Returns:
        Dict mapping activity → modified version
    """
    modifiers = {}
    
    # For each constraint, modify relevant activities
    constraints_present = []
    if environment_context.get("small_space", False):
        constraints_present.append("small_space")
    if environment_context.get("silent_required", False):
        constraints_present.append("silent_required")
    if environment_context.get("shared_room", False):
        constraints_present.append("shared_room")
    if environment_context.get("limited_equipment", False):
        constraints_present.append("limited_equipment")
    
    # Apply modifications for each constraint
    for activity, constraint_mods in ACTIVITY_MODIFICATIONS.items():
        for constraint in constraints_present:
            if constraint in constraint_mods:
                modifiers[activity] = constraint_mods[constraint]
                break
    
    logger.debug(f"Generated modifiers for {len(modifiers)} activities")
    
    return modifiers


def describe_activity_modification(
    activity: str,
    environment_context: Dict[str, Any]
) -> Optional[ActivityModifier]:
    """
    Describe how to modify a specific activity.
    
    Args:
        activity: Activity type
        environment_context: Environment context
        
    Returns:
        ActivityModifier or None
    """
    # Get modified version
    modified = get_modified_activity(activity, environment_context)
    if not modified:
        return None
    
    # Determine effectiveness (how well modified version works)
    effectiveness = 0.85  # Default: pretty effective
    if environment_context.get("small_space", False):
        effectiveness -= 0.15
    if environment_context.get("silent_required", False):
        effectiveness -= 0.1
    
    # Determine energy cost (modified activities may cost differently)
    energy_cost = 1.0  # Default: same cost
    if environment_context.get("small_space", False):
        energy_cost *= 0.8  # Smaller movements use less energy
    
    rationale = f"Modified to fit {', '.join(get_active_constraints(environment_context))}"
    
    return ActivityModifier(
        original_activity=activity,
        modified_activity=modified,
        modification_rationale=rationale,
        effectiveness_multiplier=max(0.3, effectiveness),
        energy_cost_multiplier=energy_cost,
    )


def get_modified_activity(activity: str, environment_context: Dict[str, Any]) -> Optional[str]:
    """
    Get the modified version of an activity based on constraints.
    
    Args:
        activity: Original activity
        environment_context: Environment context
        
    Returns:
        Modified activity description or None
    """
    if activity not in ACTIVITY_MODIFICATIONS:
        return None
    
    mods = ACTIVITY_MODIFICATIONS[activity]
    
    # Return first applicable modification
    for constraint in get_active_constraints(environment_context):
        if constraint in mods:
            return mods[constraint]
    
    return None


def suggest_alternative_activity(
    restricted_activity: str,
    environment_context: Dict[str, Any]
) -> Optional[str]:
    """
    Suggest an alternative activity when one is blocked.
    
    Args:
        restricted_activity: Blocked activity
        environment_context: Environment context
        
    Returns:
        Alternative activity suggestion or None
    """
    # Map blocked activities to alternatives
    alternatives = {
        "outdoor_running": "indoor treadmill or stair climbing",
        "hiking": "stationary bike or climbing stairs",
        "loud_exercises": "quiet bodyweight exercises",
        "swimming": "water-free cardio alternatives",
        "large_movement": "micro-movements or quiet stretching",
        "boxing": "shadow boxing (quiet)",
        "jump_rope": "step-based cardio",
    }
    
    return alternatives.get(restricted_activity)


# ============================================================================
# Environment Complexity Calculation
# ============================================================================

def calculate_environment_complexity(environment_context: Dict[str, Any]) -> int:
    """
    Calculate environment complexity score (0-10).
    
    Considers:
    - Number of restrictions
    - Severity of restrictions
    - Equipment limitations
    
    Args:
        environment_context: Normalized environment context
        
    Returns:
        Complexity score (0-10)
    """
    factors = build_complexity_factors(environment_context)
    
    # Take the maximum penalty (compounding effects)
    # OR could average them for smoother scoring
    complexity = min(10, factors.total_penalty() + calculate_equipment_penalty(environment_context))
    
    logger.debug(f"Environment complexity calculated: {complexity}")
    
    return complexity


def build_complexity_factors(environment_context: Dict[str, Any]) -> EnvironmentComplexityFactors:
    """
    Build detailed complexity factors from environment.
    
    Args:
        environment_context: Environment context
        
    Returns:
        Complexity factors breakdown
    """
    # Base penalties
    indoor_penalty = 2 if environment_context.get("indoor_only", False) else 0
    small_space_penalty = 3 if environment_context.get("small_space", False) else 0
    shared_room_penalty = 2 if environment_context.get("shared_room", False) else 0
    silent_penalty = 2 if environment_context.get("silent_required", False) else 0
    
    # Equipment limitations
    equipment = set(environment_context.get("equipment_available", []))
    equipment_penalty = 0
    if len(equipment) <= 1:  # Only body weight
        equipment_penalty = 3
    elif len(equipment) <= 3:
        equipment_penalty = 1
    
    # Privacy limitations (derived)
    privacy_penalty = 1 if environment_context.get("shared_room", False) else 0
    
    return EnvironmentComplexityFactors(
        indoor_only_penalty=indoor_penalty,
        small_space_penalty=small_space_penalty,
        shared_room_penalty=shared_room_penalty,
        silent_required_penalty=silent_penalty,
        equipment_limitation_penalty=equipment_penalty,
        privacy_limitation_penalty=privacy_penalty,
    )


def calculate_equipment_penalty(environment_context: Dict[str, Any]) -> int:
    """
    Calculate penalty for equipment limitations.
    
    Args:
        environment_context: Environment context
        
    Returns:
        Equipment penalty (0-3)
    """
    equipment = set(environment_context.get("equipment_available", []))
    
    if len(equipment) <= 1:
        return 3  # Severe limitation
    elif len(equipment) <= 3:
        return 1  # Minor limitation
    
    return 0  # No limitation


def interpret_complexity_score(score: int) -> str:
    """
    Interpret complexity score for human understanding.
    
    Args:
        score: Complexity score (0-10)
        
    Returns:
        Interpretation string
    """
    if score <= 2:
        return "VERY_SIMPLE"
    elif score <= 4:
        return "SIMPLE"
    elif score <= 6:
        return "MODERATE"
    elif score <= 8:
        return "COMPLEX"
    else:
        return "VERY_COMPLEX"


# ============================================================================
# Activity Capability Map (NEW)
# ============================================================================

def get_available_activity_types(
    environment_context: Dict[str, Any],
    activity_restrictions: List[str]
) -> List[str]:
    """
    Generate a list of activities that CAN be performed in this environment.
    
    This is derived from all possible activities minus the restrictions.
    Helps plan generators understand what's feasible.
    
    Args:
        environment_context: Normalized environment context
        activity_restrictions: List of activities that are restricted
        
    Returns:
        List of activity type strings available in this environment (lowercase, normalized)
    """
    # All possible activity types from the enum
    all_activities = [
        "light_movement",       # gentle, low-impact movement
        "focus_work",           # concentrated work
        "meditation",           # mindfulness/meditation
        "stretching",           # flexibility/stretching
        "exercise",             # general exercise
        "movement",             # general movement
        "deep_work",            # intense, focused work
        "creative",             # creative activities
        "outdoor",              # outdoor activities
        "loud_activity",        # activities that generate noise
        "social",               # social interactions
    ]
    
    # Normalize restrictions to lowercase for comparison
    normalized_restrictions = [r.lower() for r in activity_restrictions]
    
    # Filter out restricted activities
    available = [
        activity for activity in all_activities
        if activity not in normalized_restrictions
    ]
    
    logger.debug(
        f"Available activities: {len(available)}/{len(all_activities)} "
        f"({''.join([a[0] for a in available])})"
    )
    
    return sorted(available)


# ============================================================================
# Environment Stability Score (NEW)
# ============================================================================

def calculate_environment_stability_score(environment_context: Dict[str, Any]) -> float:
    """
    Calculate environment stability score (0.0-1.0).
    
    Lower scores indicate highly dynamic environments (frequently changing).
    Higher scores indicate stable environments (consistent, predictable).
    
    Examples:
    - dorm room: 0.2 (highly dynamic - roommates, noise, visitors)
    - shared apartment: 0.4 (fairly dynamic - multiple people sharing space)
    - home office: 0.85 (stable - personal control)
    - independent studio: 0.8 (stable - personal control)
    
    Stability affects planning:
    - Low stability (0.0-0.3): Short-term plans, flexible scheduling, frequent adaptations
    - Moderate (0.3-0.7): Medium-term plans, some flexibility needed
    - High stability (0.7-1.0): Longer-term plans, structured schedules possible
    
    Args:
        environment_context: Normalized environment context
        
    Returns:
        Stability score 0.0-1.0
    """
    # Base score from environment type
    living_situation = environment_context.get("living_situation", "independent").lower()
    
    # Initial stability based on living environment
    # Note: Check more specific patterns first to avoid substring matching issues
    if "dorm" in living_situation:
        base_score = 0.2  # Highly dynamic: shared spaces, different schedules
    elif "home_office" in living_situation:
        base_score = 0.85  # Stable: personal control of environment
    elif "open_office" in living_situation:
        base_score = 0.3  # Highly dynamic: shared workspace, interruptions
    elif "family" in living_situation:
        base_score = 0.6  # Moderate: household routines, family obligations
    elif "shared" in living_situation or "apartment" in living_situation:
        base_score = 0.4  # Fairly dynamic: multiple people, shared responsibilities
    elif "office" in living_situation:
        base_score = 0.3  # Highly dynamic: shared workspace, interruptions
    elif "studio" in living_situation or "single" in living_situation:
        base_score = 0.8  # Stable: personal control
    else:  # independent, default
        base_score = 0.8  # Stable: personal control
    
    # Apply modifiers for specific constraints
    stability_score = base_score
    
    # Shared room reduces stability significantly
    if environment_context.get("shared_room", False):
        stability_score -= 0.2
    
    # Small space affects predictability
    if environment_context.get("small_space", False):
        stability_score -= 0.1
    
    # Silent requirement indicates noise sensitivity/unpredictability
    if environment_context.get("silent_required", False):
        stability_score -= 0.15
    
    # Social obligations reduce predictability
    social_obs = environment_context.get("social_obligations_weekly", 0)
    if social_obs > 5:
        stability_score -= 0.1
    
    # Caregiving hours dramatically reduce stability
    caregiving_hours = environment_context.get("caregiving_hours_weekly", 0.0)
    if caregiving_hours > 0:
        stability_score -= min(0.2, caregiving_hours / 40)  # Max -0.2 for caregiving
    
    # Pets add some unpredictability
    pets = environment_context.get("pets", 0)
    if pets > 0:
        stability_score -= 0.05 * min(pets, 3)  # Max -0.15 for pets
    
    # Clamp to valid range
    stability_score = max(0.0, min(1.0, stability_score))
    
    logger.debug(f"Environment stability score calculated: {stability_score:.2f}")
    
    return stability_score


def interpret_stability_score(score: float) -> str:
    """
    Interpret stability score for human understanding.
    
    Args:
        score: Stability score (0.0-1.0)
        
    Returns:
        Interpretation string
    """
    if score < 0.3:
        return "HIGHLY_DYNAMIC"
    elif score < 0.6:
        return "FAIRLY_DYNAMIC"
    elif score < 0.75:
        return "MODERATE"
    elif score < 0.9:
        return "FAIRLY_STABLE"
    else:
        return "HIGHLY_STABLE"


# ============================================================================
# Helper Functions
# ============================================================================

def get_active_constraints(environment_context: Dict[str, Any]) -> List[str]:
    """
    Get list of active constraints.
    
    Args:
        environment_context: Environment context
        
    Returns:
        List of active constraint names
    """
    constraints = []
    
    if environment_context.get("indoor_only", False):
        constraints.append("indoor_only")
    if environment_context.get("small_space", False):
        constraints.append("small_space")
    if environment_context.get("shared_room", False):
        constraints.append("shared_room")
    if environment_context.get("silent_required", False):
        constraints.append("silent_required")
    if not environment_context.get("equipment_available"):
        constraints.append("limited_equipment")
    
    return constraints


def generate_adaptation_recommendations(
    activity_restrictions: List[str],
    activity_modifiers: Dict[str, str],
    complexity: int,
) -> List[str]:
    """
    Generate recommendations for how to adapt to environment.
    
    Args:
        activity_restrictions: List of restricted activities
        activity_modifiers: Dict of activity modifications
        complexity: Complexity score
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    if complexity >= 7:
        recommendations.append("Environment is complex - consider simpler activity types")
    
    if len(activity_restrictions) >= 5:
        recommendations.append(f"Multiple restrictions detected ({len(activity_restrictions)}) - focus on available options")
    
    if activity_modifiers:
        mods = ", ".join(set(activity_modifiers.values()))[:50]
        recommendations.append(f"Consider modified activities: {mods}...")
    
    if not recommendations:
        recommendations.append("Environment supports most activity types - good flexibility")
    
    return recommendations


def validate_environment_consistency(environment_context: Dict[str, Any]) -> List[str]:
    """
    Check for contradictions in environment context.
    
    Args:
        environment_context: Environment context
        
    Returns:
        List of consistency warnings
    """
    issues = []
    
    # Check contradictions
    if environment_context.get("small_space") and len(environment_context.get("equipment_available", [])) > 5:
        issues.append("Small space but many equipment items - may not fit")
    
    if (
        not environment_context.get("shared_room")
        and environment_context.get("silent_required", False)
    ):
        issues.append("Silent required but not shared room - unusual combination")
    
    if (
        environment_context.get("outdoor_space") is False
        and not environment_context.get("indoor_only", False)
    ):
        issues.append("Contradictory outdoor space settings")
    
    return issues
