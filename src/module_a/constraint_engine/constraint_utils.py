"""
Constraint Engine Utilities

Provides utility functions for constraint analysis:
- Normalization
- Validation
- Severity calculation
- Utility scoring functions

Module: Constraint Analysis & Processing
Part of: Constraint-First Wellness Agent
"""

import logging
import uuid
from typing import List, Dict, Any, Set, Tuple, Optional
from datetime import datetime

from constraint_models import (
    NormalizedConstraint,
    ConstraintCategory,
    ConstraintSeverityLevel,
    ConstraintValidationResult,
    ConstraintScoringMetrics,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CATEGORY ALIAS MAPPING
# ============================================================================

CATEGORY_ALIAS_MAP = {
    "sleep": "energy",
    "fatigue": "energy",
    "tired": "energy",
    "deadline": "time",
    "exam": "time",
    "meeting": "time",
    "travel": "logistical",
    "trip": "logistical",
    "noise": "environment",
    "crowded": "environment",
    "injury": "physical",
}


# ============================================================================
# CONFLICT RULES TABLE
# ============================================================================

CONFLICT_RULES = [
    {
        "name": "low_energy_high_time_pressure",
        "description": "Low energy constraint conflicts with high time pressure - difficult to meet both",
        "condition": lambda constraints: any(
            c.category.value == "energy" and c.severity >= 7 for c in constraints
        ) and any(
            c.category.value == "time" and c.severity >= 7 for c in constraints
        ),
    },
    {
        "name": "silent_environment_social_obligation",
        "description": "Silence requirement conflicts with social obligations - creates isolation risk",
        "condition": lambda constraints: any(
            c.category.value == "environment" for c in constraints
        ) and any(
            c.category.value == "social" for c in constraints
        ),
    },
    {
        "name": "highly_restrictive_low_adaptability",
        "description": "Highly restrictive constraints reduce adaptive capacity - vulnerability to disruption",
        "condition": lambda constraints: sum(1 for c in constraints if not c.flexible) >= 3,
    },
    {
        "name": "time_space_conflict",
        "description": "Time pressure combined with space constraints - limited options for activities",
        "condition": lambda constraints: any(
            c.category.value == "time" and c.severity >= 7 for c in constraints
        ) and any(
            c.category.value == "environment" and c.severity >= 6 for c in constraints
        ),
    },
    {
        "name": "physical_mental_conflict",
        "description": "High physical constraints combined with mental load - compounding fatigue",
        "condition": lambda constraints: any(
            c.category.value == "physical" and c.severity >= 7 for c in constraints
        ) and any(
            c.category.value == "mental" and c.severity >= 7 for c in constraints
        ),
    },
]


# ============================================================================
# NORMALIZATION
# ============================================================================

def normalize_constraints(
    raw_constraints: List[Dict[str, Any]],
    life_mode: str = "maintenance",
    validation_only: bool = False,
) -> Tuple[List[NormalizedConstraint], ConstraintValidationResult]:
    """
    Normalize raw constraints into structured NormalizedConstraint objects.

    Args:
        raw_constraints: List of raw constraint dicts from user input
        life_mode: Current life mode (maintenance, growth, recovery, crisis)
        validation_only: If True, only validate without normalizing

    Returns:
        Tuple of (normalized constraints, validation result)
    """
    validation_result = ConstraintValidationResult(is_valid=True)
    normalized = []
    seen_ids: Set[str] = set()

    for idx, raw_constraint in enumerate(raw_constraints):
        # Validate structure
        if not isinstance(raw_constraint, dict):
            validation_result.is_valid = False
            validation_result.errors.append(
                f"Constraint {idx}: Expected dict, got {type(raw_constraint)}"
            )
            continue

        # Extract and validate required fields
        name = raw_constraint.get("name", f"Unnamed Constraint {idx}").strip()
        category = raw_constraint.get("category", "logistical").lower()
        severity = raw_constraint.get("severity", 5)
        description = raw_constraint.get("description", "")
        flexible = raw_constraint.get("flexible", False)
        constraint_id = raw_constraint.get("id", str(uuid.uuid4()))

        # Validate severity
        try:
            severity = int(severity)
            if severity < 1 or severity > 10:
                validation_result.warnings.append(
                    f"Constraint '{name}': Severity {severity} out of range, clamped to 1-10"
                )
                severity = max(1, min(10, severity))
                validation_result.invalid_severities.append(name)
        except (TypeError, ValueError):
            validation_result.is_valid = False
            validation_result.errors.append(
                f"Constraint '{name}': Invalid severity value {severity}"
            )
            continue

        # Map category aliases to canonical categories
        if category in CATEGORY_ALIAS_MAP:
            category = CATEGORY_ALIAS_MAP[category]

        # Validate category
        try:
            category_enum = ConstraintCategory[category.upper()]
        except KeyError:
            validation_result.warnings.append(
                f"Constraint '{name}': Unknown category '{category}', defaulting to 'logistical'"
            )
            validation_result.missing_categories.append(category)
            category_enum = ConstraintCategory.LOGISTICAL

        # Check for duplicates
        if constraint_id in seen_ids:
            validation_result.warnings.append(
                f"Constraint '{name}': Duplicate ID {constraint_id}"
            )
            validation_result.duplicate_ids.append(constraint_id)
            # Generate new ID for duplicate
            constraint_id = str(uuid.uuid4())

        seen_ids.add(constraint_id)

        if not validation_only:
            # Calculate adjustment factor based on life mode
            adjustment_factor = _calculate_life_mode_adjustment(life_mode)

            normalized_constraint = NormalizedConstraint(
                id=constraint_id,
                name=name,
                category=category_enum,
                description=description,
                severity=severity,
                flexible=flexible,
                original_severity=severity,
                adjustment_factor=adjustment_factor,
                metadata=raw_constraint.get("metadata", {}),
            )
            normalized.append(normalized_constraint)

    return normalized, validation_result


def _calculate_life_mode_adjustment(life_mode: str) -> float:
    """
    Calculate severity adjustment factor based on life mode.

    Args:
        life_mode: One of "maintenance", "growth", "recovery", "crisis"

    Returns:
        Adjustment multiplier
    """
    adjustments = {
        "maintenance": 1.0,
        "growth": 0.9,  # Constraints feel less severe during growth
        "recovery": 1.2,  # Constraints feel more severe during recovery
        "crisis": 1.5,  # Constraints are amplified during crisis
    }
    return adjustments.get(life_mode.lower(), 1.0)


def validate_normalized_constraint(constraint: NormalizedConstraint) -> List[str]:
    """
    Validate a single normalized constraint.

    Args:
        constraint: NormalizedConstraint to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not constraint.id or not constraint.id.strip():
        errors.append("Constraint ID cannot be empty")

    if not constraint.name or not constraint.name.strip():
        errors.append("Constraint name cannot be empty")

    if constraint.severity < 1 or constraint.severity > 10:
        errors.append(f"Severity must be 1-10, got {constraint.severity}")

    if not isinstance(constraint.flexible, bool):
        errors.append("flexibility must be boolean")

    if constraint.adjustment_factor < 0.5 or constraint.adjustment_factor > 1.5:
        errors.append(
            f"Adjustment factor must be 0.5-1.5, got {constraint.adjustment_factor}"
        )

    return errors


# ============================================================================
# SEVERITY SCORING
# ============================================================================


def calculate_base_constraint_score(constraints: List[NormalizedConstraint]) -> float:
    """
    Calculate base constraint score from weighted average of severities.

    Args:
        constraints: List of normalized constraints

    Returns:
        Score from 0-10
    """
    if not constraints:
        return 0.0

    total_severity = sum(c.severity * c.adjustment_factor for c in constraints)
    weighted_average = total_severity / len(constraints)

    # Cap at 10
    return min(10.0, weighted_average)


def calculate_constraint_score(
    constraints: List[NormalizedConstraint],
    life_mode: str = "maintenance",
    recent_overload_count: int = 0,
    conflict_count: int = 0,
    user_adaptive_capacity: float = 0.5,
) -> ConstraintScoringMetrics:
    """
    Calculate comprehensive constraint score with multiple factors.

    Args:
        constraints: List of normalized constraints
        life_mode: Current life mode
        recent_overload_count: Number of recent overloads (0-3)
        conflict_count: Number of constraint conflicts
        user_adaptive_capacity: User's ability to adapt (0-1, higher = more adaptable)

    Returns:
        ConstraintScoringMetrics with detailed scoring breakdown
    """
    # Base score
    base_score = calculate_base_constraint_score(constraints)

    # Life mode multiplier
    life_mode_multiplier = _calculate_life_mode_adjustment(life_mode)

    # Recent overload factor (max 0.5 additional points)
    recent_overload_factor = min(0.5, recent_overload_count * 0.2)

    # Constraint count factor (diminishing returns)
    count_factor = min(0.5, len(constraints) * 0.05)

    # Conflict penalty (each conflict adds to score)
    conflict_penalty = min(2.0, conflict_count * 0.3)

    # Adaptability discount (reduces score if user has high adaptive capacity)
    adaptability_discount = (1 - user_adaptive_capacity) * 0.2

    # Calculate final score
    final_score = (
        (base_score * life_mode_multiplier)
        + recent_overload_factor
        + count_factor
        + conflict_penalty
        - adaptability_discount
    )

    # Clamp to 0-10 range (CRITICAL: Ensure score is always valid)
    final_score = max(0.0, min(10.0, final_score))

    # Confidence is higher with more data points
    confidence = min(
        1.0,
        0.5 + (len(constraints) * 0.1) + (0.2 if recent_overload_count > 0 else 0),
    )

    return ConstraintScoringMetrics(
        base_severity_score=base_score,
        life_mode_multiplier=life_mode_multiplier,
        recent_overload_factor=recent_overload_factor,
        constraint_count_factor=count_factor,
        conflict_penalty=conflict_penalty,
        final_score=final_score,
        confidence=confidence,
    )


# ============================================================================
# CLUSTERING
# ============================================================================


def cluster_constraints(
    constraints: List[NormalizedConstraint],
) -> Dict[str, List[str]]:
    """
    Cluster related constraints by category and correlation.
    Ensures cluster_count <= constraint_count to prevent cluster explosion.

    Args:
        constraints: List of normalized constraints

    Returns:
        Dict mapping cluster names to lists of constraint IDs
    """
    clusters: Dict[str, List[str]] = {}

    # Group by category first
    for constraint in constraints:
        category = constraint.category.value
        if category not in clusters:
            clusters[category] = []
        clusters[category].append(constraint.id)

    # Create composite clusters only if patterns exist (>= 2 constraints in each group)
    time_constraints = clusters.get("time", []) + clusters.get("logistical", [])
    if len(time_constraints) >= 2:
        clusters["time_pressure"] = time_constraints

    environment_constraints = clusters.get("environment", []) + clusters.get(
        "social", []
    )
    if len(environment_constraints) >= 2:
        clusters["environment_social"] = environment_constraints

    energy_constraints = clusters.get("energy", []) + clusters.get("physical", [])
    if len(energy_constraints) >= 2:
        clusters["energy_physical"] = energy_constraints

    # Ensure cluster count does not exceed constraint count
    if len(clusters) > len(constraints):
        # Remove composite clusters if they would exceed constraint count
        if "time_pressure" in clusters:
            del clusters["time_pressure"]
        if "environment_social" in clusters:
            del clusters["environment_social"]
        if "energy_physical" in clusters:
            del clusters["energy_physical"]

    return clusters


def get_cluster_summary(
    clusters: Dict[str, List[str]], constraints_map: Dict[str, NormalizedConstraint]
) -> Dict[str, Dict[str, Any]]:
    """
    Generate summary statistics for constraint clusters.

    Args:
        clusters: Dict of cluster_name -> constraint_ids
        constraints_map: Dict mapping constraint ID to NormalizedConstraint

    Returns:
        Dict with cluster summaries
    """
    summary = {}

    for cluster_name, constraint_ids in clusters.items():
        cluster_constraints = [
            constraints_map[cid] for cid in constraint_ids if cid in constraints_map
        ]

        if not cluster_constraints:
            continue

        severities = [c.severity for c in cluster_constraints]
        flexibility = [float(not c.flexible) for c in cluster_constraints]

        summary[cluster_name] = {
            "count": len(cluster_constraints),
            "avg_severity": sum(severities) / len(severities),
            "max_severity": max(severities),
            "min_severity": min(severities),
            "rigidity_score": sum(flexibility) / len(flexibility),  # 0=all flexible, 1=all rigid
            "constraint_names": [c.name for c in cluster_constraints],
        }

    return summary


# ============================================================================
# CONFLICT DETECTION
# ============================================================================


def detect_constraint_conflicts(
    constraints: List[NormalizedConstraint],
) -> List[str]:
    """
    Detect incompatible constraint combinations using rule-based matching.

    Args:
        constraints: List of normalized constraints

    Returns:
        List of conflict descriptions
    """
    conflicts = []

    # Iterate through conflict rules and check each one
    for rule in CONFLICT_RULES:
        try:
            if rule["condition"](constraints):
                conflicts.append(rule["description"])
        except Exception as e:
            logger.warning(f"Error evaluating conflict rule {rule['name']}: {e}")

    return conflicts


# ============================================================================
# PRESSURE CLASSIFICATION
# ============================================================================


def classify_constraint_pressure(score: float) -> ConstraintSeverityLevel:
    """
    Convert constraint score to severity level.

    Args:
        score: Constraint score 0-10

    Returns:
        ConstraintSeverityLevel (LOW, MODERATE, HIGH, CRITICAL)
    """
    if score < 3:
        return ConstraintSeverityLevel.LOW
    elif score < 5:
        return ConstraintSeverityLevel.MODERATE
    elif score < 7:
        return ConstraintSeverityLevel.HIGH
    else:
        return ConstraintSeverityLevel.CRITICAL


def classify_adaptability(
    constraints: List[NormalizedConstraint], conflicts: List[str]
) -> Tuple[str, float]:
    """
    Classify how adaptable the constraint situation is.

    Args:
        constraints: List of constraints
        conflicts: List of detected conflicts

    Returns:
        Tuple of (adaptability_rating, flexibility_score 0-1)
    """
    if not constraints:
        return "high", 1.0

    # Calculate flexibility score (1 = all flexible, 0 = all rigid)
    flexible_count = sum(1 for c in constraints if c.flexible)
    flexibility_score = flexible_count / len(constraints) if constraints else 1.0

    # Adjust by conflict count
    conflict_penalty = min(0.3, len(conflicts) * 0.1)
    adjusted_flexibility = max(0, flexibility_score - conflict_penalty)

    # Classify
    if adjusted_flexibility > 0.6:
        rating = "high"
    elif adjusted_flexibility > 0.3:
        rating = "moderate"
    else:
        rating = "low"

    return rating, adjusted_flexibility


# ============================================================================
# ANALYSIS SUMMARY
# ============================================================================


def build_constraint_summary(
    constraints: List[NormalizedConstraint],
    clusters: Dict[str, List[str]],
    conflicts: List[str],
    score: float,
    pressure_level: ConstraintSeverityLevel,
) -> Dict[str, Any]:
    """
    Build comprehensive constraint summary.

    Args:
        constraints: List of normalized constraints
        clusters: Constraint clusters
        conflicts: Detected conflicts
        score: Overall constraint score
        pressure_level: Pressure level classification

    Returns:
        Dict with complete summary
    """
    categories = set(c.category.value for c in constraints)

    return {
        "total_constraints": len(constraints),
        "categories_present": list(categories),
        "avg_severity": (
            sum(c.severity for c in constraints) / len(constraints)
            if constraints
            else 0
        ),
        "max_severity": max(
            (c.severity for c in constraints), default=0
        ),
        "rigid_constraints": sum(1 for c in constraints if not c.flexible),
        "flexible_constraints": sum(1 for c in constraints if c.flexible),
        "cluster_count": len(clusters),
        "clusters": list(clusters.keys()),
        "conflict_count": len(conflicts),
        "constraint_score": round(score, 2),
        "pressure_level": pressure_level.value,
        "timestamp": datetime.utcnow().isoformat(),
    }
