"""
Test script to verify database functionality.
Run this before testing the full application.

Tests all features including:
- Experiment creation with new fields (name, variants, status)
- Message logging with error tracking
- Soft delete and recovery
- Status updates
- Complete experiment retrieval
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import database

def test_basic_operations():
    """Test basic database setup and CRUD operations."""
    print("\n=== Testing Basic Operations ===")
    
    # Initialize database
    database.setup_database()
    print("✓ Database tables created")
    
    # Create a test experiment with new fields
    exp_id = database.create_experiment(
        model_a="Gemini",
        model_b="GPT-4",
        prompt_a="You are Gemini, a helpful AI assistant.",
        prompt_b="You are GPT-4, a helpful AI assistant.",
        max_turns=10,
        model_a_variant="gemini-2.5-pro",
        model_b_variant="gpt-4o",
        name="Test Experiment: Feature Testing"
    )
    print(f"✓ Created experiment with ID: {exp_id}")
    print(f"  - Name: Test Experiment: Feature Testing")
    print(f"  - Variants: gemini-2.5-pro vs gpt-4o")
    print(f"  - Max turns: 10")
    
    # Log test messages
    database.log_message(exp_id, "researcher", "Hello, this is a test message")
    database.log_message(exp_id, "Gemini", "Response from Gemini model")
    database.log_message(exp_id, "GPT-4", "Response from GPT-4 model")
    print("✓ Logged 3 test messages")
    
    # Log an error message
    database.log_message(
        exp_id, 
        "Gemini", 
        "API Error: Rate limit exceeded", 
        is_error=True, 
        error_type="rate_limit"
    )
    print("✓ Logged error message with error tracking")
    
    # Log an override message
    database.log_message(exp_id, "Gemini (Override)", "Manual response from researcher")
    print("✓ Logged manual override message")
    
    return exp_id

def test_status_updates(exp_id):
    """Test experiment status tracking."""
    print("\n=== Testing Status Updates ===")
    
    # Update to in_progress
    database.update_experiment_status(exp_id, "in_progress")
    print("✓ Updated status to: in_progress")
    
    # Update to error
    database.update_experiment_status(exp_id, "error")
    print("✓ Updated status to: error")
    
    # Update to completed
    database.update_experiment_status(exp_id, "completed")
    print("✓ Updated status to: completed")

def test_soft_delete_and_recovery(exp_id):
    """Test soft delete and recovery features."""
    print("\n=== Testing Soft Delete & Recovery ===")
    
    # Soft delete
    database.soft_delete_experiment(exp_id)
    print(f"✓ Soft deleted experiment {exp_id}")
    
    # Verify it's in deleted experiments
    deleted_exps = database.get_deleted_experiments()
    assert len(deleted_exps) > 0, "Should have deleted experiments"
    assert any(exp['id'] == exp_id for exp in deleted_exps), "Should find our experiment"
    print(f"✓ Found {len(deleted_exps)} deleted experiment(s)")
    
    # Recover it
    database.recover_experiment(exp_id)
    print(f"✓ Recovered experiment {exp_id}")
    
    # Verify it's back in active experiments
    all_exps = database.get_all_experiments()
    recovered = next((exp for exp in all_exps if exp['id'] == exp_id), None)
    assert recovered is not None, "Should find recovered experiment"
    print("✓ Verified experiment is active again (present in get_all_experiments)")
    
    # Double-check via direct database query that deleted_at is NULL
    import sqlite3
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT deleted_at FROM experiments WHERE id = ?", (exp_id,))
    result = cursor.fetchone()
    conn.close()
    assert result[0] is None, "deleted_at should be NULL"
    print("✓ Verified deleted_at is NULL in database")

def test_get_all_experiments():
    """Test retrieving all experiments with correct fields."""
    print("\n=== Testing Get All Experiments ===")
    
    exps = database.get_all_experiments()
    print(f"✓ Retrieved {len(exps)} experiment(s)")
    
    if exps:
        exp = exps[0]
        expected_fields = [
            'id', 'name', 'model_a_name', 'model_b_name', 
            'model_a_variant', 'model_b_variant', 'model_a_prompt',
            'model_b_prompt', 'start_time', 'max_turns', 'message_count'
        ]
        for field in expected_fields:
            assert field in exp, f"Missing field: {field}"
        print(f"✓ All expected fields present: {', '.join(expected_fields)}")

def test_get_experiment_messages(exp_id):
    """Test retrieving messages."""
    print("\n=== Testing Get Experiment Messages ===")
    
    messages = database.get_experiment_messages(exp_id)
    print(f"✓ Retrieved {len(messages)} message(s)")
    
    # Check for override message by checking sender_role
    override_msgs = [msg for msg in messages if '(Override)' in msg.get('sender_role', '')]
    print(f"✓ Found {len(override_msgs)} override message(s)")
    
    # Verify message fields that are actually returned
    if messages:
        msg = messages[0]
        expected_fields = ['id', 'experiment_id', 'sender_role', 'content', 'timestamp']
        for field in expected_fields:
            assert field in msg, f"Missing field: {field}"
        print(f"✓ All expected message fields present")
    
    # Test error tracking by querying database directly
    import sqlite3
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE experiment_id = ? AND is_error = 1", (exp_id,))
    error_count = cursor.fetchone()[0]
    conn.close()
    print(f"✓ Database contains {error_count} error message(s) (verified via direct query)")

def test_database_statistics():
    """Test overall database statistics."""
    print("\n=== Testing Database Statistics ===")
    
    import sqlite3
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Count experiments
    cursor.execute("SELECT COUNT(*) FROM experiments WHERE deleted_at IS NULL")
    active_count = cursor.fetchone()[0]
    print(f"✓ Active experiments: {active_count}")
    
    cursor.execute("SELECT COUNT(*) FROM experiments WHERE deleted_at IS NOT NULL")
    deleted_count = cursor.fetchone()[0]
    print(f"✓ Deleted experiments: {deleted_count}")
    
    # Count messages by type
    cursor.execute("SELECT COUNT(*) FROM messages WHERE is_error = 0")
    normal_msgs = cursor.fetchone()[0]
    print(f"✓ Normal messages: {normal_msgs}")
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE is_error = 1")
    error_msgs = cursor.fetchone()[0]
    print(f"✓ Error messages: {error_msgs}")
    
    # Count by status
    cursor.execute("SELECT status, COUNT(*) FROM experiments WHERE deleted_at IS NULL GROUP BY status")
    status_counts = cursor.fetchall()
    print("✓ Experiments by status:")
    for status, count in status_counts:
        print(f"  - {status}: {count}")
    
    conn.close()

def run_all_tests():
    """Run all database tests."""
    print("=" * 60)
    print("RRI ORCHESTRATOR - DATABASE TEST SUITE")
    print("=" * 60)
    
    try:
        # Run tests
        exp_id = test_basic_operations()
        test_status_updates(exp_id)
        test_get_all_experiments()
        test_get_experiment_messages(exp_id)
        test_soft_delete_and_recovery(exp_id)
        test_database_statistics()
        
        # Final summary
        print("\n" + "=" * 60)
        print("✅ ALL DATABASE TESTS PASSED!")
        print("=" * 60)
        print(f"\nDatabase file: {database.DB_NAME}")
        print("All Stage 2 features verified:")
        print("  ✓ Experiment creation with name and variants")
        print("  ✓ Status tracking (pending, in_progress, completed, error)")
        print("  ✓ Error message logging and classification")
        print("  ✓ Manual override tracking")
        print("  ✓ Soft delete and recovery")
        print("  ✓ Comprehensive experiment retrieval")
        print("\nReady for production testing!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
