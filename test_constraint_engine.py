"""
Constraint Engine Integration Tests

Tests for the constraint engine module demonstrating:
1. Constraint normalization
2. Severity scoring
3. Constraint clustering
4. Conflict detection
5. Pressure level classification
6. LangGraph node integration

Run: python test_constraint_engine.py
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add module to path
module_path = Path(__file__).parent / "src" / "module_a" / "constraint_engine"
sys.path.insert(0, str(module_path))

from constraint_models import (
    ConstraintCategory,
    ConstraintSeverityLevel,
    NormalizedConstraint,
)
from constraint_analyzer import ConstraintAnalyzer
from constraint_node import constraint_analyzer_node
from constraint_utils import (
    normalize_constraints,
    calculate_constraint_score,
    cluster_constraints,
    detect_constraint_conflicts,
    classify_constraint_pressure,
    classify_adaptability,
)


def print_section(title: str):
    """Print a test section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def test_normalization():
    """Test constraint normalization."""
    print_section("TEST 1: Constraint Normalization")

    raw_constraints = [
        {"name": "Exam week", "category": "time", "severity": 8},
        {"name": "Low sleep", "category": "physical", "severity": 7},
        {"name": "Shared dorm room", "category": "environment", "severity": 6},
        {"name": "Invalid severity", "category": "mental", "severity": 15},
        {"name": "Incomplete", "category": "social"},  # Missing severity
    ]

    normalized, validation = normalize_constraints(
        raw_constraints, life_mode="maintenance"
    )

    print(f"Input constraints: {len(raw_constraints)}")
    print(f"Normalized constraints: {len(normalized)}")
    print(f"Validation errors: {len(validation.errors)}")
    print(f"Validation warnings: {len(validation.warnings)}")

    print("\nNormalized constraints:")
    for constraint in normalized:
        print(
            f"  - {constraint.name} ({constraint.category.value}): "
            f"severity {constraint.severity}, flexible: {constraint.flexible}"
        )

    if validation.errors:
        print("\nValidation errors:")
        for error in validation.errors:
            print(f"  ⚠ {error}")

    if validation.warnings:
        print("\nValidation warnings:")
        for warning in validation.warnings:
            print(f"  ⓘ {warning}")

    assert len(normalized) == 5, "Should have normalized all 5 constraints (with defaults applied)"
    assert len(validation.errors) == 0, "Should have no errors"
    assert len(validation.warnings) == 1, "Should have 1 warning for clamped severity"
    print("\n✓ Normalization test passed")


def test_scoring():
    """Test constraint scoring."""
    print_section("TEST 2: Constraint Scoring")

    raw_constraints = [
        {"name": "High time pressure", "category": "time", "severity": 9},
        {"name": "Moderate energy", "category": "energy", "severity": 6},
        {"name": "Low social capacity", "category": "social", "severity": 5},
    ]

    normalized, _ = normalize_constraints(raw_constraints, life_mode="recovery")

    metrics = calculate_constraint_score(
        normalized,
        life_mode="recovery",
        recent_overload_count=1,
        conflict_count=0,
        user_adaptive_capacity=0.4,
    )

    print(f"Base severity score: {metrics.base_severity_score:.2f}")
    print(f"Life mode multiplier: {metrics.life_mode_multiplier:.2f}")
    print(f"Recent overload factor: {metrics.recent_overload_factor:.2f}")
    print(f"Constraint count factor: {metrics.constraint_count_factor:.2f}")
    print(f"Final score: {metrics.final_score:.2f}/10")
    print(f"Confidence: {metrics.confidence:.0%}")

    assert 0 <= metrics.final_score <= 10, "Score should be 0-10"
    assert metrics.confidence > 0, "Confidence should be positive"
    print("\n✓ Scoring test passed")


