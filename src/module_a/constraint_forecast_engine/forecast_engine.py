"""
Forecast Engine - Orchestration of constraint forecasting pipeline.

Coordinates all forecasting steps: data validation, prediction generation,
confidence calculation, and result compilation.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from forecast_models import (
    ForecastResult,
    ForecastMetadata,
    PredictionFactors,
)
from forecast_utils import (
    predict_energy_dips,
    predict_schedule_disruptions,
    detect_opportunity_windows,
    calculate_forecast_confidence,
    compute_forecast_expiry,
    validate_forecast_input,
    calculate_data_quality_rating,
)

logger = logging.getLogger(__name__)


class ConstraintForecastEngine:
    """
    Main forecasting orchestration engine.
    
    Coordinates:
    - Input validation and preparation
    - Energy dip prediction
    - Schedule disruption detection
    - Opportunity window identification
    - Confidence calculation
    - Result compilation and reporting
    """
    
    DEFAULT_FORECAST_WINDOW_DAYS = 7
    
    def __init__(self, forecast_window_days: int = DEFAULT_FORECAST_WINDOW_DAYS):
        """
        Initialize forecasting engine.
        
        Args:
            forecast_window_days: Forecasting horizon (default 7)
        """
        self.forecast_window_days = forecast_window_days
        self.logger = logger
    
    def forecast(self, factors: PredictionFactors) -> ForecastResult:
        """
        Generate complete constraint forecast.
        
        Pipeline:
        1. Validate input factors
        2. Predict energy dips
        3. Predict schedule disruptions
        4. Detect opportunity windows
        5. Calculate forecast confidence
        6. Compute expiry
        7. Generate summary
        8. Build result
        
        Args:
            factors: Prediction input factors
            
        Returns:
            Complete forecast result
        """
        self.logger.info(
            f"Starting forecast generation for user "
            f"(window={self.forecast_window_days}d, score={factors.current_constraint_score:.1f})"
        )
        
        # Step 1: Validate input
        validation = validate_forecast_input(factors)
        if not validation.is_valid:
            self.logger.error(f"Forecast validation failed: {validation.errors}")
            return self._create_empty_forecast(validation.data_quality_score)
        
        if validation.warnings:
            for warning in validation.warnings:
                self.logger.warning(f"Forecast warning: {warning}")
        
        # Step 2: Predict energy dips
        self.logger.debug("Predicting energy dips...")
        energy_dips = predict_energy_dips(factors)
        self.logger.info(f"Detected {len(energy_dips)} energy dips")
        
        # Step 3: Predict schedule disruptions
        self.logger.debug("Predicting schedule disruptions...")
        disruptions = predict_schedule_disruptions(factors)
        self.logger.info(f"Detected {len(disruptions)} schedule disruptions")
        
        # Step 4: Detect opportunity windows
        self.logger.debug("Detecting opportunity windows...")
        opportunities = detect_opportunity_windows(factors, self.forecast_window_days)
        self.logger.info(f"Identified {len(opportunities)} opportunity windows")
        
        # Step 5: Calculate forecast confidence
        self.logger.debug("Calculating forecast confidence...")
        confidence = calculate_forecast_confidence(factors)
        self.logger.info(f"Forecast confidence: {confidence:.2f}")
        
        # Step 6: Compute expiry times
        generated_at, expires_at = compute_forecast_expiry(self.forecast_window_days)
        
        # Step 7: Generate summary
        summary = self._generate_forecast_summary(
            factors, energy_dips, disruptions, opportunities, confidence
        )
        
        # Step 8: Build result
        metadata = ForecastMetadata(
            generated_at=generated_at,
            expires_at=expires_at,
            forecast_window_days=self.forecast_window_days,
            forecast_confidence=confidence,
            data_quality=calculate_data_quality_rating(
                factors.user_history_sample_size,
                validation.data_quality_score
            ),
            samples_analyzed=factors.user_history_sample_size,
        )
        
        result = ForecastResult(
            predicted_energy_dips=energy_dips,
            predicted_schedule_disruptions=disruptions,
            opportunity_windows=opportunities,
            metadata=metadata,
            summary=summary,
        )
        
        self.logger.info(f"Forecast complete: {len(energy_dips)} dips, "
                        f"{len(disruptions)} disruptions, "
                        f"{len(opportunities)} opportunities")
        
        return result
    
    def _create_empty_forecast(self, data_quality: float) -> ForecastResult:
        """Create empty forecast when validation fails."""
        generated_at, expires_at = compute_forecast_expiry(1)  # Expire in 1 day
        
        return ForecastResult(
            predicted_energy_dips=[],
            predicted_schedule_disruptions=[],
            opportunity_windows=[],
            metadata=ForecastMetadata(
                generated_at=generated_at,
                expires_at=expires_at,
                forecast_window_days=self.forecast_window_days,
                forecast_confidence=0.1,
                data_quality="LOW",
                samples_analyzed=0,
            ),
            summary="Forecast unavailable due to insufficient input data.",
        )
    
    def _generate_forecast_summary(
        self,
        factors: PredictionFactors,
        energy_dips,
        disruptions,
        opportunities,
        confidence: float,
    ) -> str:
        """
        Generate human-readable forecast summary.
        
        Args:
            factors: Input factors
            energy_dips: Predicted energy dips
            disruptions: Predicted disruptions
            opportunities: Detected opportunities
            confidence: Overall confidence
            
        Returns:
            Markdown-formatted summary
        """
        lines = [
            f"# Constraint Forecast (Next {self.forecast_window_days} Days)",
            "",
            f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Confidence**: {confidence:.0%}",
            f"**Current Constraint Score**: {factors.current_constraint_score:.1f}/10 ({factors.pressure_level})",
            "",
        ]
        
        # Energy dips section
        lines.append("## Energy Dips")
        if energy_dips:
            lines.append(f"⚠️ **{len(energy_dips)} energy dips predicted**")
            lines.append("")
            for dip in energy_dips[:3]:  # Show top 3
                lines.append(f"- **Day {dip.day_offset}** ({dip.severity.value}): {dip.primary_cause}")
                if dip.recommended_action:
                    lines.append(f"  - *{dip.recommended_action}*")
        else:
            lines.append("✅ No significant energy dips predicted")
        lines.append("")
        
        # Schedule disruptions section
        lines.append("## Schedule Disruptions")
        if disruptions:
            lines.append(f"⚠️ **{len(disruptions)} disruptions forecasted**")
            lines.append("")
            disruption_types = set(d.disruption_type.value for d in disruptions)
            for dtype in disruption_types:
                count = sum(1 for d in disruptions if d.disruption_type.value == dtype)
                lines.append(f"- {dtype.replace('_', ' ').title()}: {count} incident(s)")
        else:
            lines.append("✅ Schedule appears stable")
        lines.append("")
        
        # Opportunity windows section
        lines.append("## Opportunity Windows")
        if opportunities:
            lines.append(f"🌟 **{len(opportunities)} opportunity windows identified**")
            lines.append("")
            for opp in opportunities[:3]:  # Show top 3
                lines.append(f"- **Days {opp.start_day}-{opp.start_day + opp.duration - 1}** "
                            f"({opp.confidence:.0%} confidence): {opp.duration} day opportunity window")
        else:
            lines.append("📌 Limited opportunities in this window")
        lines.append("")
        
        # Recommendations
        lines.append("## Recommendations")
        if factors.current_constraint_score >= 8:
            lines.append("- 🔴 **Critical constraint load**: Prioritize recovery and stabilization")
        elif factors.current_constraint_score >= 6:
            lines.append("- 🟡 **High constraint load**: Reduce optional commitments")
        else:
            lines.append("- 🟢 **Manageable constraint load**: Maintain current approach")
        
        if factors.life_mode == "crisis":
            lines.append("- 🚨 **Life mode CRISIS**: Activate emergency protocols")
        
        if opportunities and confidence >= 0.7:
            lines.append("- 💡 Use identified opportunity windows for planning or recovery")
        
        if confidence < 0.5:
            lines.append("- ⚠️ Low forecast confidence: Review with more historical data")
        
        return "\n".join(lines)
    
    def estimate_system_impact(self, forecast: ForecastResult, factors: PredictionFactors) -> Dict[str, Any]:
        """
        Estimate downstream system impact of forecast.
        
        Args:
            forecast: Generated forecast
            factors: Input factors
            
        Returns:
            Dictionary of impact estimates
        """
        critical_dips = sum(1 for d in forecast.predicted_energy_dips 
                           if d.severity.value == "critical")
        high_disruptions = sum(1 for d in forecast.predicted_schedule_disruptions
                              if d.severity.value == "high" or d.severity.value == "critical")
        
        return {
            "energy_preservation_needed": critical_dips > 0,
            "schedule_flexibility_required": high_disruptions > 2,
            "recovery_priority": critical_dips > 1 or (factors.current_constraint_score >= 8),
            "opportunity_utilization": len(forecast.opportunity_windows) > 1,
            "planning_complexity": "high" if high_disruptions > 3 else "medium" if high_disruptions > 0 else "low",
            "recommended_intervention": self._recommend_intervention(forecast, factors),
        }
    
    def _recommend_intervention(self, forecast: ForecastResult, factors: PredictionFactors) -> str:
        """Recommend intervention strategy."""
        if factors.current_constraint_score >= 9:
            return "EMERGENCY_RECOVERY"
        elif len(forecast.predicted_energy_dips) >= 3:
            return "INTENSIVE_RECOVERY"
        elif len(forecast.predicted_schedule_disruptions) >= 3:
            return "SCHEDULE_FLEXIBILITY"
        elif len(forecast.opportunity_windows) > 1 and factors.adaptation_capacity > 0.7:
            return "GROWTH_OPPORTUNITY"
        else:
            return "MAINTENANCE"
