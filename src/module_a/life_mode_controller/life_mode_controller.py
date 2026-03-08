"""
Life Mode Controller

Main orchestrator for life mode detection and selection.
Integrates signal detection, priority resolution, and profile lookup.

Module: Life Mode Controller
Part of: Constraint-First Wellness Agent (Module A)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from life_mode_models import (
    LifeModeName,
    LifeModeDetectionResult,
    LifeModeSelection,
    ModeProfile,
)
from life_mode_utils import (
    detect_life_mode,
    resolve_mode_priority,
    get_mode_profile,
    calculate_mode_confidence,
    generate_mode_reason,
    calculate_mode_stability,
    estimate_mode_duration,
)

logger = logging.getLogger(__name__)


class LifeModeController:
    """
    Main controller for life mode management.
    
    Responsibilities:
    1. Detect candidate life modes from system signals
    2. Resolve conflicts using priority hierarchy
    3. Calculate confidence scores
    4. Generate explanations
    5. Retrieve behavior profiles
    """

    def __init__(self):
        """Initialize life mode controller."""
        self.logger = logging.getLogger(__name__)
        self.last_selection: Optional[LifeModeSelection] = None

    def select_life_mode(self, state: Dict[str, Any]) -> LifeModeSelection:
        """
        Complete life mode selection workflow.
        
        Steps:
        1. Detect candidate modes and their signals
        2. Resolve priority conflicts
        3. Retrieve behavior profile
        4. Calculate confidence
        5. Generate explanation
        6. Calculate stability estimates
        
        Args:
            state: Current agent state with all signals
            
        Returns:
            LifeModeSelection with complete metadata
        """
        self.logger.info("=" * 70)
        self.logger.info("LIFE MODE CONTROLLER: Starting mode selection")
        self.logger.info("=" * 70)
        
        # Step 1: Detect candidate modes
        self.logger.info("Step 1: Detecting candidate life modes...")
        detection_result = detect_life_mode(state)
        
        if not detection_result.candidate_modes:
            self.logger.warning("No candidate modes detected, using maintenance fallback")
            candidate_modes = [LifeModeName.MAINTENANCE]
        else:
            candidate_modes = detection_result.candidate_modes
        
        self.logger.info(
            f"Detected {len(candidate_modes)} candidate modes: "
            f"{[m.value for m in candidate_modes]}"
        )
        
        # Step 2: Resolve priority conflicts
        self.logger.info(f"Step 2: Resolving priority among {len(candidate_modes)} modes...")
        resolution = resolve_mode_priority(
            candidate_modes,
            detection_result.mode_signals,
        )
        
        selected_mode = resolution.selected_mode
        self.logger.info(f"Selected mode after priority resolution: {selected_mode.value}")
        if resolution.competing_modes:
            self.logger.info(
                f"Deprioritized modes: {[m.value for m in resolution.competing_modes[:2]]}"
            )
        
        # Step 3: Retrieve behavior profile
        self.logger.info(f"Step 3: Retrieving behavior profile for {selected_mode.value}...")
        profile = get_mode_profile(selected_mode)
        
        # Step 4: Calculate confidence
        self.logger.info("Step 4: Calculating confidence score...")
        signals_for_mode = detection_result.mode_signals.get(selected_mode.value, [])
        user_history = state.get("user_history", {})
        
        confidence, confidence_factors = calculate_mode_confidence(
            selected_mode, signals_for_mode, user_history
        )
        
        self.logger.info(
            f"Confidence score: {confidence:.2f} "
            f"({confidence:.0%})"
        )
        
        # Step 5: Generate explanation
        self.logger.info("Step 5: Generating mode explanation...")
        reason = generate_mode_reason(selected_mode, signals_for_mode, confidence)
        self.logger.info(f"Reason: {reason}")
        
        # Step 6: Calculate stability and duration estimates
        self.logger.info("Step 6: Calculating mode stability and duration...")
        stability = calculate_mode_stability(
            selected_mode,
            signals_for_mode,
            state.get("system_flags", {}).get("constraint_pressure_level", "LOW"),
        )
        
        duration_hours = estimate_mode_duration(
            selected_mode,
            signals_for_mode,
            state.get("forecast_data", {}).get("forecast_window_days", 7),
        )
        
        self.logger.info(f"Mode stability: {stability:.2f}, Duration estimate: {duration_hours} hours")
        
        # Build complete selection
        selection = LifeModeSelection(
            selected_mode=selected_mode,
            confidence_score=confidence,
            confidence_factors=confidence_factors,
            reason=reason,
            triggering_signals=[s.signal_name for s in signals_for_mode],
            profile=profile,
            mode_stability=stability,
            expected_duration_hours=duration_hours,
            created_at=datetime.utcnow(),
        )
        
        self.logger.info("=" * 70)
        self.logger.info("LIFE MODE CONTROLLER: Mode selection complete")
        self.logger.info("=" * 70)
        
        # Store for reference
        self.last_selection = selection
        
        return selection

    def update_state_with_mode(
        self,
        state: Dict[str, Any],
        selection: LifeModeSelection,
    ) -> Dict[str, Any]:
        """
        Update agent state with the selected life mode and related metadata.
        
        Updates:
        - state.life_mode
        - state.system_flags.active_mode
        - state.system_flags.mode_reason
        - state.system_flags.mode_confidence
        - state.system_flags.mode_profile
        
        Args:
            state: Current agent state
            selection: LifeModeSelection from select_life_mode()
            
        Returns:
            Updated state
        """
        self.logger.info(f"Updating state with selected mode: {selection.selected_mode.value}")
        
        # Update life_mode
        state["life_mode"] = selection.selected_mode.value
        
        # Update system_flags
        if "system_flags" not in state:
            state["system_flags"] = {}
        
        state["system_flags"]["active_mode"] = selection.selected_mode.value
        state["system_flags"]["mode_reason"] = selection.reason
        state["system_flags"]["mode_confidence"] = selection.confidence_score
        
        # Store profile as dict for JSON serialization
        profile_dict = {
            "mode": selection.profile.mode.value,
            "plan_complexity": selection.profile.plan_complexity.value,
            "activity_intensity": selection.profile.activity_intensity.value,
            "recovery_priority": selection.profile.recovery_priority.value,
            "description": selection.profile.description,
            "focus_areas": selection.profile.focus_areas,
            "avoid_areas": selection.profile.avoid_areas,
            "energy_protection": selection.profile.energy_protection,
        }
        state["system_flags"]["mode_profile"] = profile_dict
        
        # Store additional metadata
        state["system_flags"]["mode_stability"] = selection.mode_stability
        state["system_flags"]["mode_expected_duration_hours"] = selection.expected_duration_hours
        
        self.logger.info("State updated successfully")
        
        return state

    def append_execution_trace(
        self,
        state: Dict[str, Any],
        selection: LifeModeSelection,
    ) -> Dict[str, Any]:
        """
        Append execution trace entry for the life mode controller node.
        
        Trace format (JSON):
        {
          "node": "life_mode_controller",
          "timestamp": "ISO_TIME",
          "life_mode": "recovery",
          "confidence": 0.82,
          "signals_triggered": 3,
          "competing_modes": ["growth", "maintenance"]
        }
        
        Args:
            state: Current agent state
            selection: LifeModeSelection
            
        Returns:
            Updated state with trace entry
        """
        import json
        
        trace_entry = {
            "node": "life_mode_controller",
            "timestamp": datetime.utcnow().isoformat(),
            "life_mode": selection.selected_mode.value,
            "confidence": selection.confidence_score,
            "signals_triggered": len(selection.triggering_signals),
            "triggering_signals": selection.triggering_signals,
            "mode_stability": selection.mode_stability,
        }
        
        if "execution_trace" not in state:
            state["execution_trace"] = []
        
        # Append as JSON string for trace logging
        state["execution_trace"].append(json.dumps(trace_entry))
        
        self.logger.info(f"Execution trace appended: {json.dumps(trace_entry)}")
        
        return state

    def set_last_node_executed(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set the last_node_executed flag.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state
        """
        state["last_node_executed"] = "life_mode_controller"
        return state
