"""
Environment Adapter

Main orchestrator for environment context adaptation.
Analyzes physical environment constraints and generates adaptation strategies.

Module: Environment Adapter
Part of: Constraint-First Wellness Agent (Module A)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from copy import deepcopy

from environment_models import (
    EnvironmentContextExtended,
    EnvironmentAdaptationSummary,
)
from environment_utils import (
    normalize_environment_context,
    detect_environment_type,
    detect_activity_restrictions,
    get_restriction_details,
    generate_activity_modifiers,
    describe_activity_modification,
    calculate_environment_complexity,
    build_complexity_factors,
    interpret_complexity_score,
    get_active_constraints,
    generate_adaptation_recommendations,
    validate_environment_consistency,
    get_available_activity_types,
    calculate_environment_stability_score,
)

logger = logging.getLogger(__name__)


class EnvironmentAdapterManager:
    """
    Manages environment adaptation for wellness planning.
    
    Responsibilities:
    1. Normalize environment context
    2. Detect activity restrictions
    3. Generate activity modifiers
    4. Calculate environment complexity
    5. Produce adaptation summary
    """

    def __init__(self):
        """Initialize environment adapter manager."""
        self.logger = logging.getLogger(__name__)

    def adapt_environment_context(
        self,
        environment_context: Dict[str, Any],
        constraints: Optional[List[Dict[str, Any]]] = None,
        energy_budget: Optional[Dict[str, Any]] = None,
    ) -> EnvironmentContextExtended:
        """
        Adapt environment context based on constraints and adapt strategies.
        
        Args:
            environment_context: Raw environment context from state
            constraints: Optional list of user constraints
            energy_budget: Optional energy budget for context
            
        Returns:
            Extended environment context with derived fields
        """
        logger.info("Starting environment adaptation")
        
        # Step 1: Normalize environment context
        normalized = normalize_environment_context(environment_context)
        logger.debug("Step 1 - Environment normalized")
        
        # Step 2: Detect environment type
        env_type = detect_environment_type(normalized)
        logger.debug(f"Step 2 - Environment type detected: {env_type}")
        
        # Step 3: Check consistency
        consistency_issues = validate_environment_consistency(normalized)
        if consistency_issues:
            logger.warning(f"Environment consistency issues: {consistency_issues}")
        
        # Step 4: Detect activity restrictions
        activity_restrictions = detect_activity_restrictions(normalized)
        logger.debug(f"Step 4 - Activity restrictions detected: {len(activity_restrictions)}")
        
        # Step 5: Generate activity modifiers
        activity_modifiers = generate_activity_modifiers(normalized)
        logger.debug(f"Step 5 - Activity modifiers generated: {len(activity_modifiers)}")
        
        # Step 6: Calculate environment complexity
        complexity = calculate_environment_complexity(normalized)
        logger.debug(f"Step 6 - Environment complexity: {complexity}")
        
        # Step 7: Get available activity types capability map (NEW)
        available_activities = get_available_activity_types(normalized, activity_restrictions)
        logger.debug(f"Step 7 - Available activities: {available_activities}")
        
        # Step 8: Calculate environment stability score (NEW)
        stability_score = calculate_environment_stability_score(normalized)
        logger.debug(f"Step 8 - Environment stability score: {stability_score:.2f}")
        
        # Step 9: Generate adaptation summary
        summary = self._generate_adaptation_summary(
            normalized,
            env_type,
            activity_restrictions,
            activity_modifiers,
            complexity,
        )
        
        # Build extended context with all derived fields
        extended = EnvironmentContextExtended(
            **normalized,
            activity_restrictions=activity_restrictions,
            activity_modifiers=activity_modifiers,
            environment_complexity=complexity,
            available_activity_types=available_activities,
            environment_stability_score=stability_score,
            adaptation_summary=summary,
            last_adapted_at=datetime.utcnow(),
        )
        
        logger.info(
            f"Environment adaptation complete: "
            f"complexity={complexity}, restrictions={len(activity_restrictions)}, "
            f"available_activities={len(available_activities)}, stability={stability_score:.2f}"
        )
        
        return extended

    def _generate_adaptation_summary(
        self,
        environment_context: Dict[str, Any],
        env_type: str,
        activity_restrictions: List[str],
        activity_modifiers: Dict[str, str],
        complexity: int,
    ) -> EnvironmentAdaptationSummary:
        """
        Generate comprehensive adaptation summary.
        
        Args:
            environment_context: Normalized environment context
            env_type: Detected environment type
            activity_restrictions: List of restricted activities
            activity_modifiers: Dict of activity modifications
            complexity: Complexity score
            
        Returns:
            Adaptation summary
        """
        active_constraints = get_active_constraints(environment_context)
        recommendations = generate_adaptation_recommendations(
            activity_restrictions,
            activity_modifiers,
            complexity,
        )
        
        adaptation_required = len(activity_restrictions) > 0 or len(activity_modifiers) > 0
        
        summary = EnvironmentAdaptationSummary(
            original_restrictions=active_constraints,
            active_restrictions=active_constraints,
            activity_restrictions=activity_restrictions,
            activity_modifiers=activity_modifiers,
            environment_complexity=complexity,
            adaptation_required=adaptation_required,
            environment_type=env_type,
            equipment_available=environment_context.get("equipment_available", []),
            recommendations=recommendations,
        )
        
        logger.debug(f"Adaptation summary generated with {len(recommendations)} recommendations")
        
        return summary

    def get_compatible_activities(
        self,
        environment_context: Dict[str, Any],
        activity_pool: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Get list of compatible activities for this environment.
        
        Args:
            environment_context: Environment context
            activity_pool: Optional list of activities to filter (default: common activities)
            
        Returns:
            List of compatible activity names
        """
        if not activity_pool:
            activity_pool = [
                "bodyweight_exercise",
                "meditation",
                "focus_work",
                "stretching",
                "yoga",
                "walking",
                "breathing",
                "creative_work",
                "reading",
                "writing",
            ]
        
        restricted = set(detect_activity_restrictions(environment_context))
        compatible = [a for a in activity_pool if a not in restricted]
        
        logger.debug(f"Compatible activities: {len(compatible)}/{len(activity_pool)}")
        
        return compatible

    def suggest_activity_adaptation(
        self,
        activity: str,
        environment_context: Dict[str, Any],
    ) -> Optional[str]:
        """
        Suggest how to adapt a specific activity.
        
        Args:
            activity: Activity name
            environment_context: Environment context
            
        Returns:
            Adapted activity description or None
        """
        modifiers = generate_activity_modifiers(environment_context)
        
        # Check direct mapping
        if activity in modifiers:
            return modifiers[activity]
        
        # Check if activity is restricted
        restrictions = detect_activity_restrictions(environment_context)
        if activity in restrictions:
            detail = get_restriction_details(activity, environment_context)
            if detail and detail.alternative:
                return detail.alternative
        
        return None

    def is_activity_possible(
        self,
        activity: str,
        environment_context: Dict[str, Any],
    ) -> bool:
        """
        Check if an activity is possible in this environment.
        
        Args:
            activity: Activity name
            environment_context: Environment context
            
        Returns:
            True if activity is possible
        """
        restrictions = detect_activity_restrictions(environment_context)
        return activity not in restrictions

    def get_restriction_reason(
        self,
        activity: str,
        environment_context: Dict[str, Any],
    ) -> Optional[str]:
        """
        Get human-readable reason why activity is restricted.
        
        Args:
            activity: Activity name
            environment_context: Environment context
            
        Returns:
            Reason string or None
        """
        detail = get_restriction_details(activity, environment_context)
        if detail:
            return f"{detail.reason}. Consider: {detail.alternative}" if detail.alternative else detail.reason
        
        return None

    def calculate_adaptation_impact(
        self,
        environment_context: Dict[str, Any],
        energy_budget: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate impact of environment on planning.
        
        Args:
            environment_context: Environment context
            energy_budget: Optional energy budget
            
        Returns:
            Impact summary dict
        """
        complexity = calculate_environment_complexity(environment_context)
        restrictions_count = len(detect_activity_restrictions(environment_context))
        modifiers_count = len(generate_activity_modifiers(environment_context))
        
        # Adjust planning approach
        planning_approach = "flexible"
        if complexity >= 7:
            planning_approach = "simple"
        elif complexity >= 5:
            planning_approach = "moderate"
        
        impact = {
            "complexity": complexity,
            "restricted_activities": restrictions_count,
            "modifiable_activities": modifiers_count,
            "planning_approach": planning_approach,
            "requires_special_attention": complexity >= 6 or restrictions_count >= 5,
        }
        
        # Mix with energy volatility if provided
        if energy_budget:
            volatility = energy_budget.get("energy_volatility", 0.0)
            impact["combined_adaptation_difficulty"] = (complexity / 10.0 + volatility) / 2.0
        
        return impact
