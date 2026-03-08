"""
Life Mode Controller Node - LangGraph Integration

LangGraph node for life mode controller.
Integrates life mode selection into the constraint-first wellness workflow.

Position in workflow:
User Input
   ↓
Constraint Analyzer
   ↓
Constraint Forecast Engine
   ↓
Energy Budget Manager
   ↓
Environment Adapter
   ↓
Life Mode Controller   ← THIS NODE
   ↓
Plan Request Node (LLM)

Module: Life Mode Controller
Part of: Constraint-First Wellness Agent (Module A)

Schema Compliance Notes:
- CORRECTION: No new top-level state fields
- Only updates: life_mode, system_flags, execution_trace, last_node_executed
- Input sources: All upstream analysis results
- Output: state.life_mode and system_flags.active_mode metadata
- Metadata stored in: system_flags.mode_* fields
- Timestamps use ISO format
"""

import logging
import time
from typing import Dict, Any
from datetime import datetime
from copy import deepcopy

from life_mode_controller import LifeModeController

logger = logging.getLogger(__name__)


def life_mode_controller_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for life mode controller.
    
    Orchestrates the complete life mode detection and selection workflow.
    
    Inputs from state:
    - system_flags.constraint_pressure_level
    - system_flags.overload_detected
    - energy_budget.daily_budget
    - energy_budget.remaining_energy
    - environment_context.environment_stability_score
    - environment_context.social_obligations_weekly
    - forecast_data.predicted_energy_dips
    - forecast_data.forecast_window_days
    - constraints
    - constraint_analysis
    - user_history
    
    Updates to state:
    - life_mode (new/updated)
    - system_flags.active_mode
    - system_flags.mode_reason
    - system_flags.mode_confidence
    - system_flags.mode_profile
    - system_flags.mode_stability
    - system_flags.mode_expected_duration_hours
    - execution_trace (appended)
    - last_node_executed
    
    Args:
        state: Current LangGraph agent state
        
    Returns:
        Updated state with selected life mode and metadata
        
    Raises:
        ValueError: If critical state fields are missing
        Exception: For unexpected errors during mode selection
    """
    start_time = time.time()
    
    try:
        logger.info("=" * 80)
        logger.info("LIFE MODE CONTROLLER NODE START")
        logger.info("=" * 80)
        
        # Make a copy to avoid mutating original state outside of this function
        updated_state = deepcopy(state)
        
        # ====================================================================
        # STEP 1: Validation
        # ====================================================================
        logger.info("Step 1: Validating state inputs...")
        
        _validate_state_inputs(state)
        logger.debug("✓ State inputs validated")
        
        # ====================================================================
        # STEP 2: Initialize controller
        # ====================================================================
        logger.info("Step 2: Initializing life mode controller...")
        
        controller = LifeModeController()
        logger.debug("✓ Controller initialized")
        
        # ====================================================================
        # STEP 3: Perform mode selection
        # ====================================================================
        logger.info("Step 3: Performing life mode selection...")
        
        selection = controller.select_life_mode(state)
        
        logger.info(
            f"✓ Mode selection complete: {selection.selected_mode.value} "
            f"(confidence: {selection.confidence_score:.0%})"
        )
        
        # ====================================================================
        # STEP 4: Update state with selected mode
        # ====================================================================
        logger.info("Step 4: Updating state with selected mode...")
        
        updated_state = controller.update_state_with_mode(updated_state, selection)
        logger.debug("✓ State updated")
        
        # ====================================================================
        # STEP 5: Append execution trace
        # ====================================================================
        logger.info("Step 5: Appending execution trace...")
        
        updated_state = controller.append_execution_trace(updated_state, selection)
        logger.debug("✓ Trace entry appended")
        
        # ====================================================================
        # STEP 6: Set last_node_executed flag
        # ====================================================================
        logger.info("Step 6: Setting last_node_executed flag...")
        
        updated_state = controller.set_last_node_executed(updated_state)
        logger.debug("✓ Flag set")
        
        # ====================================================================
        # STEP 7: Calculate execution time
        # ====================================================================
        elapsed_time = time.time() - start_time
        
        # ====================================================================
        # Final logging
        # ====================================================================
        logger.info("=" * 80)
        logger.info("LIFE MODE CONTROLLER NODE COMPLETE")
        logger.info(f"Selected Mode: {selection.selected_mode.value}")
        logger.info(f"Confidence: {selection.confidence_score:.0%}")
        logger.info(f"Signals Triggered: {len(selection.triggering_signals)}")
        logger.info(f"Processing Time: {elapsed_time:.3f}s")
        logger.info("=" * 80)
        
        return updated_state
    
    except ValueError as e:
        logger.error(f"State validation error: {e}")
        raise
    except KeyError as e:
        logger.error(f"Missing state field: {e}")
        raise ValueError(f"Required state field missing: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in life_mode_controller_node: {e}", exc_info=True)
        raise


def _validate_state_inputs(state: Dict[str, Any]) -> None:
    """
    Validate that all required state inputs are present.
    
    Required fields:
    - user_id
    - system_flags
    - energy_budget
    - environment_context
    - forecast_data
    - constraints
    - constraint_analysis
    - user_history
    
    Args:
        state: State to validate
        
    Raises:
        ValueError: If required fields are missing
    """
    required_fields = [
        "user_id",
        "system_flags",
        "energy_budget",
        "environment_context",
        "forecast_data",
        "constraints",
        "constraint_analysis",
        "user_history",
    ]
    
    missing_fields = [f for f in required_fields if f not in state]
    
    if missing_fields:
        raise ValueError(f"Missing required state fields: {missing_fields}")
    
    # Validate nested system_flags
    required_system_flags = [
        "constraint_pressure_level",
        "overload_detected",
    ]
    
    system_flags = state.get("system_flags", {})
    missing_flags = [f for f in required_system_flags if f not in system_flags]
    
    if missing_flags:
        raise ValueError(f"Missing required system_flags: {missing_flags}")
    
    # Validate nested energy_budget
    required_energy_fields = [
        "daily_budget",
        "remaining_energy",
    ]
    
    energy_budget = state.get("energy_budget", {})
    missing_energy = [f for f in required_energy_fields if f not in energy_budget]
    
    if missing_energy:
        logger.warning(f"Missing energy_budget fields (using defaults): {missing_energy}")
    
    logger.debug("✓ All required state fields present")
