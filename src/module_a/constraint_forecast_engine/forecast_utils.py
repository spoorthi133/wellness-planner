"""
Forecast Utilities - Core prediction logic for constraint forecasting.

Implements deterministic algorithms for:
- Energy dip prediction
- Schedule disruption detection
- Opportunity window identification
- Confidence calculation
- Forecast validation
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any
from forecast_models import (
    PredictedEnergyDip,
    PredictedScheduleDisruption,
    OpportunityWindow,
    SeverityLevel,
    DisruptionType,
    ForecastValidationResult,
    PredictionFactors,
)

logger = logging.getLogger(__name__)

# ============================================================================
# ENERGY DIP DETECTION RULES
# ============================================================================

ENERGY_DIP_RULES = [
    {
        "name": "high_constraint_score",
        "description": "High current constraint burden reduces available energy",
        "condition": lambda factors: factors.current_constraint_score >= 7.0,
        "dip_severity": lambda score: SeverityLevel.CRITICAL if score >= 9 else SeverityLevel.HIGH,
        "day_offset": 0,
        "confidence": 0.9,
    },
    {
        "name": "recent_overload",
        "description": "Recent overload episodes predict energy dips 1-2 days later",
        "condition": lambda factors: factors.overload_history >= 1,
        "dip_severity": lambda _: SeverityLevel.HIGH,
        "day_offset": 1,
        "confidence": 0.75,
    },
    {
        "name": "low_recovery_periods",
        "description": "Insufficient recovery time amplifies fatigue",
        "condition": lambda factors: factors.recovery_periods <= 1,
        "dip_severity": lambda _: SeverityLevel.MODERATE,
        "day_offset": 2,
        "confidence": 0.7,
    },
    {
        "name": "physical_mental_cluster",
        "description": "Compounding physical + mental constraints drain energy",
        "condition": lambda factors: (
            factors.constraint_clusters.get("physical", 0) > 0 and
            factors.constraint_clusters.get("mental", 0) > 0
        ),
        "dip_severity": lambda _: SeverityLevel.HIGH,
        "day_offset": 3,
        "confidence": 0.8,
    },
    {
        "name": "crisis_mode",
        "description": "Crisis mode amplifies all energy constraints",
        "condition": lambda factors: factors.life_mode == "crisis",
        "dip_severity": lambda _: SeverityLevel.CRITICAL,
        "day_offset": 0,
        "confidence": 1.0,
    },
]

# ============================================================================
# SCHEDULE DISRUPTION DETECTION RULES
# ============================================================================

SCHEDULE_DISRUPTION_RULES = [
    {
        "name": "deadline_pressure",
        "description": "High time pressure predicts deadline disruptions",
        "condition": lambda factors: factors.constraint_clusters.get("time", 0) >= 2,
        "disruption_type": DisruptionType.DEADLINE_PRESSURE,
        "day_offsets": [0, 1, 2],
        "confidence": 0.85,
    },
    {
        "name": "travel_disruption",
        "description": "Logistical constraints predict travel-related disruptions",
        "condition": lambda factors: factors.constraint_clusters.get("logistical", 0) > 0,
        "disruption_type": DisruptionType.TRAVEL_DISRUPTION,
        "day_offsets": [1, 2],
        "confidence": 0.75,
    },
    {
        "name": "social_conflict",
        "description": "Social constraint conflicts indicate interpersonal stress",
        "condition": lambda factors: (
            factors.constraint_clusters.get("social", 0) > 0 and
            any("social" in str(c).lower() for c in factors.constraint_conflicts)
        ),
        "disruption_type": DisruptionType.SOCIAL_CONFLICT,
        "day_offsets": [1, 3, 4],
        "confidence": 0.7,
    },
    {
        "name": "environment_stress",
        "description": "Unstable environment increases disruption likelihood",
        "condition": lambda factors: factors.environment_stability == "unstable",
        "disruption_type": DisruptionType.ENVIRONMENT_STRESS,
        "day_offsets": [0, 1, 2, 3],
        "confidence": 0.8,
    },
    {
        "name": "irregular_schedule",
        "description": "Irregular schedule predicts compounding disruptions",
        "condition": lambda factors: factors.schedule_regularity == "irregular",
        "disruption_type": DisruptionType.COMPOUNDING_LOAD,
        "day_offsets": [2, 3, 4, 5],
        "confidence": 0.65,
    },
    {
        "name": "recovery_needed",
        "description": "Insufficient recovery periods signal need for stabilization",
        "condition": lambda factors: factors.recent_constraint_frequency >= 5,
        "disruption_type": DisruptionType.RECOVERY_NEEDED,
        "day_offsets": [3, 4],
        "confidence": 0.75,
    },
]

# ============================================================================
# OPPORTUNITY WINDOW DETECTION RULES
# ============================================================================

OPPORTUNITY_RULES = [
    {
        "name": "low_constraint_score",
        "description": "Score < 4 indicates low constraint pressure",
        "condition": lambda factors: factors.current_constraint_score < 4.0,
        "duration_days": 3,
        "flexibility": 0.8,
        "start_offset": 0,
    },
    {
        "name": "high_adaptability",
        "description": "High adaptability creates flexibility opportunity",
        "condition": lambda factors: factors.adaptation_capacity > 0.7,
        "duration_days": 2,
        "flexibility": 0.75,
        "start_offset": 1,
    },
    {
        "name": "low_recent_frequency",
        "description": "Few constraints recently = potential window",
        "condition": lambda factors: factors.recent_constraint_frequency <= 2,
        "duration_days": 2,
        "flexibility": 0.7,
        "start_offset": 2,
    },
    {
        "name": "growth_mode",
        "description": "Growth life mode enables opportunity expansion",
        "condition": lambda factors: factors.life_mode == "growth",
        "duration_days": 3,
        "flexibility": 0.85,
        "start_offset": 1,
    },
]

# ============================================================================
# ENERGY DIP PREDICTION
# ============================================================================

def predict_energy_dips(factors: PredictionFactors) -> List[PredictedEnergyDip]:
    """
    Predict periods of reduced energy availability.
    
    Uses multi-rule detection across constraint score, overload history,
    recovery gaps, and constraint clusters.
    
    Args:
        factors: Prediction input factors
        
    Returns:
        List of predicted energy dips with day offsets and severities
    """
    dips: Dict[int, PredictedEnergyDip] = {}
    
    for rule in ENERGY_DIP_RULES:
        if rule["condition"](factors):
            day_offset = rule["day_offset"]
            severity = rule["dip_severity"](factors.current_constraint_score)
            confidence = rule["confidence"]
            
            # Reduce confidence if low data quality
            if factors.user_history_sample_size < 10:
                confidence *= 0.7
            
            # Merge with existing dip or create new
            if day_offset in dips:
                existing = dips[day_offset]
                # Combine: take max severity, average confidence
                severity_rank = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
                if severity_rank[severity.value] > severity_rank[existing.severity.value]:
                    dips[day_offset].severity = severity
                dips[day_offset].confidence = min(1.0, (existing.confidence + confidence) / 2)
                dips[day_offset].secondary_causes.append(rule["description"])
            else:
                dips[day_offset] = PredictedEnergyDip(
                    day_offset=day_offset,
                    severity=severity,
                    confidence=confidence,
                    primary_cause=rule["description"],
                    secondary_causes=[],
                    recommended_action=_get_energy_dip_recommendation(severity),
                )
    
    # Sort by day offset and return only high-confidence predictions
    return sorted(
        [d for d in dips.values() if d.confidence >= 0.5],
        key=lambda d: d.day_offset
    )


def _get_energy_dip_recommendation(severity: SeverityLevel) -> str:
    """Get recommendation based on dip severity."""
    recommendations = {
        SeverityLevel.LOW: "Monitor energy levels; maintain routine",
        SeverityLevel.MODERATE: "Reduce optional commitments; prioritize rest",
        SeverityLevel.HIGH: "Clear schedule if possible; plan recovery time",
        SeverityLevel.CRITICAL: "Emergency recovery mode; cancel non-essential activities",
    }
    return recommendations.get(severity, "")


# ============================================================================
# SCHEDULE DISRUPTION PREDICTION
# ============================================================================

def predict_schedule_disruptions(factors: PredictionFactors) -> List[PredictedScheduleDisruption]:
    """
    Predict future schedule disruptions.
    
    Uses multi-rule detection across time pressure, logistics, social factors,
    and environment stability.
    
    Args:
        factors: Prediction input factors
        
    Returns:
        List of predicted disruptions with types and severities
    """
    disruptions: List[PredictedScheduleDisruption] = []
    
    for rule in SCHEDULE_DISRUPTION_RULES:
        if rule["condition"](factors):
            disruption_type = rule["disruption_type"]
            confidence = rule["confidence"]
            
            # Severity based on constraint score and disruption type
            severity = _calculate_disruption_severity(factors, disruption_type)
            
            # Adjust confidence by data quality
            if factors.user_history_sample_size < 5:
                confidence *= 0.6
            
            # Create disruption for each predicted day offset
            for day_offset in rule["day_offsets"]:
                affected_categories = _get_affected_categories(factors, disruption_type)
                
                disruptions.append(
                    PredictedScheduleDisruption(
                        day_offset=day_offset,
                        disruption_type=disruption_type,
                        severity=severity,
                        confidence=confidence * (1.0 - day_offset * 0.1),  # Decay confidence over time
                        affected_categories=affected_categories,
                        expected_duration_hours=_estimate_duration(disruption_type),
                        mitigation_available=_has_mitigation(disruption_type),
                    )
                )
    
    # Deduplicate and sort by day offset
    unique_disruptions = {}
    for d in disruptions:
        key = (d.day_offset, d.disruption_type.value)
        if key not in unique_disruptions or d.confidence > unique_disruptions[key].confidence:
            unique_disruptions[key] = d
    
    return sorted(unique_disruptions.values(), key=lambda d: d.day_offset)


def _calculate_disruption_severity(factors: PredictionFactors, disruption_type: DisruptionType) -> SeverityLevel:
    """Calculate disruption severity based on factors and type."""
    base_score = factors.current_constraint_score
    
    if base_score >= 9:
        return SeverityLevel.CRITICAL
    elif base_score >= 7:
        return SeverityLevel.HIGH
    elif base_score >= 5:
        return SeverityLevel.MODERATE
    else:
        return SeverityLevel.LOW


def _get_affected_categories(factors: PredictionFactors, disruption_type: DisruptionType) -> List[str]:
    """Get affected constraint categories for disruption type."""
    mapping = {
        DisruptionType.DEADLINE_PRESSURE: ["time", "mental"],
        DisruptionType.TRAVEL_DISRUPTION: ["logistical", "time", "environment"],
        DisruptionType.SOCIAL_CONFLICT: ["social", "mental"],
        DisruptionType.ENVIRONMENT_STRESS: ["environment", "physical"],
        DisruptionType.RECOVERY_NEEDED: ["energy", "mental"],
        DisruptionType.COMPOUNDING_LOAD: ["time", "energy", "mental"],
    }
    return mapping.get(disruption_type, [])


def _estimate_duration(disruption_type: DisruptionType) -> int:
    """Estimate duration in hours for disruption type."""
    durations = {
        DisruptionType.DEADLINE_PRESSURE: 240,  # 10 hours
        DisruptionType.TRAVEL_DISRUPTION: 480,  # 20 hours
        DisruptionType.SOCIAL_CONFLICT: 120,    # 5 hours
        DisruptionType.ENVIRONMENT_STRESS: 180,  # 7.5 hours
        DisruptionType.RECOVERY_NEEDED: 360,     # 15 hours
        DisruptionType.COMPOUNDING_LOAD: 600,    # 25 hours
    }
    return durations.get(disruption_type, 240)


def _has_mitigation(disruption_type: DisruptionType) -> bool:
    """Determine if disruption can be mitigated."""
    mitigatable = {
        DisruptionType.DEADLINE_PRESSURE: True,
        DisruptionType.TRAVEL_DISRUPTION: True,
        DisruptionType.SOCIAL_CONFLICT: False,
        DisruptionType.ENVIRONMENT_STRESS: False,
        DisruptionType.RECOVERY_NEEDED: True,
        DisruptionType.COMPOUNDING_LOAD: True,
    }
    return mitigatable.get(disruption_type, False)


# ============================================================================
# OPPORTUNITY WINDOW DETECTION
# ============================================================================

def detect_opportunity_windows(factors: PredictionFactors, forecast_window_days: int = 7) -> List[OpportunityWindow]:
    """
    Detect periods with lower constraint pressure.
    
    Identifies windows where user has flexibility to add activities or recovery.
    
    Args:
        factors: Prediction input factors
        forecast_window_days: Forecasting horizon
        
    Returns:
        List of opportunity windows with start day and duration
    """
    windows: List[OpportunityWindow] = []
    
    # First, identify base opportunities from rules
    for rule in OPPORTUNITY_RULES:
        if rule["condition"](factors):
            start_day = rule["start_offset"]
            duration = rule["duration_days"]
            flexibility = rule["flexibility"]
            
            # Ensure window fits within forecast horizon
            if start_day + duration <= forecast_window_days:
                windows.append(
                    OpportunityWindow(
                        start_day=start_day,
                        duration=duration,
                        confidence=0.8 - start_day * 0.1,  # Decay over time
                        flexibility_available=flexibility,
                        recommended_activities=_get_recommended_activities(factors),
                        constraint_categories_relaxed=_get_relaxed_categories(factors),
                    )
                )
    
    # Secondary: detect inverse of energy dips
    energy_dips = predict_energy_dips(factors)
    dip_days = {d.day_offset for d in energy_dips}
    
    for day in range(forecast_window_days):
        if day not in dip_days and not any(w.start_day <= day < w.start_day + w.duration for w in windows):
            # Found a potential opportunity day
            if not windows or windows[-1].start_day + windows[-1].duration < day:
                windows.append(
                    OpportunityWindow(
                        start_day=day,
                        duration=1,
                        confidence=0.6,
                        flexibility_available=0.5,
                        recommended_activities=[],
                        constraint_categories_relaxed=[],
                    )
                )
    
    # Merge adjacent windows
    merged_windows = _merge_adjacent_windows(windows)
    
    return sorted(merged_windows, key=lambda w: w.start_day)


def _merge_adjacent_windows(windows: List[OpportunityWindow]) -> List[OpportunityWindow]:
    """Merge adjacent or overlapping windows."""
    if not windows:
        return []
    
    sorted_windows = sorted(windows, key=lambda w: w.start_day)
    merged: List[OpportunityWindow] = []
    
    for window in sorted_windows:
        if merged and merged[-1].start_day + merged[-1].duration >= window.start_day:
            # Merge with previous
            merged[-1].duration = max(
                merged[-1].duration,
                window.start_day + window.duration - merged[-1].start_day
            )
            merged[-1].confidence = (merged[-1].confidence + window.confidence) / 2
        else:
            # New window
            merged.append(window)
    
    return merged


def _get_recommended_activities(factors: PredictionFactors) -> List[str]:
    """Get activities recommended for opportunity windows."""
    activities = []
    
    if factors.life_mode == "recovery":
        activities.append("Rest and recovery")
        activities.append("Stress-relief activities")
    
    if factors.adaptation_capacity > 0.7:
        activities.append("Optional skills development")
        activities.append("Social connection")
    
    if factors.current_constraint_score < 4:
        activities.append("Planning and organization")
        activities.append("Personal projects")
    
    return activities if activities else ["Light activity", "Rest"]


def _get_relaxed_categories(factors: PredictionFactors) -> List[str]:
    """Get constraint categories that relax during opportunity windows."""
    relaxed = []
    
    if factors.constraint_clusters.get("time", 0) == 0:
        relaxed.append("time")
    
    if factors.constraint_clusters.get("social", 0) == 0:
        relaxed.append("social")
    
    if factors.constraint_clusters.get("logistical", 0) == 0:
        relaxed.append("logistical")
    
    return relaxed if relaxed else ["energy"]


# ============================================================================
# FORECAST CONFIDENCE CALCULATION
# ============================================================================

def calculate_forecast_confidence(factors: PredictionFactors) -> float:
    """
    Calculate confidence score for entire forecast.
    """

    base_confidence = 0.5

    # Data availability: sample size
    if factors.user_history_sample_size >= 30:
        base_confidence += 0.3
    elif factors.user_history_sample_size >= 15:
        base_confidence += 0.2
    elif factors.user_history_sample_size >= 8:
        base_confidence += 0.1

    # Constraint stability
    score_range = (factors.current_constraint_score / 10.0)

    if score_range < 0.3:
        base_confidence += 0.15
    elif score_range < 0.6:
        base_confidence += 0.1

    # Life mode stability
    mode_stability = {
        "maintenance": 0.2,
        "growth": 0.1,
        "recovery": 0.05,
        "crisis": -0.3,
    }

    base_confidence += mode_stability.get(factors.life_mode, 0.0)

    # Recovery periods
    if factors.recovery_periods >= 3:
        base_confidence += 0.1

    # --- FIX: empty clusters reduce confidence ---
    if not factors.constraint_clusters or sum(factors.constraint_clusters.values()) == 0:
        base_confidence -= 0.7

    # Clamp
    confidence = max(0.1, min(1.0, base_confidence))
    return round(confidence, 2)


# ============================================================================
# FORECAST EXPIRY CALCULATION
# ============================================================================

def compute_forecast_expiry(
    forecast_window_days: int = 7,
    generated_at: datetime = None,
) -> Tuple[datetime, datetime]:
    """
    Calculate forecast generation and expiry times.
    
    Forecast expires after window period (or immediately if high disruption).
    
    Args:
        forecast_window_days: Window in days
        generated_at: Generation time (defaults to now)
        
    Returns:
        Tuple of (generated_at, expires_at)
    """
    if generated_at is None:
        generated_at = datetime.utcnow()
    
    expires_at = generated_at + timedelta(days=forecast_window_days)
    
    return generated_at, expires_at


# ============================================================================
# DATA QUALITY & VALIDATION
# ============================================================================

def validate_forecast_input(factors: PredictionFactors) -> ForecastValidationResult:
    """
    Validate input factors for forecasting.
    
    Checks for missing data, invalid ranges, and provides quality assessment.
    
    Args:
        factors: Input factors to validate
        
    Returns:
        Validation result with errors, warnings, and quality score
    """
    errors: List[str] = []
    warnings: List[str] = []
    quality_score = 1.0
    
    # Validate required fields
    if factors.current_constraint_score < 0 or factors.current_constraint_score > 10:
        errors.append("Constraint score out of range (0-10)")
    
    if factors.adaptation_capacity < 0 or factors.adaptation_capacity > 1:
        errors.append("Adaptation capacity out of range (0-1)")
    
    if not factors.life_mode:
        errors.append("Life mode required")
    
    # Check for data quality issues
    if factors.user_history_sample_size == 0:
        warnings.append("No historical data; confidence will be reduced")
        quality_score -= 0.4
    elif factors.user_history_sample_size < 10:
        warnings.append("Limited history (< 10 samples); forecast less reliable")
        quality_score -= 0.2
    
    if factors.recent_constraint_frequency == 0 and factors.overload_history == 0:
        warnings.append("No recent constraints; forecast may be overly optimistic")
        quality_score -= 0.15
    
    if not factors.constraint_clusters:
        warnings.append("No constraint clusters provided")
        quality_score -= 0.1
    
    # Calculate quality score
    quality_score = max(0.1, min(1.0, quality_score))
    
    return ForecastValidationResult(
        is_valid=len(errors) == 0,
        warnings=warnings,
        errors=errors,
        data_quality_score=quality_score,
    )


def calculate_data_quality_rating(sample_size: int, data_quality_score: float) -> str:
    """Calculate data quality rating (HIGH/MEDIUM/LOW)."""
    if sample_size >= 20 and data_quality_score >= 0.8:
        return "HIGH"
    elif sample_size >= 10 and data_quality_score >= 0.6:
        return "MEDIUM"
    else:
        return "LOW"
