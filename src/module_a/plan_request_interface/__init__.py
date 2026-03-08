"""
Plan Request Interface Package

Module A (Orchestration) - Constraint-First Wellness Agent

Responsibilities:
1. Aggregate all upstream planning signals
2. Compress context for LLM consumption
3. Construct structured planning prompts
4. Invoke Ollama to generate plans
5. Parse LLM responses into structured plans
6. Provide fallback plans when LLM unavailable
7. Update state with plan candidates
8. Append execution traces

This is the first module to interact with the LLM (Module B).

Key Components:
- Models: Data structures for context, prompts, responses
- Utils: Functions for context building, compression, prompting
- Builder: Orchestration class for complete workflow
- Node: LangGraph integration

Quick Start:

    # Using the convenience function
    candidate, metadata = build_and_request_plan(state)
    
    # Using the builder class
    builder = PlanRequestBuilder()
    candidate, metadata = builder.request_plan(state)
    
    # Using the LangGraph node
    updated_state = plan_request_node(state)
"""

__version__ = "1.0.0"
__module_name__ = "Plan Request Interface"
__description__ = "Requests wellness plan from LLM and manages responses"

# Import models
from .plan_request_models import (
    # Enums
    PlanningApproach,
    ActivityTimeblock,
    PlanStatus,
    LLMProvider,
    
    # Context models
    EnergyContextSnapshot,
    ConstraintContextSnapshot,
    EnvironmentContextSnapshot,
    ForecastContextSnapshot,
    LifemodeContextSnapshot,
    PlanningContext,
    
    # Compression
    CompressedContextSummary,
    
    # Prompt
    PlanningPrompt,
    
    # Plans
    PlanTimeblock,
    DailyWellnessPlan,
    PlanCandidate,
    
    # LLM interaction
    LLMRequest,
    LLMResponse,
    
    # Tracing
    PlanRequestExecutionTrace,
)

# Import utilities
from .plan_request_utils import (
    # Context functions
    build_planning_context,
    determine_planning_approach,
    compress_planning_context,
    
    # Prompt functions
    build_planning_prompt,
    validate_prompt_size,
    
    # LLM functions
    request_plan_from_llm,
    parse_plan_response,
    
    # Fallback
    create_fallback_plan,
    
    # Constants
    MAX_PROMPT_SIZE_BYTES,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    OLLAMA_API_ENDPOINT,
)

# Import builder
from .plan_request_builder import (
    PlanRequestBuilder,
    build_and_request_plan,
    request_plan_with_fallback,
)

# Import node
from .plan_request_node import (
    plan_request_node,
    get_plan_request_node_config,
    validate_node_inputs,
    extract_planning_signals,
    get_candidate_summary,
)

# Public API
__all__ = [
    # Enums
    "PlanningApproach",
    "ActivityTimeblock",
    "PlanStatus",
    "LLMProvider",
    
    # Context
    "EnergyContextSnapshot",
    "ConstraintContextSnapshot",
    "EnvironmentContextSnapshot",
    "ForecastContextSnapshot",
    "LifemodeContextSnapshot",
    "PlanningContext",
    "CompressedContextSummary",
    
    # Prompt
    "PlanningPrompt",
    
    # Plans
    "PlanTimeblock",
    "DailyWellnessPlan",
    "PlanCandidate",
    
    # LLM
    "LLMRequest",
    "LLMResponse",
    
    # Tracing
    "PlanRequestExecutionTrace",
    
    # Functions
    "build_planning_context",
    "determine_planning_approach",
    "compress_planning_context",
    "build_planning_prompt",
    "validate_prompt_size",
    "request_plan_from_llm",
    "parse_plan_response",
    "create_fallback_plan",
    
    # Builder
    "PlanRequestBuilder",
    "build_and_request_plan",
    "request_plan_with_fallback",
    
    # Node
    "plan_request_node",
    "get_plan_request_node_config",
    "validate_node_inputs",
    "extract_planning_signals",
    "get_candidate_summary",
    
    # Constants
    "MAX_PROMPT_SIZE_BYTES",
    "DEFAULT_LLM_MODEL",
    "DEFAULT_LLM_TIMEOUT_SECONDS",
    "OLLAMA_API_ENDPOINT",
]


def get_module_info() -> dict:
    """Get module information."""
    return {
        "name": __module_name__,
        "version": __version__,
        "description": __description__,
        "module_a_component": True,
        "workflow_position": 7,
        "is_llm_interface": True,
        "responsibilities": [
            "Aggregate planning signals from upstream modules",
            "Compress context for LLM",
            "Build structured prompts",
            "Request plans from Ollama",
            "Parse and validate responses",
            "Provide fallbacks",
            "Manage execution traces",
        ],
    }