def test_clustering():
    """Test constraint clustering."""
    print_section("TEST 3: Constraint Clustering")

    raw_constraints = [
        {"name": "Exam week", "category": "time", "severity": 8},
        {"name": "Project deadline", "category": "logistical", "severity": 7},
        {"name": "Shared room", "category": "environment", "severity": 6},
        {"name": "Group project work", "category": "social", "severity": 5},
        {"name": "Low energy", "category": "energy", "severity": 7},
        {"name": "Poor sleep", "category": "physical", "severity": 6},
    ]

    normalized, _ = normalize_constraints(raw_constraints)
    clusters = cluster_constraints(normalized)

    print(f"Total constraints: {len(normalized)}")
    print(f"Clusters created: {len(clusters)}")
    print("\nCluster breakdown:")
    for cluster_name, constraint_ids in clusters.items():
        constraint_names = [
            c.name for c in normalized if c.id in constraint_ids
        ]
        print(f"  {cluster_name}: {len(constraint_ids)} constraints")
        for name in constraint_names:
            print(f"    - {name}")

    assert len(clusters) > 0, "Should create clusters"
    print("\n✓ Clustering test passed")


def test_conflict_detection():
    """Test constraint conflict detection."""
    print_section("TEST 4: Conflict Detection")

    # High-conflict scenario
    raw_constraints = [
        {"name": "Exam week (high time pressure)", "category": "time", "severity": 9},
        {"name": "Chronic fatigue (energy crisis)", "category": "energy", "severity": 8},
        {"name": "Needs silence to focus", "category": "environment", "severity": 7},
        {"name": "Shared dorm room", "category": "environment", "severity": 6},
        {"name": "Active social schedule", "category": "social", "severity": 6},
    ]

    normalized, _ = normalize_constraints(raw_constraints)
    conflicts = detect_constraint_conflicts(normalized)

    print(f"Total constraints: {len(normalized)}")
    print(f"Conflicts detected: {len(conflicts)}")

    if conflicts:
        print("\nDetected conflicts:")
        for i, conflict in enumerate(conflicts, 1):
            print(f"  {i}. {conflict}")
    else:
        print("\nNo conflicts detected (constraints are compatible)")

    print("\n✓ Conflict detection test passed")


def test_pressure_classification():
    """Test pressure level classification."""
    print_section("TEST 5: Pressure Level Classification")

    test_scores = [2.0, 4.5, 6.2, 8.5, 10.0]

    print("Pressure level classification:")
    for score in test_scores:
        level = classify_constraint_pressure(score)
        print(f"  Score {score:.1f} → {level.value}")

    # Verify boundaries
    assert (
        classify_constraint_pressure(2.0) == ConstraintSeverityLevel.LOW
    ), "2.0 should be LOW"
    assert (
        classify_constraint_pressure(4.5) == ConstraintSeverityLevel.MODERATE
    ), "4.5 should be MODERATE"
    assert (
        classify_constraint_pressure(8.5) == ConstraintSeverityLevel.CRITICAL
    ), "8.5 should be CRITICAL"

    print("\n✓ Pressure classification test passed")


def test_adaptability():
    """Test adaptability classification."""
    print_section("TEST 6: Adaptability Classification")

    # Flexible constraints, no conflicts
    flexible_constraints = [
        NormalizedConstraint(
            id="1",
            name="Flexible time",
            category=ConstraintCategory.TIME,
            severity=5,
            flexible=True,
            description="",
            original_severity=5,
        ),
        NormalizedConstraint(
            id="2",
            name="Some work",
            category=ConstraintCategory.ENERGY,
            severity=4,
            flexible=True,
            description="",
            original_severity=4,
        ),
    ]

    rigid_constraints = [
        NormalizedConstraint(
            id="3",
            name="Fixed schedule",
            category=ConstraintCategory.TIME,
            severity=8,
            flexible=False,
            description="",
            original_severity=8,
        ),
        NormalizedConstraint(
            id="4",
            name="Severe limitation",
            category=ConstraintCategory.PHYSICAL,
            severity=9,
            flexible=False,
            description="",
            original_severity=9,
        ),
    ]

    rating1, score1 = classify_adaptability(flexible_constraints, [])
    rating2, score2 = classify_adaptability(rigid_constraints, ["conflict1", "conflict2"])

    print(f"Flexible constraints:")
    print(f"  Adaptability rating: {rating1}")
    print(f"  Flexibility score: {score1:.0%}")

    print(f"\nRigid constraints with conflicts:")
    print(f"  Adaptability rating: {rating2}")
    print(f"  Flexibility score: {score2:.0%}")

    assert score1 > score2, "Flexible should have higher score than rigid"
    print("\n✓ Adaptability test passed")


