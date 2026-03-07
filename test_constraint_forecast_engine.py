"""
Comprehensive Test Suite for Constraint Forecast Engine

Tests all core forecasting functionality:
1. Energy dip prediction
2. Schedule disruption detection
3. Opportunity window identification
4. Forecast confidence calculation
5. Data validation
6. Complete forecast generation
7. LangGraph node integration
8. Edge cases and error handling
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'module_a', 'constraint_forecast_engine'))

# Import module components
from forecast_models import (
    PredictionFactors,
    SeverityLevel,
    DisruptionType,
)
from forecast_utils import (
    predict_energy_dips,
    predict_schedule_disruptions,
    detect_opportunity_windows,
    calculate_forecast_confidence,
    validate_forecast_input,
)
from forecast_engine import ConstraintForecastEngine
from forecast_node import constraint_forecast_node


class TestEnergyDipPrediction(unittest.TestCase):
    """Test energy dip prediction accuracy."""
    
    def setUp(self):
        """Set up test factors."""
        self.factors = PredictionFactors(
            current_constraint_score=5.0,
            pressure_level="MODERATE",
            life_mode="maintenance",
            constraint_clusters={"time": 0, "energy": 0, "physical": 0, "mental": 0},
            constraint_conflicts=[],
            recent_constraint_frequency=2,
            overload_history=0,
            recovery_periods=1,
            environment_stability="stable",
            schedule_regularity="regular",
            adaptation_capacity=0.6,
            user_history_sample_size=20,
        )
    
    def test_high_score_predicts_dips(self):
        """High constraint score should predict energy dips."""
        self.factors.current_constraint_score = 8.0
        dips = predict_energy_dips(self.factors)
        self.assertGreater(len(dips), 0, "Should predict dips for high constraint score")
    
    def test_crisis_mode_immediate_dip(self):
        """Crisis mode should predict immediate energy dip."""
        self.factors.life_mode = "crisis"
        dips = predict_energy_dips(self.factors)
        immediate_dips = [d for d in dips if d.day_offset == 0]
        self.assertGreater(len(immediate_dips), 0, "Crisis mode should predict day-0 dips")
        if immediate_dips:
            self.assertEqual(immediate_dips[0].severity, SeverityLevel.CRITICAL)
    
    def test_recent_overload_predicts_future_dips(self):
        """Recent overload should predict dips 1-2 days later."""
        self.factors.overload_history = 2
        dips = predict_energy_dips(self.factors)
        future_dips = [d for d in dips if d.day_offset >= 1]
        self.assertGreater(len(future_dips), 0, "Recent overload should predict future dips")
    
    def test_low_recovery_amplifies_fatigue(self):
        """Low recovery periods should increase predicted dips."""
        self.factors.recovery_periods = 0
        dips_no_recovery = predict_energy_dips(self.factors)
        
        self.factors.recovery_periods = 5
        dips_with_recovery = predict_energy_dips(self.factors)
        
        self.assertGreaterEqual(len(dips_no_recovery), len(dips_with_recovery),
                               "Low recovery should predict more dips")
    
    def test_physical_mental_cluster_creates_dips(self):
        """Physical + mental clusters should predict compound dips."""
        self.factors.constraint_clusters = {"physical": 1, "mental": 1}
        dips = predict_energy_dips(self.factors)
        self.assertGreater(len(dips), 0, "Should predict dips for physical+mental combo")


class TestScheduleDisruptionPrediction(unittest.TestCase):
    """Test schedule disruption detection."""
    
    def setUp(self):
        """Set up test factors."""
        self.factors = PredictionFactors(
            current_constraint_score=6.0,
            pressure_level="HIGH",
            life_mode="maintenance",
            constraint_clusters={"time": 0, "logistical": 0, "social": 0},
            constraint_conflicts=[],
            recent_constraint_frequency=3,
            overload_history=1,
            recovery_periods=1,
            environment_stability="stable",
            schedule_regularity="regular",
            adaptation_capacity=0.6,
            user_history_sample_size=20,
        )
    
    def test_time_pressure_predicts_deadlines(self):
        """High time constraints should predict deadline disruptions."""
        self.factors.constraint_clusters["time"] = 3
        disruptions = predict_schedule_disruptions(self.factors)
        deadline_disruptions = [d for d in disruptions 
                               if d.disruption_type == DisruptionType.DEADLINE_PRESSURE]
        self.assertGreater(len(deadline_disruptions), 0, "Should predict deadline disruptions")
    
    def test_logistical_constraints_predict_travel(self):
        """Logistical constraints should predict travel disruptions."""
        self.factors.constraint_clusters["logistical"] = 2
        disruptions = predict_schedule_disruptions(self.factors)
        travel_disruptions = [d for d in disruptions 
                             if d.disruption_type == DisruptionType.TRAVEL_DISRUPTION]
        self.assertGreater(len(travel_disruptions), 0, "Should predict travel disruptions")
    
    def test_unstable_environment_increases_disruptions(self):
        """Unstable environment should increase disruption predictions."""
        self.factors.environment_stability = "stable"
        disruptions_stable = predict_schedule_disruptions(self.factors)
        
        self.factors.environment_stability = "unstable"
        disruptions_unstable = predict_schedule_disruptions(self.factors)
        
        self.assertGreaterEqual(len(disruptions_unstable), len(disruptions_stable),
                               "Unstable environment should predict more disruptions")
    
    def test_irregular_schedule_predicts_compounding(self):
        """Irregular schedule should predict compounding disruptions."""
        self.factors.schedule_regularity = "irregular"
        disruptions = predict_schedule_disruptions(self.factors)
        compounding = [d for d in disruptions 
                      if d.disruption_type == DisruptionType.COMPOUNDING_LOAD]
        self.assertGreater(len(compounding), 0, "Should predict compounding for irregular schedule")


class TestOpportunityWindowDetection(unittest.TestCase):
    """Test opportunity window identification."""
    
    def setUp(self):
        """Set up test factors."""
        self.factors = PredictionFactors(
            current_constraint_score=3.0,
            pressure_level="LOW",
            life_mode="maintenance",
            constraint_clusters={"time": 0, "social": 0, "logistical": 0},
            constraint_conflicts=[],
            recent_constraint_frequency=1,
            overload_history=0,
            recovery_periods=2,
            environment_stability="stable",
            schedule_regularity="regular",
            adaptation_capacity=0.7,
            user_history_sample_size=25,
        )
    
    def test_low_score_creates_opportunities(self):
        """Low constraint score should create opportunity windows."""
        windows = detect_opportunity_windows(self.factors)
        self.assertGreater(len(windows), 0, "Should identify opportunity windows")
    
    def test_high_adaptability_extends_opportunities(self):
        """High adaptability should create more/longer opportunity windows."""
        self.factors.adaptation_capacity = 0.8
        windows_high = detect_opportunity_windows(self.factors)
        
        self.factors.adaptation_capacity = 0.3
        windows_low = detect_opportunity_windows(self.factors)
        
        total_high = sum(w.duration for w in windows_high)
        total_low = sum(w.duration for w in windows_low)
        self.assertGreaterEqual(total_high, total_low,
                               "High adaptability should create more opportunity days")
    
    def test_growth_mode_creates_opportunities(self):
        """Growth life mode should create more opportunities."""
        self.factors.life_mode = "growth"
        windows = detect_opportunity_windows(self.factors)
        self.assertGreater(len(windows), 0, "Growth mode should identify opportunities")
    
    def test_opportunity_respects_forecast_window(self):
        """Opportunities should not exceed forecast window."""
        windows = detect_opportunity_windows(self.factors, forecast_window_days=7)
        for window in windows:
            self.assertLessEqual(window.start_day + window.duration, 7,
                               "Window should fit within forecast horizon")


class TestForecastConfidence(unittest.TestCase):
    """Test forecast confidence calculation."""
    
    def setUp(self):
        """Set up test factors."""
        self.factors = PredictionFactors(
            current_constraint_score=5.0,
            pressure_level="MODERATE",
            life_mode="maintenance",
            constraint_clusters={},
            constraint_conflicts=[],
            recent_constraint_frequency=2,
            overload_history=0,
            recovery_periods=1,
            environment_stability="stable",
            schedule_regularity="regular",
            adaptation_capacity=0.6,
            user_history_sample_size=20,
        )
    
    def test_high_sample_size_increases_confidence(self):
        """More historical data should increase confidence."""
        self.factors.user_history_sample_size = 5
        confidence_low = calculate_forecast_confidence(self.factors)
        
        self.factors.user_history_sample_size = 40
        confidence_high = calculate_forecast_confidence(self.factors)
        
        self.assertGreater(confidence_high, confidence_low,
                          "More history should increase confidence")
    
    def test_crisis_mode_reduces_confidence(self):
        """Crisis mode should reduce predictability."""
        self.factors.life_mode = "maintenance"
        confidence_normal = calculate_forecast_confidence(self.factors)
        
        self.factors.life_mode = "crisis"
        confidence_crisis = calculate_forecast_confidence(self.factors)
        
        self.assertLess(confidence_crisis, confidence_normal,
                       "Crisis mode should reduce confidence")
    
    def test_confidence_range(self):
        """Confidence should always be 0-1."""
        confidences = []
        for life_mode in ["maintenance", "growth", "recovery", "crisis"]:
            self.factors.life_mode = life_mode
            confidence = calculate_forecast_confidence(self.factors)
            confidences.append(confidence)
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)


class TestDataValidation(unittest.TestCase):
    """Test input data validation."""
    
    def test_valid_factors_pass_validation(self):
        """Valid factors should pass validation."""
        factors = PredictionFactors(
            current_constraint_score=5.0,
            pressure_level="MODERATE",
            life_mode="maintenance",
            constraint_clusters={},
            constraint_conflicts=[],
            recent_constraint_frequency=2,
            overload_history=0,
            recovery_periods=1,
            environment_stability="stable",
            schedule_regularity="regular",
            adaptation_capacity=0.6,
            user_history_sample_size=20,
        )
        result = validate_forecast_input(factors)
        self.assertTrue(result.is_valid, "Valid factors should pass validation")
    
    def test_invalid_score_fails_validation(self):
        """Out-of-range score should fail validation."""
        factors = PredictionFactors(
            current_constraint_score=15.0,  # Invalid
            pressure_level="MODERATE",
            life_mode="maintenance",
            constraint_clusters={},
            constraint_conflicts=[],
            recent_constraint_frequency=2,
            overload_history=0,
            recovery_periods=1,
            environment_stability="stable",
            schedule_regularity="regular",
            adaptation_capacity=0.6,
            user_history_sample_size=20,
        )
        result = validate_forecast_input(factors)
        self.assertFalse(result.is_valid, "Invalid score should fail validation")
    
    def test_no_history_generates_warning(self):
        """No history should generate warning and reduce quality."""
        factors = PredictionFactors(
            current_constraint_score=5.0,
            pressure_level="MODERATE",
            life_mode="maintenance",
            constraint_clusters={},
            constraint_conflicts=[],
            recent_constraint_frequency=0,
            overload_history=0,
            recovery_periods=0,
            environment_stability="stable",
            schedule_regularity="regular",
            adaptation_capacity=0.6,
            user_history_sample_size=0,  # No history
        )
        result = validate_forecast_input(factors)
        self.assertGreater(len(result.warnings), 0, "No history should generate warnings")
        self.assertLess(result.data_quality_score, 0.7, "No history should reduce quality")


class TestCompleteForecast(unittest.TestCase):
    """Test complete forecast generation."""
    
    def test_realistic_scenario(self):
        """Test realistic forecasting scenario."""
        # Scenario: Exam prep + low energy + shared space + tight schedule
        factors = PredictionFactors(
            current_constraint_score=7.5,
            pressure_level="HIGH",
            life_mode="maintenance",
            constraint_clusters={
                "time": 3,
                "energy": 2,
                "environment": 1,
                "mental": 2,
            },
            constraint_conflicts=[
                "Deadline pressure conflicts with low energy",
                "Shared space limits focus",
            ],
            recent_constraint_frequency=4,
            overload_history=1,
            recovery_periods=0,
            environment_stability="variable",
            schedule_regularity="irregular",
            adaptation_capacity=0.5,
            user_history_sample_size=18,
        )
        
        engine = ConstraintForecastEngine()
        forecast = engine.forecast(factors)
        
        # Validate results
        self.assertIsNotNone(forecast)
        self.assertEqual(forecast.metadata.forecast_window_days, 7)
        self.assertGreater(forecast.metadata.forecast_confidence, 0.3)
        self.assertGreater(len(forecast.predicted_energy_dips), 0)
        self.assertGreater(len(forecast.predicted_schedule_disruptions), 0)
    
    def test_low_constraint_scenario(self):
        """Test forecast for low-constraint user."""
        factors = PredictionFactors(
            current_constraint_score=2.0,
            pressure_level="LOW",
            life_mode="growth",
            constraint_clusters={"time": 0, "energy": 0},
            constraint_conflicts=[],
            recent_constraint_frequency=0,
            overload_history=0,
            recovery_periods=2,
            environment_stability="stable",
            schedule_regularity="regular",
            adaptation_capacity=0.85,
            user_history_sample_size=30,
        )
        
        engine = ConstraintForecastEngine()
        forecast = engine.forecast(factors)
        
        self.assertIsNotNone(forecast)
        self.assertGreater(len(forecast.opportunity_windows), 0, "Low constraints should yield opportunities")
        self.assertLess(len(forecast.predicted_energy_dips), 2, "Low constraints should have few dips")


class TestLangGraphNodeIntegration(unittest.TestCase):
    """Test LangGraph node integration."""
    
    def test_node_processes_minimal_state(self):
        """Node should handle minimal state gracefully."""
        state = {
            "user_id": "test_user",
            "forecast_data": {
                "initial_constraint_map": {
                    "constraint_score": 5.0,
                    "pressure_level": "MODERATE",
                    "clusters": {"time": 1, "energy": 0},
                    "conflicts": [],
                    "categories": {},
                }
            },
            "user_history": {"constraint_history": []},
            "system_flags": {},
            "environment_context": {"stability": "stable", "schedule_regularity": "regular"},
            "life_mode": "maintenance",
            "execution_trace": [],
        }
        
        result = constraint_forecast_node(state)
        
        self.assertIsNotNone(result)
        self.assertIn("last_node_executed", result)
        self.assertEqual(result["last_node_executed"], "constraint_forecast_engine")
        self.assertIn("execution_trace", result)
        self.assertGreater(len(result["execution_trace"]), 0)
    
    def test_node_updates_forecast_data(self):
        """Node should populate forecast_data fields."""
        state = {
            "user_id": "test_user",
            "forecast_data": {
                "initial_constraint_map": {
                    "constraint_score": 7.0,
                    "pressure_level": "HIGH",
                    "clusters": {"time": 2, "energy": 1},
                    "conflicts": ["Deadline + fatigue"],
                    "categories": {},
                }
            },
            "user_history": {"constraint_history": []},
            "system_flags": {},
            "environment_context": {"stability": "stable", "schedule_regularity": "regular"},
            "life_mode": "maintenance",
            "execution_trace": [],
        }
        
        result = constraint_forecast_node(state)
        
        self.assertIn("predicted_energy_dips", result["forecast_data"])
        self.assertIn("predicted_schedule_disruptions", result["forecast_data"])
        self.assertIn("opportunity_windows", result["forecast_data"])
        self.assertIn("forecast_confidence", result["forecast_data"])
    
    def test_node_schema_compliance(self):
        """Node should not add unauthorized top-level fields."""
        state = {
            "user_id": "test_user",
            "forecast_data": {
                "initial_constraint_map": {
                    "constraint_score": 5.0,
                    "pressure_level": "MODERATE",
                    "clusters": {},
                    "conflicts": [],
                    "categories": {},
                }
            },
            "user_history": {"constraint_history": []},
            "system_flags": {},
            "environment_context": {"stability": "stable", "schedule_regularity": "regular"},
            "life_mode": "maintenance",
            "execution_trace": [],
        }
        
        result = constraint_forecast_node(state)
        
        # Initial constraint map should not be modified
        self.assertIn("initial_constraint_map", result["forecast_data"])
        self.assertEqual(
            result["forecast_data"]["initial_constraint_map"]["constraint_score"],
            5.0,
            "Should preserve initial_constraint_map"
        )
        
        # Check that no unauthorized fields were added
        forbidden_fields = ["forecast_analysis", "forecast_engine_impact", "predictions_only"]
        for field in forbidden_fields:
            self.assertNotIn(field, result, f"Forbidden field '{field}' should not exist")
    
    def test_node_trace_entry_format(self):
        """Execution trace entry should be properly formatted dict."""
        state = {
            "user_id": "test_user",
            "forecast_data": {
                "initial_constraint_map": {
                    "constraint_score": 5.0,
                    "pressure_level": "MODERATE",
                    "clusters": {},
                    "conflicts": [],
                    "categories": {},
                }
            },
            "user_history": {"constraint_history": []},
            "system_flags": {},
            "environment_context": {"stability": "stable", "schedule_regularity": "regular"},
            "life_mode": "maintenance",
            "execution_trace": [],
        }
        
        result = constraint_forecast_node(state)
        
        trace = result["execution_trace"][-1]  # Last entry
        self.assertIsInstance(trace, dict, "Trace entry should be dict")
        self.assertEqual(trace["node"], "constraint_forecast_engine")
        self.assertIn("timestamp", trace)
        self.assertIn("status", trace)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_empty_constraint_clusters(self):
        """Should handle empty constraint clusters."""
        factors = PredictionFactors(
            current_constraint_score=5.0,
            pressure_level="MODERATE",
            life_mode="maintenance",
            constraint_clusters={},  # Empty
            constraint_conflicts=[],
            recent_constraint_frequency=0,
            overload_history=0,
            recovery_periods=0,
            environment_stability="stable",
            schedule_regularity="regular",
            adaptation_capacity=0.5,
            user_history_sample_size=0,
        )
        
        engine = ConstraintForecastEngine()
        forecast = engine.forecast(factors)
        
        self.assertIsNotNone(forecast)
        self.assertEqual(forecast.metadata.forecast_confidence, 0.1)  # Low due to empty data
    
    def test_extreme_constraint_score(self):
        """Should handle extreme constraint scores."""
        for score in [0.0, 10.0]:
            factors = PredictionFactors(
                current_constraint_score=score,
                pressure_level="CRITICAL",
                life_mode="maintenance",
                constraint_clusters={},
                constraint_conflicts=[],
                recent_constraint_frequency=0,
                overload_history=0,
                recovery_periods=0,
                environment_stability="stable",
                schedule_regularity="regular",
                adaptation_capacity=0.5,
                user_history_sample_size=10,
            )
            
            engine = ConstraintForecastEngine()
            forecast = engine.forecast(factors)
            self.assertIsNotNone(forecast)
    
    def test_missing_initial_constraint_map(self):
        """Node should handle missing constraint map gracefully."""
        state = {
            "user_id": "test_user",
            "forecast_data": {},  # Missing initial_constraint_map
            "user_history": {},
            "system_flags": {},
            "environment_context": {},
            "life_mode": "maintenance",
            "execution_trace": [],
        }
        
        result = constraint_forecast_node(state)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["last_node_executed"], "constraint_forecast_engine")


def run_tests():
    """Run all tests and print results."""
    print("=" * 80)
    print("CONSTRAINT FORECAST ENGINE - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print("")
    
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("")
    print("=" * 80)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED")
        print(f"Ran {result.testsRun} tests successfully")
    else:
        print("❌ SOME TESTS FAILED")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    print("=" * 80)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
