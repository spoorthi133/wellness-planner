"""
Constraint Analyzer

Orchestrates constraint analysis pipeline.
Coordinates normalization, scoring, clustering, and conflict detection.

Module: Constraint Analysis & Processing
Part of: Constraint-First Wellness Agent
"""

import logging
from typing import Dict, List, Any, Optional

from constraint_models import (
    NormalizedConstraint,
    ConstraintAnalysisResult,
    ConstraintAnalysisContext,
    ConstraintValidationResult,
    ConstraintSeverityLevel,
)
from constraint_utils import (
    normalize_constraints,
    validate_normalized_constraint,
    calculate_base_constraint_score,
    calculate_constraint_score,
    cluster_constraints,
    get_cluster_summary,
    detect_constraint_conflicts,
    classify_constraint_pressure,
    classify_adaptability,
    build_constraint_summary,
)

logger = logging.getLogger(__name__)


class ConstraintAnalyzer:
    """
    Main constraint analysis orchestrator.

    Handles the complete constraint analysis workflow:
    1. Normalization and validation
    2. Calculation of constraint score
    3. Clustering related constraints
    4. Conflict detection
    5. Pressure level classification
    """

    def __init__(self, context: Optional[ConstraintAnalysisContext] = None):
        """
        Initialize analyzer with optional context.

        Args:
            context: Optional ConstraintAnalysisContext with user background
        """
        self.context = context
        self.normalized_constraints: List[NormalizedConstraint] = []
        self.validation_result: Optional[ConstraintValidationResult] = None

    def analyze(
        self,
        raw_constraints: List[Dict[str, Any]],
        life_mode: str = "maintenance",
        recent_overload_count: int = 0,
        user_adaptive_capacity: float = 0.5,
    ) -> ConstraintAnalysisResult:
        """
        Execute complete constraint analysis pipeline.

        Args:
            raw_constraints: Raw constraint data from user input
            life_mode: Current life mode
            recent_overload_count: Number of recent overloads (0-3)
            user_adaptive_capacity: User's adaptive capacity (0-1)

        Returns:
            ConstraintAnalysisResult with complete analysis
        """
        logger.info(f"Starting constraint analysis for {len(raw_constraints)} constraints")

        # Step 1: Normalize and validate
        self.normalized_constraints, self.validation_result = normalize_constraints(
            raw_constraints, life_mode=life_mode
        )

        if self.validation_result.errors:
            logger.warning(
                f"Validation errors found: {self.validation_result.errors}"
            )

        if not self.normalized_constraints:
            logger.info("No valid constraints after normalization")
            return self._create_empty_result()

        # Step 2: Validate individual constraints
        for constraint in self.normalized_constraints:
            validation_errors = validate_normalized_constraint(constraint)
            if validation_errors:
                logger.warning(
                    f"Constraint '{constraint.name}' validation errors: {validation_errors}"
                )

        # Step 3: Calculate constraint score
        scoring_metrics = calculate_constraint_score(
            self.normalized_constraints,
            life_mode=life_mode,
            recent_overload_count=recent_overload_count,
            conflict_count=0,  # Will update after conflict detection
            user_adaptive_capacity=user_adaptive_capacity,
        )
        logger.debug(f"Constraint score calculated: {scoring_metrics.final_score}")

        # Step 4: Cluster constraints
        clusters = cluster_constraints(self.normalized_constraints)
        logger.debug(f"Constraints clustered into {len(clusters)} clusters")

        # Step 5: Detect conflicts (CORRECTION 5: rule-table based)
        conflicts = detect_constraint_conflicts(self.normalized_constraints)
        logger.debug(f"Detected {len(conflicts)} conflicts")

        # Recalculate score with conflict penalty
        if conflicts:
            scoring_metrics = calculate_constraint_score(
                self.normalized_constraints,
                life_mode=life_mode,
                recent_overload_count=recent_overload_count,
                conflict_count=len(conflicts),
                user_adaptive_capacity=user_adaptive_capacity,
            )

        # Step 6: Classify pressure level  
        pressure_level = classify_constraint_pressure(scoring_metrics.final_score)
        logger.debug(f"Pressure level classified as: {pressure_level.value}")

        # Step 7: Classify adaptability
        adaptability_rating, flexibility_score = classify_adaptability(
            self.normalized_constraints, conflicts
        )

        # Step 8: Build summary
        constraint_summary = build_constraint_summary(
            self.normalized_constraints,
            clusters,
            conflicts,
            scoring_metrics.final_score,
            pressure_level,
        )

        # Step 9: Build cluster details
        constraints_map = {c.id: c for c in self.normalized_constraints}
        cluster_summary = get_cluster_summary(clusters, constraints_map)

        # Step 10: Convert to result object
        result = ConstraintAnalysisResult(
            constraint_summary=constraint_summary,
            constraint_score=scoring_metrics.final_score,
            constraint_clusters=clusters,
            constraint_conflicts=conflicts,
            constraint_pressure_level=pressure_level,
            constraint_count=len(self.normalized_constraints),
            constraint_categories_present=[
                c.category.value for c in self.normalized_constraints
            ],
            normalized_constraints=[
                self._constraint_to_dict(c) for c in self.normalized_constraints
            ],
            scoring_metrics=scoring_metrics,
            cluster_details=[
                {
                    "cluster_name": name,
                    "details": summary,
                }
                for name, summary in cluster_summary.items()
            ],
            conflict_details=[
                {"conflict_description": c, "index": i}
                for i, c in enumerate(conflicts)
            ],
            flexibility_score=flexibility_score,
            adaptability_rating=adaptability_rating,
        )

        logger.info(
            f"Constraint analysis complete. Score: {result.constraint_score}, "
            f"Pressure: {result.constraint_pressure_level.value}"
        )

        return result

    def _create_empty_result(self) -> ConstraintAnalysisResult:
        """Create an empty analysis result when no constraints present."""
        return ConstraintAnalysisResult(
            constraint_summary={
                "total_constraints": 0,
                "categories_present": [],
                "avg_severity": 0,
                "max_severity": 0,
                "rigid_constraints": 0,
                "flexible_constraints": 0,
                "cluster_count": 0,
                "clusters": [],
                "conflict_count": 0,
                "constraint_score": 0,
                "pressure_level": "LOW",
            },
            constraint_score=0.0,
            constraint_clusters={},
            constraint_conflicts=[],
            constraint_pressure_level=ConstraintSeverityLevel.LOW,
            constraint_count=0,
            constraint_categories_present=[],
            flexibility_score=1.0,
            adaptability_rating="high",
        )

    def _constraint_to_dict(self, constraint: NormalizedConstraint) -> Dict[str, Any]:
        """Convert NormalizedConstraint to dict for serialization."""
        return {
            "id": constraint.id,
            "name": constraint.name,
            "category": constraint.category.value,
            "description": constraint.description,
            "severity": constraint.severity,
            "original_severity": constraint.original_severity,
            "adjustment_factor": constraint.adjustment_factor,
            "flexible": constraint.flexible,
            "created_at": constraint.created_at.isoformat(),
            "updated_at": constraint.updated_at.isoformat(),
            "metadata": constraint.metadata,
        }

    def get_normalized_constraints(self) -> List[NormalizedConstraint]:
        """Get the last set of normalized constraints."""
        return self.normalized_constraints

    def get_validation_result(self) -> Optional[ConstraintValidationResult]:
        """Get the validation result from last analysis."""
        return self.validation_result

    @staticmethod
    def estimate_system_impact(
        analysis_result: ConstraintAnalysisResult,
    ) -> Dict[str, Any]:
        """
        Estimate system-wide impact of constraints.

        Args:
            analysis_result: ConstraintAnalysisResult to analyze

        Returns:
            Dict with impact estimates for downstream nodes
        """
        impact = {
            "forecast_difficulty": "easy"
            if analysis_result.constraint_score < 3
            else "moderate"
            if analysis_result.constraint_score < 6
            else "challenging"
            if analysis_result.constraint_score < 8
            else "critical",
            "energy_budget_adjustment": _calculate_energy_adjustment(
                analysis_result.constraint_score
            ),
            "planning_complexity": int(
                analysis_result.constraint_count * 0.5 + len(analysis_result.constraint_conflicts) * 0.5
            ),
            "adaptation_capacity_reduced": analysis_result.flexibility_score < 0.4,
            "recommended_plan_conservatism": min(
                100, int(analysis_result.constraint_score * 10)
            ),
        }
        return impact

    @staticmethod
    def generate_analysis_report(
        analysis_result: ConstraintAnalysisResult,
    ) -> str:
        """
        Generate human-readable analysis report.

        Args:
            analysis_result: ConstraintAnalysisResult to report on

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("CONSTRAINT ANALYSIS REPORT")
        report.append("=" * 60)

        # Summary
        report.append("\nSUMMARY:")
        report.append(f"  Total Constraints: {analysis_result.constraint_count}")
        report.append(
            f"  Categories: {', '.join(analysis_result.constraint_categories_present)}"
        )
        report.append(f"  Constraint Score: {analysis_result.constraint_score:.1f}/10")
        report.append(f"  Pressure Level: {analysis_result.constraint_pressure_level.value}")
        report.append(
            f"  Adaptability: {analysis_result.adaptability_rating} "
            f"({analysis_result.flexibility_score:.0%})"
        )

        # Detailed summary
        if analysis_result.constraint_summary:
            report.append("\nDETAILS:")
            for key, value in analysis_result.constraint_summary.items():
                if key != "timestamp":
                    report.append(f"  {key}: {value}")

        # Clusters
        if analysis_result.cluster_details:
            report.append("\nCONSTRAINT CLUSTERS:")
            for cluster_info in analysis_result.cluster_details:
                name = cluster_info["cluster_name"]
                details = cluster_info["details"]
                report.append(f"  {name}:")
                report.append(
                    f"    Count: {details['count']}, "
                    f"Avg Severity: {details['avg_severity']:.1f}"
                )

        # Conflicts
        if analysis_result.constraint_conflicts:
            report.append("\nDETECTED CONFLICTS:")
            for conflict in analysis_result.constraint_conflicts:
                report.append(f"  ⚠ {conflict}")

        # Impact
        impact = ConstraintAnalyzer.estimate_system_impact(analysis_result)
        report.append("\nSYSTEM IMPACT:")
        for key, value in impact.items():
            report.append(f"  {key}: {value}")

        report.append("\n" + "=" * 60)
        return "\n".join(report)


def _calculate_energy_adjustment(constraint_score: float) -> float:
    """
    Calculate how much to reduce energy budget based on constraint score.

    Args:
        constraint_score: Overall constraint score 0-10

    Returns:
        Adjustment percentage (0.5 = 50% reduction)
    """
    if constraint_score < 3:
        return 1.0  # No reduction
    elif constraint_score < 5:
        return 0.9  # 10% reduction
    elif constraint_score < 7:
        return 0.8  # 20% reduction
    else:
        return 0.7  # 30% reduction
