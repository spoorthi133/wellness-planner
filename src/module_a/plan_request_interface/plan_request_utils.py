"""
Plan Request Interface Utilities

Utility functions for building planning requests.

Core functions:
- build_planning_context: Extract signals from state
- compress_planning_context: Convert to compressed summary
- build_planning_prompt: Construct LLM prompt
- create_fallback_plan: Generate default plan
- validate_prompt_size: Check prompt constraints

NOTE: LLM invocation moved to Module B (llm_engine)
NOTE: Response parsing moved to Plan Parser module
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from .plan_request_models import (
    PlanningContext,
    EnergyContextSnapshot,
    ConstraintContextSnapshot,
    EnvironmentContextSnapshot,
    ForecastContextSnapshot,
    LifemodeContextSnapshot,
    CompressedContextSummary,
    PlanningPrompt,
    PlanCandidate,
    DailyWellnessPlan,
    PlanTimeblock,
    LLMRequest,
    LLMResponse,
    PlanningApproach,
    ActivityTimeblock,
    PlanStatus,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

MAX_PROMPT_SIZE_BYTES = 4096  # 4KB limit for prompt
DEFAULT_LLM_TIMEOUT_SECONDS = 30
DEFAULT_LLM_MODEL = "mistral"
DEFAULT_LLM_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2000

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_API_ENDPOINT = f"{OLLAMA_BASE_URL}/api/chat"

# Planning approach thresholds
ENERGY_VOLATILITY_THRESHOLD_SIMPLE = 0.5
CONSTRAINT_PRESSURE_THRESHOLD_SIMPLE = 8
ENVIRONMENT_COMPLEXITY_THRESHOLD_SIMPLE = 7

# Activity mappings for fallback plans
FALLBACK_ACTIVITIES_BY_APPROACH = {
    PlanningApproach.SIMPLE: {
        "morning_activities": [
            {"activity": "light stretching", "duration_minutes": 10, "energy_cost": 5},
            {"activity": "mindful breathing", "duration_minutes": 5, "energy_cost": 2},
        ],
        "afternoon_activities": [
            {"activity": "short walk", "duration_minutes": 15, "energy_cost": 8},
            {"activity": "focused work block", "duration_minutes": 30, "energy_cost": 10},
        ],
        "evening_activities": [
            {"activity": "light movement", "duration_minutes": 10, "energy_cost": 5},
            {"activity": "meditation", "duration_minutes": 15, "energy_cost": 3},
        ],
        "recovery_blocks": [
            {"activity": "rest", "duration_minutes": 60, "energy_cost": 0},
        ],
    },
    PlanningApproach.STANDARD: {
        "morning_activities": [
            {"activity": "warm-up stretching", "duration_minutes": 15, "energy_cost": 8},
            {"activity": "meditation", "duration_minutes": 10, "energy_cost": 5},
            {"activity": "breakfast & hydration", "duration_minutes": 20, "energy_cost": 3},
        ],
        "afternoon_activities": [
            {"activity": "exercise or movement", "duration_minutes": 30, "energy_cost": 15},
            {"activity": "deep work block", "duration_minutes": 60, "energy_cost": 20},
            {"activity": "social interaction", "duration_minutes": 30, "energy_cost": 10},
        ],
        "evening_activities": [
            {"activity": "light movement", "duration_minutes": 15, "energy_cost": 8},
            {"activity": "dinner & family time", "duration_minutes": 45, "energy_cost": 5},
            {"activity": "meditation or reflection", "duration_minutes": 20, "energy_cost": 5},
        ],
        "recovery_blocks": [
            {"activity": "rest & hydration", "duration_minutes": 60, "energy_cost": 0},
        ],
    },
    PlanningApproach.RECOVERY: {
        "morning_activities": [
            {"activity": "gentle stretching", "duration_minutes": 10, "energy_cost": 3},
            {"activity": "mindful breathing", "duration_minutes": 10, "energy_cost": 2},
        ],
        "afternoon_activities": [
            {"activity": "light activity", "duration_minutes": 20, "energy_cost": 5},
            {"activity": "focus task", "duration_minutes": 30, "energy_cost": 8},
        ],
        "evening_activities": [
            {"activity": "rest", "duration_minutes": 30, "energy_cost": 0},
            {"activity": "sleep preparation", "duration_minutes": 30, "energy_cost": 2},
        ],
        "recovery_blocks": [
            {"activity": "rest", "duration_minutes": 120, "energy_cost": 0},
        ],
    },
}


# ============================================================================
# Context Building
# ============================================================================

def build_planning_context(state: Dict[str, Any]) -> PlanningContext:
    """
    Extract relevant planning signals from state.
    
    Requires state fields:
    - user_id
    - constraints (with pressure_level, score)
    - energy_budget (with daily_budget, remaining_energy)
    - environment_context (with complexity, restrictions, modifiers)
    - life_mode
    - forecast_data (optional)
    
    Args:
        state: Current state dictionary
        
    Returns:
        PlanningContext object with all signals
        
    Raises:
        ValueError: If required fields missing
    """
    logger.debug(f"Building planning context for user {state.get('user_id')}")
    
    try:
        user_id = state.get("user_id")
        if not user_id:
            raise ValueError("user_id required in state")
        
        # Extract energy context
        budget_data = state.get("energy_budget", {})
        energy = EnergyContextSnapshot(
            daily_budget=budget_data.get("daily_budget", 100),
            remaining_energy=budget_data.get("remaining_energy", 100),
            budget_allocation=budget_data.get("budget_allocation"),
            energy_volatility=budget_data.get("energy_volatility", 0.0),
            constraint_impact=budget_data.get("constraint_impact", 0),
        )
        
        # Extract constraint context
        constraint_data = state.get("constraints", {})
        constraints = ConstraintContextSnapshot(
            pressure_level=constraint_data.get("pressure_level", "LOW"),
            constraint_score=float(constraint_data.get("constraint_score", 0)),
            active_constraints=constraint_data.get("active_constraints", []),
            constraint_count=constraint_data.get("constraint_count", 0),
            dominant_constraint=constraint_data.get("dominant_constraint"),
        )
        
        # Extract environment context
        env_data = state.get("environment_context", {})
        environment = EnvironmentContextSnapshot(
            environment_complexity=env_data.get("environment_complexity", 0),
            activity_restrictions=env_data.get("activity_restrictions", []),
            activity_modifiers=env_data.get("activity_modifiers", {}),
            available_activity_types=env_data.get("available_activity_types", []),
            environment_stability=float(env_data.get("environment_stability", 1.0)),
        )
        
        # Extract forecast context
        forecast_data = state.get("forecast_data", {})
        forecast = ForecastContextSnapshot(
            predicted_energy_dips=forecast_data.get("predicted_energy_dips", []),
            disruption_risk=float(forecast_data.get("disruption_risk", 0.0)),
            recovery_opportunity=forecast_data.get("recovery_opportunity"),
            forecast_confidence=float(forecast_data.get("forecast_confidence", 1.0)),
        )
        
        # Extract life mode context
        lifemode_data = state.get("life_mode", {})
        lifemode = LifemodeContextSnapshot(
            life_mode=lifemode_data.get("mode", "maintenance"),
            mode_profile=lifemode_data.get("mode_profile", {}),
            mode_adjustments=lifemode_data.get("mode_adjustments"),
            planning_approach=PlanningApproach(
                lifemode_data.get("planning_approach", "standard")
            ),
        )
        
        # Build complete context
        context = PlanningContext(
            user_id=user_id,
            energy=energy,
            constraints=constraints,
            environment=environment,
            forecast=forecast,
            lifemode=lifemode,
            planning_precision=float(state.get("planning_precision", 0.5)),
            additional_context=state.get("additional_context"),
        )
        
        logger.info(f"Planning context built: {user_id} - {lifemode.life_mode} mode, {energy.daily_budget} energy")
        return context
        
    except Exception as e:
        logger.error(f"Error building planning context: {str(e)}")
        raise


def determine_planning_approach(context: PlanningContext) -> PlanningApproach:
    """
    Determine optimal planning approach based on context.
    
    Logic:
    - HIGH/CRITICAL constraint pressure → SIMPLE
    - High energy volatility (>0.5) → SIMPLE
    - High environment complexity (>7) → SIMPLE
    - Recovery life mode → RECOVERY
    - Otherwise → STANDARD
    
    Args:
        context: Planning context
        
    Returns:
        Recommended PlanningApproach
    """
    logger.debug("Determining planning approach")
    
    # Check constraints
    if context.constraints.pressure_level in ["HIGH", "CRITICAL"]:
        logger.info("Constraint pressure suggests SIMPLE approach")
        return PlanningApproach.SIMPLE
    
    # Check energy volatility
    if context.energy.energy_volatility and context.energy.energy_volatility > ENERGY_VOLATILITY_THRESHOLD_SIMPLE:
        logger.info("High energy volatility suggests SIMPLE approach")
        return PlanningApproach.SIMPLE
    
    # Check environment complexity
    if context.environment.environment_complexity > ENVIRONMENT_COMPLEXITY_THRESHOLD_SIMPLE:
        logger.info("High environment complexity suggests SIMPLE approach")
        return PlanningApproach.SIMPLE
    
    # Check life mode
    if context.lifemode.life_mode == "recovery":
        logger.info("Recovery life mode selected")
        return PlanningApproach.RECOVERY
    
    # Default to standard
    logger.info("Using STANDARD approach")
    return PlanningApproach.STANDARD


# ============================================================================
# Context Compression
# ============================================================================

def compress_planning_context(context: PlanningContext) -> CompressedContextSummary:
    """
    Convert structured context to human-readable compressed summary.
    
    Reduces verbose context to concise text for LLM prompt.
    
    Args:
        context: Full planning context
        
    Returns:
        CompressedContextSummary with text summaries
    """
    logger.debug(f"Compressing planning context for {context.user_id}")
    
    try:
        # Energy summary
        energy_summary = (
            f"Daily energy: {context.energy.daily_budget} units. "
            f"Current available: {context.energy.remaining_energy} units. "
        )
        if context.energy.energy_volatility:
            stability = "stable" if context.energy.energy_volatility < 0.3 else \
                       "moderate" if context.energy.energy_volatility < 0.6 else \
                       "volatile"
            energy_summary += f"Stability: {stability}. "
        if context.energy.constraint_impact:
            energy_summary += f"Constraint impact: -{context.energy.constraint_impact} units. "
        
        # Constraint summary
        constraint_summary = (
            f"Constraint pressure: {context.constraints.pressure_level}. "
            f"Score: {context.constraints.constraint_score}/10. "
        )
        if context.constraints.active_constraints:
            constraint_summary += f"Active: {', '.join(context.constraints.active_constraints[:3])}. "
        
        # Environment summary
        env_level = "very simple" if context.environment.environment_complexity < 2 else \
                   "simple" if context.environment.environment_complexity < 4 else \
                   "moderate" if context.environment.environment_complexity < 6 else \
                   "complex" if context.environment.environment_complexity < 8 else \
                   "very complex"
        environment_summary = f"Environment: {env_level} (score {context.environment.environment_complexity}/10). "
        if context.environment.activity_restrictions:
            environment_summary += f"Restricted: {', '.join(context.environment.activity_restrictions[:3])}. "
        if context.environment.available_activity_types:
            environment_summary += f"Available: {', '.join(context.environment.available_activity_types[:3])}. "
        
        # Forecast summary
        forecast_summary = ""
        if context.forecast.predicted_energy_dips:
            forecast_summary += f"Energy dips predicted: {', '.join(context.forecast.predicted_energy_dips)}. "
        if context.forecast.disruption_risk > 0.5:
            forecast_summary += f"High disruption risk ({context.forecast.disruption_risk:.0%}). "
        if context.forecast.recovery_opportunity:
            forecast_summary += f"Recovery opportunity: {context.forecast.recovery_opportunity}. "
        if not forecast_summary:
            forecast_summary = "No major forecast concerns. "
        
        # Life mode summary
        lifemode_summary = f"Life mode: {context.lifemode.life_mode}. "
        lifemode_summary += f"Planning approach: {context.lifemode.planning_approach.value}. "
        if context.lifemode.mode_profile:
            lifemode_summary += f"Profile: {', '.join(str(k) for k in list(context.lifemode.mode_profile.keys())[:2])}. "
        
        # Overall summary
        overall_text = (
            f"User {context.user_id} in {context.lifemode.life_mode} mode. "
            f"{energy_summary} "
            f"{constraint_summary} "
            f"{environment_summary} "
            f"{forecast_summary} "
            f"Focus on {context.lifemode.planning_approach.value} planning. "
        )
        
        # Calculate compression ratio
        original_size = len(json.dumps(context.model_dump()))
        compressed_size = len(overall_text)
        compression_ratio = compressed_size / original_size if original_size > 0 else 0
        
        logger.info(f"Compression ratio: {compression_ratio:.2%}")
        
        return CompressedContextSummary(
            summary_text=overall_text,
            energy_summary=energy_summary,
            constraint_summary=constraint_summary,
            environment_summary=environment_summary,
            forecast_summary=forecast_summary,
            lifemode_summary=lifemode_summary,
            original_context_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
        )
        
    except Exception as e:
        logger.error(f"Error compressing context: {str(e)}")
        raise


# ============================================================================
# Prompt Building
# ============================================================================

SYSTEM_PROMPT_TEMPLATE = """You are an expert constraint-aware wellness planner.

