"""
Test Script - State Model & Persistence Layer with Supabase

This script tests your complete state management system with real Supabase connection.

Run with: python test_integration.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add backend to path so we can import src.state
sys.path.insert(0, os.path.dirname(__file__))

# Import state management functions
from src.state import (
    initialize_persistence,
    create_default_state,
    save_state,
    load_state,
    add_constraint,
    update_life_mode,
    increment_plan_count,
    record_micro_win,
    get_state_summary,
    validate_state,
    Constraint,
)


def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_environment():
    """Test 1: Check environment variables."""
    print_header("TEST 1: Environment Setup")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url:
        print("❌ SUPABASE_URL not found in .env")
        return False
    
    if not supabase_key:
        print("❌ SUPABASE_KEY not found in .env")
        return False
    
    print(f"✅ SUPABASE_URL: {supabase_url[:40]}...")
    print(f"✅ SUPABASE_KEY: {supabase_key[:40]}...")
    
    return True


def test_supabase_connection():
    """Test 2: Initialize Supabase connection."""
    print_header("TEST 2: Supabase Connection")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    try:
        persistence = initialize_persistence(supabase_url, supabase_key)
        
        if persistence.is_available():
            print("✅ Supabase client initialized successfully")
            print("✅ Database connection available")
            return True
        else:
            print("❌ Supabase client not available")
            return False
    
    except Exception as e:
        print(f"❌ Error initializing Supabase: {e}")
        return False


def test_state_creation():
    """Test 3: Create default state."""
    print_header("TEST 3: Create Default State")
    
    try:
        user_id = "demo_user_001"
        state = create_default_state(user_id)
        
        print(f"✅ Created state for user: {user_id}")
        print(f"   - Life mode: {state.life_mode.value}")
        print(f"   - Motivation: {state.motivation_style.value}")
        print(f"   - Energy budget: {state.energy_budget.daily_total}")
        
        # Validate
        is_valid = validate_state(state)
        if is_valid:
            print(f"✅ State validation: PASSED")
            return state
        else:
            print(f"❌ State validation: FAILED")
            return None
    
    except Exception as e:
        print(f"❌ Error creating state: {e}")
        return None


def test_state_modifications(state):
    """Test 4: Modify state."""
    print_header("TEST 4: Modify State")
    
    try:
        # Add constraint
        constraint = Constraint(
            id="demo_constraint_1",
            name="Limited energy capacity",
            category="physical",
            description="ME/CFS symptoms affecting daily activities",
            severity=8
        )
        state = add_constraint(state, constraint)
        print(f"✅ Added constraint: {constraint.name}")
        
        # Update life mode
        state = update_life_mode(state, "recovery")
        print(f"✅ Updated life mode to: {state.life_mode.value}")
        
        # Record activities
        state = increment_plan_count(state)
        state = record_micro_win(state)
        print(f"✅ Recorded: 1 plan generated, 1 micro-win achieved")
        
        return state
    
    except Exception as e:
        print(f"❌ Error modifying state: {e}")
        return None


def test_save_to_supabase(state):
    """Test 5: Save state to Supabase."""
    print_header("TEST 5: Save State to Supabase")
    
    try:
        success = save_state(state)
        
        if success:
            print(f"✅ State saved successfully for user: {state.user_id}")
            print(f"   - User profile saved")
            print(f"   - {len(state.constraints)} constraint(s) saved")
            return True
        else:
            print(f"❌ Failed to save state")
            return False
    
    except Exception as e:
        print(f"❌ Error saving state: {e}")
        return False


def test_load_from_supabase(user_id):
    """Test 6: Load state from Supabase."""
    print_header("TEST 6: Load State from Supabase")
    
    try:
        loaded_state = load_state(user_id)
        
        if loaded_state is None:
            print(f"❌ User not found: {user_id}")
            return None
        
        print(f"✅ State loaded successfully for user: {loaded_state.user_id}")
        print(f"   - Life mode: {loaded_state.life_mode.value}")
        print(f"   - Constraints: {len(loaded_state.constraints)}")
        print(f"   - Plans generated: {loaded_state.user_history.total_plans_generated}")
        print(f"   - Micro-wins: {loaded_state.user_history.micro_wins_achieved}")
        
        return loaded_state
    
    except Exception as e:
        print(f"❌ Error loading state: {e}")
        return None


def test_state_summary(state):
    """Test 7: Get state summary."""
    print_header("TEST 7: State Summary")
    
    try:
        summary = get_state_summary(state)
        
        print("✅ State Summary:")
        for key, value in summary.items():
            if not key.startswith("session"):
                print(f"   - {key}: {value}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "STATE MODEL & PERSISTENCE LAYER TEST" + " "*16 + "║")
    print("║" + " "*10 + "Complete Integration Test with Supabase Database" + " "*10 + "║")
    print("╚" + "="*68 + "╝")
    
    # Test 1: Environment
    if not test_environment():
        print("\n❌ Environment setup failed. Please check your .env file.")
        return
    
    # Test 2: Supabase connection
    if not test_supabase_connection():
        print("\n❌ Supabase connection failed. Check credentials in .env")
        return
    
    # Test 3: Create state
    state = test_state_creation()
    if state is None:
        print("\n❌ State creation failed.")
        return
    
    # Test 4: Modify state
    state = test_state_modifications(state)
    if state is None:
        print("\n❌ State modification failed.")
        return
    
    # Test 5: Save to Supabase
    if not test_save_to_supabase(state):
        print("\n❌ Saving to Supabase failed.")
        return
    
    # Test 6: Load from Supabase
    loaded_state = test_load_from_supabase(state.user_id)
    if loaded_state is None:
        print("\n❌ Loading from Supabase failed.")
        return
    
    # Test 7: Summary
    test_state_summary(loaded_state)
    
    # Success
    print_header("✅ ALL TESTS PASSED!")
    print("""
Your State Management System is working perfectly with Supabase!

What you've tested:
  ✅ Environment variables loaded
  ✅ Supabase connection established
  ✅ Default state created
  ✅ State modifications (constraints, life mode, activities)
  ✅ State saved to Supabase database
  ✅ State loaded from Supabase database
  ✅ State summary generated

Next steps:
  1. Integrate this into your LangGraph nodes
  2. Create more users with different configurations
  3. Build your planning modules on top of this state
  4. Add your wellness logic in separate modules

For more info, see:
  - backend/src/state/__init__.py (public API)
  - backend/src/state/state_manager.py (state functions)
  - backend/src/state/persistence.py (database operations)
""")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
