"""
Supabase Persistence Layer

Manages all database operations for state persistence.
Handles user profiles, constraints, plans, and metrics storage.

Module: State Model & Persistence Layer
Part of: Constraint-First Wellness Agent
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import logging
from .agent_state import AgentState
from .validators import StateValidator, StateValidationError

logger = logging.getLogger(__name__)


def _convert_datetime_to_iso(obj: Any) -> Any:
    """
    Recursively convert datetime objects to ISO format strings.
    Handles dictionaries, lists, and nested structures.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: _convert_datetime_to_iso(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_datetime_to_iso(item) for item in obj]
    return obj


class SupabaseConfig:
    """Supabase configuration holder."""
    
    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
    ):
        self.url = url or ""
        self.key = key or ""
        self.is_configured = bool(self.url and self.key)


class SupabasePersistence:
    """
    Manages state persistence with Supabase (PostgreSQL).
    
    Tables:
      - users: User profiles and metadata
      - constraints: Constraint history
      - plans: Generated plans
      - energy_logs: Energy usage tracking
      - weekly_metrics: Aggregated weekly statistics
      - micro_wins: User micro-wins history
    """

    def __init__(self, config: SupabaseConfig):
        """
        Initialize persistence layer.
        
        Args:
            config: SupabaseConfig with URL and key
        """
        self.config = config
        self.client = None
        
        if config.is_configured:
            try:
                from supabase import create_client
                self.client = create_client(config.url, config.key)
                logger.info("Supabase client initialized")
            except ImportError:
                logger.warning("supabase-py not installed. Install with: pip install supabase-py")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")

    def is_available(self) -> bool:
        """Check if Supabase is configured and available."""
        return self.client is not None

    # ============================================================================
    # User Profile Operations
    # ============================================================================

    def save_user_profile(self, user_id: str, state: AgentState) -> bool:
        """
        Save user profile to database.
        
        Args:
            user_id: User ID
            state: Current agent state
            
        Returns:
            True if successful
        """
        if not self.is_available():
            logger.warning("Supabase not available, skipping user profile save")
            return False

        try:
            profile_data = {
                "id": user_id,
                "life_mode": state.life_mode.value,
                "motivation_style": state.motivation_style.value,
                "is_onboarded": state.system_flags.is_onboarded,
                "total_plans": state.user_history.total_plans_generated,
                "plans_completed": state.user_history.plans_completed,
                "micro_wins_achieved": state.user_history.micro_wins_achieved,
                "days_active": state.user_history.days_active,
                "last_interaction": state.user_history.last_interaction.isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Upsert to handle both insert and update
            response = self.client.table("users").upsert(profile_data).execute()
            logger.info(f"User profile saved for {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")
            return False

    def load_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Load user profile from database.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile or None if not found
        """
        if not self.is_available():
            logger.warning("Supabase not available, cannot load user profile")
            return None

        try:
            response = self.client.table("users").select("*").eq("id", user_id).execute()
            if response.data and len(response.data) > 0:
                logger.info(f"User profile loaded for {user_id}")
                return response.data[0]
            else:
                logger.info(f"No user profile found for {user_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to load user profile: {e}")
            return None

    # ============================================================================
    # Constraint Operations
    # ============================================================================

    def save_constraints(self, user_id: str, constraints: List[Dict[str, Any]]) -> bool:
        """
        Save user constraints to database.
        
        Args:
            user_id: User ID
            constraints: List of constraint dictionaries
            
        Returns:
            True if successful
        """
        if not self.is_available():
            logger.warning("Supabase not available, skipping constraints save")
            return False

        try:
            constraint_records = []
            for constraint in constraints:
                # Convert constraint to dict if it's a Pydantic model
                if hasattr(constraint, 'dict'):
                    constraint_dict = constraint.dict()
                else:
                    constraint_dict = constraint
                
                # Convert all datetime objects to ISO strings
                constraint_dict = _convert_datetime_to_iso(constraint_dict)
                
                record = {
                    **constraint_dict,
                    "user_id": user_id,
                    "created_at": constraint_dict.get("created_at") or datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                constraint_records.append(record)

            # Delete old constraints and insert new ones
            self.client.table("constraints").delete().eq("user_id", user_id).execute()
            if constraint_records:
                self.client.table("constraints").insert(constraint_records).execute()

            logger.info(f"Saved {len(constraint_records)} constraints for {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save constraints: {e}")
            return False

    def load_constraints(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Load user constraints from database.
        
        Args:
            user_id: User ID
            
        Returns:
            List of constraint dictionaries
        """
        if not self.is_available():
            logger.warning("Supabase not available, returning empty constraints")
            return []

        try:
            response = self.client.table("constraints").select("*").eq("user_id", user_id).execute()
            logger.info(f"Loaded {len(response.data)} constraints for {user_id}")
            return response.data or []

        except Exception as e:
            logger.error(f"Failed to load constraints: {e}")
            return []

    # ============================================================================
    # Plan Operations
    # ============================================================================

    def save_plan(self, user_id: str, plan: Dict[str, Any]) -> bool:
        """
        Save generated plan to database.
        
        Args:
            user_id: User ID
            plan: Plan dictionary
            
        Returns:
            True if successful
        """
        if not self.is_available():
            logger.warning("Supabase not available, skipping plan save")
            return False

        try:
            # Convert plan to dict if it's a Pydantic model
            if hasattr(plan, 'dict'):
                plan_dict = plan.dict()
            else:
                plan_dict = plan
            
            # Convert all datetime objects to ISO strings
            plan_dict = _convert_datetime_to_iso(plan_dict)
            
            plan_record = {
                **plan_dict,
                "user_id": user_id,
                "created_at": plan_dict.get("created_at") or datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = self.client.table("plans").insert([plan_record]).execute()
            logger.info(f"Plan saved for {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save plan: {e}")
            return False

    def get_recent_plans(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent plans for user.
        
        Args:
            user_id: User ID
            limit: Maximum number of plans to return
            
        Returns:
            List of plans
        """
        if not self.is_available():
            return []

        try:
            response = (
                self.client.table("plans")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.error(f"Failed to load plans: {e}")
            return []

    # ============================================================================
    # Energy Logging
    # ============================================================================

    def log_energy_usage(
        self,
        user_id: str,
        period: str,
        usage: float,
        notes: Optional[str] = None
    ) -> bool:
        """
        Log energy usage data.
        
        Args:
            user_id: User ID
            period: Time period (morning/afternoon/evening)
            usage: Energy value used
            notes: Optional notes
            
        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            record = {
                "user_id": user_id,
                "period": period,
                "usage": usage,
                "notes": notes,
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.client.table("energy_logs").insert([record]).execute()
            logger.info(f"Energy usage logged for {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to log energy usage: {e}")
            return False

    def get_energy_history(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get energy usage history.
        
        Args:
            user_id: User ID
            days: Number of days to retrieve
            
        Returns:
            List of energy log records
        """
        if not self.is_available():
            return []

        try:
            cutoff_date = (datetime.utcnow() - __import__('datetime').timedelta(days=days)).isoformat()
            response = (
                self.client.table("energy_logs")
                .select("*")
                .eq("user_id", user_id)
                .gte("timestamp", cutoff_date)
                .order("timestamp", desc=True)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.error(f"Failed to load energy history: {e}")
            return []

    # ============================================================================
    # Weekly Metrics
    # ============================================================================

    def save_weekly_metrics(
        self,
        user_id: str,
        week_start: datetime,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        Save weekly aggregated metrics.
        
        Args:
            user_id: User ID
            week_start: Start date of week
            metrics: Metrics dictionary
            
        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            record = {
                "user_id": user_id,
                "week_start": week_start.isoformat(),
                "stability_score": metrics.get("stability_score", 0),
                "completion_rate": metrics.get("completion_rate", 0),
                "energy_score": metrics.get("energy_score", 0),
                "notes": metrics.get("notes", ""),
                "updated_at": datetime.utcnow().isoformat(),
            }

            self.client.table("weekly_metrics").upsert([record]).execute()
            logger.info(f"Weekly metrics saved for {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save weekly metrics: {e}")
            return False

    def get_weekly_metrics(self, user_id: str, weeks: int = 12) -> List[Dict[str, Any]]:
        """
        Get historical weekly metrics.
        
        Args:
            user_id: User ID
            weeks: Number of weeks to retrieve
            
        Returns:
            List of weekly metric records
        """
        if not self.is_available():
            return []

        try:
            response = (
                self.client.table("weekly_metrics")
                .select("*")
                .eq("user_id", user_id)
                .order("week_start", desc=True)
                .limit(weeks)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.error(f"Failed to load weekly metrics: {e}")
            return []

    # ============================================================================
    # Micro-wins
    # ============================================================================

    def save_micro_win(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Record a micro-win achievement.
        
        Args:
            user_id: User ID
            title: Micro-win title
            description: Optional description
            category: Optional category
            
        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            record = {
                "user_id": user_id,
                "title": title,
                "description": description,
                "category": category,
                "created_at": datetime.utcnow().isoformat(),
            }

            self.client.table("micro_wins").insert([record]).execute()
            logger.info(f"Micro-win recorded for {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save micro-win: {e}")
            return False

    def get_micro_wins(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get micro-wins history.
        
        Args:
            user_id: User ID
            limit: Maximum number to return
            
        Returns:
            List of micro-win records
        """
        if not self.is_available():
            return []

        try:
            response = (
                self.client.table("micro_wins")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.error(f"Failed to load micro-wins: {e}")
            return []

    # ============================================================================
    # Full State Persistence
    # ============================================================================

    def save_full_state(self, state: AgentState) -> bool:
        """
        Save complete state to database across multiple tables with versioning.
        
        Implements optimistic concurrency control: if version mismatch occurs,
        the save fails and caller should reload latest state and retry.
        
        Args:
            state: Full agent state
            
        Returns:
            True if successful
        """
        success = True

        # Save user profile with version check
        if not self.save_user_profile(state.user_id, state):
            success = False

        # Save constraints
        constraints_data = [c.dict() for c in state.constraints]
        if not self.save_constraints(state.user_id, constraints_data):
            success = False

        # Save plan if exists
        if state.plan:
            if not self.save_plan(state.user_id, state.plan.dict()):
                success = False

        # Save atomic snapshot (Correction 3, 8)
        if not self.save_state_snapshot(state):
            success = False

        logger.info(f"Full state saved for {state.user_id}, version={state.state_version}, success={success}")
        return success

    def load_full_state(self, user_id: str) -> Optional[AgentState]:
        """
        Load complete state from database.
        
        Args:
            user_id: User ID
            
        Returns:
            Reconstructed AgentState or None if user not found
        """
        try:
            profile = self.load_user_profile(user_id)
            if not profile:
                logger.info(f"No profile found for user {user_id}")
                return None

            constraints_data = self.load_constraints(user_id)
            recent_plans = self.get_recent_plans(user_id, limit=1)

            # Reconstruct state with all required fields (Correction 3, 4, 5, 6, 7, 9)
            state_data = {
                "user_id": user_id,
                "state_version": profile.get("version", 0),  # Concurrency control
                "life_mode": profile.get("life_mode", "maintenance"),
                "motivation_style": profile.get("motivation_style", "progress_tracking"),
                "constraints": constraints_data,
                # Forecast data (Correction 4: expanded fields)
                "forecast_data": {
                    "period": "week",
                    "predicted_energy_level": 50.0,
                    "expected_disruptions": [],
                    "opportunity_windows": [],
                    "confidence_score": 0.5,
                    "upcoming_constraints": [],
                    "predicted_energy_dips": [],
                    "predicted_schedule_disruptions": [],
                    "forecast_confidence": 0.5,
                    "forecast_window_days": 7,
                    "generated_at": datetime.utcnow().isoformat(),
                    "expires_at": datetime.utcnow().isoformat(),
                },
                # Energy budget (Correction 5: task-level allocation)
                "energy_budget": {
                    "daily_total": 100,
                    "morning": 30,
                    "afternoon": 40,
                    "evening": 20,
                    "contingency": 10,
                    "last_updated": datetime.utcnow().isoformat(),
                    "daily_budget": 100,
                    "allocated_energy": 0,
                    "remaining_energy": 100,
                    "task_energy_costs": {},
                    "recovery_factor": 0.8,
                },
                # Environment context (Correction 6: environmental limitations)
                "environment_context": {
                    "timezone": "UTC",
                    "work_hours": {"start": "09:00", "end": "17:00"},
                    "commute_time_minutes": 0,
                    "social_obligations_weekly": 0,
                    "caregiving_hours_weekly": 0.0,
                    "pets": 0,
                    "living_situation": "independent",
                    "updated_at": datetime.utcnow().isoformat(),
                    "indoor_only": False,
                    "small_space": False,
                    "silent_required": False,
                    "shared_room": False,
                    "equipment_available": [],
                },
                "user_history": {
                    "total_plans_generated": profile.get("total_plans", 0),
                    "plans_completed": profile.get("plans_completed", 0),
                    "micro_wins_achieved": profile.get("micro_wins_achieved", 0),
                    "days_active": profile.get("days_active", 0),
                    "last_interaction": profile.get("last_interaction", datetime.utcnow().isoformat()),
                    "feedback_provided": 0,
                    "average_plan_completion": 0.5,
                },
                # System flags (Correction 7: orchestration control signals)
                "system_flags": {
                    "is_onboarded": profile.get("is_onboarded", False),
                    "requires_replan": False,
                    "emergency_mode": False,
                    "data_sync_pending": False,
                    "last_sync": datetime.utcnow().isoformat(),
                    "reentry_required": False,
                    "overload_detected": False,
                    "simulation_mode": False,
                    "plan_locked": False,
                    "forecast_stale": False,
                },
                # Graph debug metadata (Correction 9)
                "last_node_executed": None,
                "execution_trace": [],
            }

            if recent_plans:
                state_data["plan"] = recent_plans[0]

            state = AgentState(**state_data)
            StateValidator.assert_valid_state(state)
            logger.info(f"Full state loaded for {user_id}")
            return state

        except Exception as e:
            logger.error(f"Failed to load full state: {e}")
            return None


    # ============================================================================
    # Atomic State Snapshot (Correction 8)
    # ============================================================================

    def save_state_snapshot(self, state: AgentState) -> bool:
        """
        Save complete agent state as atomic snapshot for authoritative source.
        
        This snapshot table acts as the primary state source for LangGraph,
        preventing partial saves and race conditions.
        
        Args:
            state: Full agent state to snapshot
            
        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            state_json = state.dict(exclude_unset=False, by_alias=False)
            state_json = _convert_datetime_to_iso(state_json)

            response = (
                self.client.table("agent_state_snapshots")
                .upsert({
                    "user_id": state.user_id,
                    "state_json": state_json,
                    "version": state.state_version + 1,  # Increment on save
                    "updated_at": datetime.utcnow().isoformat(),
                })
                .execute()
            )

            logger.info(f"State snapshot saved for {state.user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save state snapshot: {e}")
            return False

    def load_state_snapshot(self, user_id: str) -> Optional[AgentState]:
        """
        Load authoritative state from snapshot table.
        
        Args:
            user_id: User ID
            
        Returns:
            Reconstructed AgentState or None if not found
        """
        if not self.is_available():
            return None

        try:
            response = (
                self.client.table("agent_state_snapshots")
                .select("state_json, version")
                .eq("user_id", user_id)
                .single()
                .execute()
            )

            if not response.data:
                logger.info(f"No state snapshot found for user {user_id}")
                return None

            state_data = response.data["state_json"]
            version = response.data["version"]

            # Reconstruct AgentState
            state = AgentState(**state_data)
            state.state_version = version
            StateValidator.assert_valid_state(state)

            logger.info(f"State snapshot loaded for {user_id}, version={version}")
            return state

        except Exception as e:
            logger.error(f"Failed to load state snapshot: {e}")
            return None


# ============================================================================
# Singleton persistence instance
# ============================================================================


def initialize_persistence(url: str, key: str) -> SupabasePersistence:
    """
    Initialize the global persistence layer.
    
    Args:
        url: Supabase URL
        key: Supabase API key
        
    Returns:
        Configured SupabasePersistence instance
    """
    global _persistence_instance
    config = SupabaseConfig(url=url, key=key)
    _persistence_instance = SupabasePersistence(config)
    return _persistence_instance


def get_persistence() -> SupabasePersistence:
    """
    Get the global persistence instance.
    
    Returns:
        SupabasePersistence instance
    """
    global _persistence_instance
    if _persistence_instance is None:
        # Initialize with empty config if not already done
        _persistence_instance = SupabasePersistence(SupabaseConfig())
    return _persistence_instance