Your role is to generate realistic, achievable wellness plans that respect:
- Energy budget limitations
- Physical environment constraints
- User's life mode and capacity
- Predicted disruptions and opportunities

Generate plans that are practical and sustainable, not idealistic.
Prioritize recovery and consistency over intensity.
Adapt recommendations to current context."""


def build_planning_prompt(context_summary: CompressedContextSummary, 
                         context: PlanningContext) -> PlanningPrompt:
    """
    Construct structured LLM prompt.
    
    Combines system instructions with compressed context and task.
    
    Args:
        context_summary: Compressed context
        context: Original context for reference data
        
    Returns:
        PlanningPrompt ready for LLM
    """
    logger.debug(f"Building planning prompt")
    
    try:
        # Build user prompt
        user_prompt = f"""
Based on the following user context, generate a realistic daily wellness plan:

{context_summary.summary_text}

ENERGY DETAILS:
{context_summary.energy_summary}

CONSTRAINTS:
{context_summary.constraint_summary}

ENVIRONMENT:
{context_summary.environment_summary}

FORECAST:
{context_summary.forecast_summary}

Available activity types: {', '.join(context.environment.available_activity_types) if context.environment.available_activity_types else 'standard activities'}

REQUIREMENTS:
1. Total energy allocated must not exceed {context.energy.daily_budget} units
2. Respect all activity restrictions
3. Adapt activities as needed to environment
4. Include recovery blocks as appropriate
5. Match planning approach: {context.lifemode.planning_approach.value}