def test_full_analysis():
    """Test complete constraint analysis pipeline."""
    print_section("TEST 7: Full Analysis Pipeline")

    # Create a realistic scenario
    raw_constraints = [
        {
            "name": "Exam prep (2 weeks)",
            "category": "time",
            "severity": 8,
            "flexible": False,
            "description": "Heavy study load for midterms",
        },
        {
            "name": "Low energy",
            "category": "energy",
            "severity": 7,
            "flexible": False,
            "description": "Recovering from illness",
        },
        {
            "name": "Shared living space",
            "category": "environment",
            "severity": 5,
            "flexible": False,
            "description": "Limited private space for focus",
        },
        {
            "name": "New parent responsibilities",
            "category": "social",
            "severity": 7,
            "flexible": False,
            "description": "Caring for newborn",
        },
        {
            "name": "Work deadlines",
            "category": "logistical",
            "severity": 7,
            "flexible": False,
            "description": "Project delivery next week",
        },
    ]

    analyzer = ConstraintAnalyzer()

    result = analyzer.analyze(
        raw_constraints=raw_constraints,
        life_mode="recovery",
        recent_overload_count=2,
        user_adaptive_capacity=0.35,
    )

    print(f"Analysis complete!")
    print(f"\nResults:")
    print(f"  Constraints analyzed: {result.constraint_count}")
    print(f"  Categories present: {', '.join(result.constraint_categories_present)}")
    print(f"  Overall score: {result.constraint_score:.1f}/10")
    print(f"  Pressure level: {result.constraint_pressure_level.value}")
    print(f"  Adaptability: {result.adaptability_rating} ({result.flexibility_score:.0%})")
    print(f"  Clusters found: {len(result.constraint_clusters)}")
    print(f"  Conflicts detected: {len(result.constraint_conflicts)}")

    if result.constraint_clusters:
        print(f"\n  Clusters:")
        for name, ids in result.constraint_clusters.items():
            print(f"    - {name}: {len(ids)} constraints")

    if result.constraint_conflicts:
        print(f"\n  Conflicts:")
        for i, conflict in enumerate(result.constraint_conflicts[:3], 1):
            print(f"    {i}. {conflict}")

    # Test system impact estimation
    impact = ConstraintAnalyzer.estimate_system_impact(result)
    print(f"\nSystem Impact Estimates:")
    print(f"  Forecast difficulty: {impact['forecast_difficulty']}")
    print(f"  Energy budget adjustment: {impact['energy_budget_adjustment']:.0%}")
    print(f"  Planning complexity: {impact['planning_complexity']}")
    print(f"  Adaptation capacity reduced: {impact['adaptation_capacity_reduced']}")

    print("\n✓ Full analysis test passed")