OUTPUT FORMAT:
Provide the plan as a structured JSON with this format:
{{
  "plan_id": "candidate_[timestamp]",
  "morning_activities": [
    {{"activity": "name", "duration_minutes": 20, "energy_cost": 5, "description": "..."}}
  ],
  "afternoon_activities": [...],
  "evening_activities": [...],
  "recovery_blocks": [...],
  "total_energy_allocated": 50,
  "plan_rationale": "Why this plan makes sense for this user..."
}}

Generate the plan now."""
        
        # Build constraints list
        constraints = [
            f"Maximum energy budget: {context.energy.daily_budget} units",
            f"Must respect environment constraints",
            f"Must avoid restricted activities: {', '.join(context.environment.activity_restrictions[:5]) if context.environment.activity_restrictions else 'none'}",
            f"Must use available activity types",
            f"Must be sustainable for {context.lifemode.life_mode} life mode",
        ]
        
        prompt = PlanningPrompt(
            system_prompt=SYSTEM_PROMPT_TEMPLATE,
            user_prompt=user_prompt,
            context_data={
                "energy_budget": context.energy.daily_budget,
                "remaining_energy": context.energy.remaining_energy,
                "life_mode": context.lifemode.life_mode,
                "planning_approach": context.lifemode.planning_approach.value,
                "constraint_pressure": context.constraints.pressure_level,
                "environment_complexity": context.environment.environment_complexity,
            },
            constraints=constraints,
            output_format="json",
        )
        
        logger.info("Planning prompt constructed")
        return prompt
        
    except Exception as e:
        logger.error(f"Error building prompt: {str(e)}")
        raise


def validate_prompt_size(prompt: PlanningPrompt) -> Tuple[bool, Optional[str]]:
    """
    Validate prompt fits within size constraints.
    
    Args:
        prompt: Prompt to validate
        
    Returns:
        (is_valid, error_message) tuple
    """
    full_prompt = f"{prompt.system_prompt}\n{prompt.user_prompt}"
    size_bytes = len(full_prompt.encode('utf-8'))
    
    if size_bytes > MAX_PROMPT_SIZE_BYTES:
        error = f"Prompt too large: {size_bytes} bytes > {MAX_PROMPT_SIZE_BYTES} max"
        logger.warning(error)
        return False, error
    
    logger.debug(f"Prompt size valid: {size_bytes} bytes")
    return True, None


# ============================================================================
# LLM Invocation
# ============================================================================
# NOTE: LLM invocation moved to Module B (backend/src/module_b/llm_engine/)
# Use OllamaClient from Module B instead.
#
# from ..module_b.llm_engine import OllamaClient
# client = OllamaClient(model="mistral")
# response = client.generate(prompt_text)


# ============================================================================
# Response Parsing
# ============================================================================
# NOTE: Response parsing moved to Plan Parser module
# (separate module between Plan Request Interface and Plan Validator)
#
# This separation ensures clean responsibility division:
# - Plan Request Interface: Build prompt + call Module B
# - Plan Parser: Parse LLM response into structured plan
# - Plan Validator: Validate plan and constraints


# ============================================================================
# Fallback Plans
# ============================================================================

def create_fallback_plan(approach: PlanningApproach, 
                        candidate_id: str,
                        energy_budget: int) -> PlanCandidate:
    """
    Generate fallback plan when LLM unavailable.
    
    Uses predefined plans by approach type.
    Adjusts energy allocation if needed.
    
    Args:
        approach: Planning approach
        candidate_id: Candidate ID
        energy_budget: Total energy available
        
    Returns:
        PlanCandidate with fallback plan
    """
    logger.info(f"Creating fallback plan: {approach.value}, budget {energy_budget}")
    
    try:
        plan_template = FALLBACK_ACTIVITIES_BY_APPROACH.get(
            approach,
            FALLBACK_ACTIVITIES_BY_APPROACH[PlanningApproach.STANDARD]
        )
        
        # Parse activities into timeblocks
        morning = [
            PlanTimeblock(**activity)
            for activity in plan_template.get("morning_activities", [])
        ]
        afternoon = [
            PlanTimeblock(**activity)
            for activity in plan_template.get("afternoon_activities", [])
        ]
        evening = [
            PlanTimeblock(**activity)
            for activity in plan_template.get("evening_activities", [])
        ]
        recovery = [
            PlanTimeblock(**activity)
            for activity in plan_template.get("recovery_blocks", [])
        ]
        
        total_energy = sum(
            a.energy_cost for a in morning + afternoon + evening + recovery
        )
        
        # Scale if needed
        if total_energy > energy_budget:
            scale_factor = energy_budget / total_energy if total_energy > 0 else 1.0
            for activities in [morning, afternoon, evening, recovery]:
                for activity in activities:
                    activity.energy_cost = max(1, int(activity.energy_cost * scale_factor))
            total_energy = sum(
                a.energy_cost for a in morning + afternoon + evening + recovery
            )
        
        plan = DailyWellnessPlan(
            plan_id=candidate_id,
            morning_activities=morning,
            afternoon_activities=afternoon,
            evening_activities=evening,
            recovery_blocks=recovery,
            total_energy_allocated=total_energy,
            plan_rationale=f"Fallback plan for {approach.value} approach",
            adaptability_score=0.8,
        )
        
        candidate = PlanCandidate(
            candidate_id=candidate_id,
            source="fallback",
            plan=plan,
            raw_response=json.dumps(plan.model_dump()),
            status=PlanStatus.GENERATED,
            generated_at=datetime.utcnow(),
        )
        
        logger.info(f"Fallback plan created: {total_energy} energy")
        return candidate
        
    except Exception as e:
        logger.error(f"Error creating fallback plan: {str(e)}")
        # Return minimal fallback
        return PlanCandidate(
            candidate_id=candidate_id,
            source="fallback_error",
            raw_response="",
            status=PlanStatus.REJECTED,
            validation_errors=[f"Fallback creation error: {str(e)}"],
        )