def test_langgraph_node():
    """Test LangGraph node integration."""
    print_section("TEST 8: LangGraph Node Integration")

    # Create state dict resembling AgentState output
    state = {
        "user_id": "user123",
        "session_id": "session456",
        "constraints": [
            {"name": "Time pressure", "category": "time", "severity": 8},
            {"name": "Energy low", "category": "energy", "severity": 7},
            {"name": "Shared space", "category": "environment", "severity": 5},
        ],
        "life_mode": "maintenance",
        "environment_context": {
            "indoor_only": False,
            "small_space": True,
            "shared_room": True,
        },
        "user_history": {
            "total_plans_generated": 5,
            "average_plan_completion": 0.6,
        },
        "system_flags": {
            "emergency_mode": False,
        },
        "execution_trace": [],
    }

    print(f"Input state:")
    print(f"  User ID: {state['user_id']}")
    print(f"  Constraints: {len(state['constraints'])}")
    print(f"  Life mode: {state['life_mode']}")

    updated_state = constraint_analyzer_node(state)

    print(f"\nOutput state updates (CORRECTION 1: no constraint_analysis field):")
    print(f"  Forecast data present: {'forecast_data' in updated_state}")
    print(f"  Initial constraint map present: {'initial_constraint_map' in updated_state.get('forecast_data', {})}")
    print(f"  System flags updated: {'constraint_pressure_level' in updated_state.get('system_flags', {})}")
    print(f"  Overload detected: {updated_state['system_flags']['overload_detected']}")
    print(f"  Pressure level: {updated_state['system_flags']['constraint_pressure_level']}")
    print(f"  Constraint diagnostics: {bool(updated_state['system_flags'].get('constraint_diagnostics'))}")
    
    # Validate execution trace format (CORRECTION 9)
    trace = updated_state.get('execution_trace', [])
    if trace and isinstance(trace[-1], dict):
        print(f"  Execution trace format: dict (CORRECTED)")
        print(f"    - Node: {trace[-1].get('node')}")
        print(f"    - Score: {trace[-1].get('constraint_score')}")
        print(f"    - Has timestamp: {'timestamp' in trace[-1]}")

    # Check schema compliance (CORRECTION 1)
    assert "constraint_analysis" not in updated_state, "Should NOT have constraint_analysis (CORRECTION 1)"
    assert "constraint_engine_impact" not in updated_state, "Should NOT have constraint_engine_impact (CORRECTION 1)"
    assert "forecast_data" in updated_state, "Should have forecast_data"
    assert "initial_constraint_map" in updated_state["forecast_data"], "Should have initial_constraint_map in forecast_data (CORRECTION 8)"
    assert "constraint_pressure_level" in updated_state["system_flags"], "Should have pressure level in flags (CORRECTION 1)"
    assert isinstance(trace[-1], dict), "Trace entries should be dicts (CORRECTION 9)"
    assert "node" in trace[-1] and "timestamp" in trace[-1], "Trace entries must have node and timestamp (CORRECTION 9)"

    print("\n✓ LangGraph node test passed (all corrections validated)")


def test_edge_cases():
    """Test edge cases."""
    print_section("TEST 9: Edge Cases")

    # Empty constraints
    print("Testing empty constraints...")
    normalized, validation = normalize_constraints([])
    assert len(normalized) == 0, "Should handle empty list"
    print("  ✓ Empty constraint list handled")

    # All flexible constraints
    print("Testing all flexible constraints...")
    flexible_raw = [
        {"name": "Flexible 1", "category": "time", "severity": 3, "flexible": True},
        {"name": "Flexible 2", "category": "energy", "severity": 2, "flexible": True},
    ]
    normalized, _ = normalize_constraints(flexible_raw)
    rating, score = classify_adaptability(normalized, [])
    assert rating == "high", "All flexible should be high adaptability"
    print("  ✓ All flexible constraints handled")

    # Extreme severity values
    print("Testing extreme severity values...")
    extreme_raw = [
        {"name": "Severity 0", "category": "time", "severity": 0},
        {"name": "Severity 20", "category": "time", "severity": 20},
    ]
    normalized, validation = normalize_constraints(extreme_raw)
    for c in normalized:
        assert 1 <= c.severity <= 10, "Severity should be clamped to 1-10"
    print("  ✓ Extreme values clamped correctly")

    print("\n✓ Edge cases test passed")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  CONSTRAINT ENGINE MODULE - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    try:
        test_normalization()
        test_scoring()
        test_clustering()
        test_conflict_detection()
        test_pressure_classification()
        test_adaptability()
        test_full_analysis()
        test_langgraph_node()
        test_edge_cases()

        print_section("ALL TESTS PASSED ✓")
        print("Constraint Engine module is fully functional and ready for integration.")
        return 0

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
