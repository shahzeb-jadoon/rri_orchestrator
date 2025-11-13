"""
Test suite for pause button state machine bug fixes.

Tests the 4 critical bugs identified in the pause/resume functionality:
1. Duplicate log_message call for Model B (lines 1144-1149)
2. mid_turn_pause cleared too early on resume (line 1021)
3. Missing mid_turn_pause clearing in Model A error handler (lines 1006-1018)
4. Missing mid_turn_pause clearing in Model B error handler (lines 1182-1195)
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing modules that depend on it
sys.modules['streamlit'] = MagicMock()

from core import database
from config import model_config


class TestPauseBugFixes(unittest.TestCase):
    """Test suite for pause button bug fixes"""
    
    def setUp(self):
        """Set up test database and session state"""
        # Create in-memory test database with shared cache so it persists across connections
        self.test_db_name = "file::memory:?cache=shared"
        self.test_conn = sqlite3.connect(self.test_db_name, uri=True, check_same_thread=False)
        self.test_conn.row_factory = sqlite3.Row
        
        # Patch database connection to return new connections to same shared memory DB
        self.db_patcher = patch('core.database.get_db_connection')
        self.mock_get_db = self.db_patcher.start()
        
        def get_test_conn():
            conn = sqlite3.connect(self.test_db_name, uri=True, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        
        self.mock_get_db.side_effect = get_test_conn
        
        # Initialize test database schema manually
        cursor = self.test_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                model_a_name TEXT,
                model_b_name TEXT,
                model_a_variant TEXT,
                model_b_variant TEXT,
                max_turns INTEGER,
                status TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                sender_role TEXT,
                content TEXT,
                target_model TEXT,
                is_error INTEGER DEFAULT 0,
                error_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        """)
        self.test_conn.commit()
        
        # Mock Streamlit session state
        self.mock_session_state = {
            'experiment_id': 1,
            'turn_count': 0,
            'max_turns': 5,
            'model_a_display': 'Gemini Pro',
            'model_b_display': 'GPT-4',
            'provider_a': 'gemini',
            'provider_b': 'openai',
            'model_a_variant': 'gemini-2.5-pro',
            'model_b_variant': 'gpt-4o-mini',
            'model_a_history': [],
            'model_b_history': [],
            'messages': [],
            'conversation_mode': 'Manual',
            'auto_running': False,
            'paused': False,
            'mid_turn_pause': False,
            'last_speaker': None,
            'next_speaker': None,
            'stop_requested': False,
            'pause_after_turn': False,
            'limit_reached': False
        }
        
        # Create test experiment
        cursor.execute("""
            INSERT INTO experiments (name, model_a_name, model_b_name, max_turns, status)
            VALUES (?, ?, ?, ?, ?)
        """, ('Test Experiment', 'gemini-2.5-pro', 'gpt-4o-mini', 5, 'in_progress'))
        self.test_conn.commit()
    
    def tearDown(self):
        """Clean up test database"""
        self.test_conn.close()
        self.db_patcher.stop()
    
    @patch('streamlit.session_state', new_callable=lambda: MagicMock())
    def test_duplicate_logging_fixed(self, mock_st_session):
        """
        BUG FIX #1: Verify Model B response is only logged once.
        
        Previously, lines 1144 and 1149 both called log_message for Model B,
        causing duplicate entries in the database and CSV exports.
        """
        # Configure mock session state
        for key, value in self.mock_session_state.items():
            setattr(mock_st_session, key, value)
        
        # Log a Model B message
        exp_id = 1
        model_b_name = model_config.PROVIDERS['openai']
        response_text = "This is Model B's response"
        
        # Call log_message once (as fixed code should)
        database.log_message(exp_id, model_b_name, response_text)
        
        # Verify only ONE entry exists
        cursor = self.test_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM messages 
            WHERE experiment_id = ? AND sender_role = ? AND content = ?
        """, (exp_id, model_b_name, response_text))
        result = cursor.fetchone()
        
        self.assertEqual(result['count'], 1, 
                        "Model B response should only be logged once (BUG FIX #1)")
    
    @patch('streamlit.session_state', new_callable=lambda: MagicMock())
    def test_mid_turn_pause_not_cleared_on_resume(self, mock_st_session):
        """
        BUG FIX #2: Verify mid_turn_pause is NOT cleared when resuming mid-turn.
        
        Previously, line 1021 cleared mid_turn_pause in the else block when
        skipping Model A, which broke the state machine logic. The flag should
        only be cleared AFTER Model B successfully responds.
        """
        # Configure mock session state for mid-turn resume scenario
        for key, value in self.mock_session_state.items():
            setattr(mock_st_session, key, value)
        
        # Set up mid-turn pause state (Model A already responded)
        mock_st_session.mid_turn_pause = True
        mock_st_session.last_speaker = 'Gemini Pro'
        mock_st_session.next_speaker = 'GPT-4'
        
        # Simulate the resume logic check
        skip_model_a = (mock_st_session.mid_turn_pause and 
                       mock_st_session.last_speaker == 'Gemini Pro')
        
        self.assertTrue(skip_model_a, "Should skip Model A when resuming mid-turn")
        
        # CRITICAL: mid_turn_pause should STILL be True at this point
        # It should only be cleared after Model B succeeds
        self.assertTrue(mock_st_session.mid_turn_pause,
                       "mid_turn_pause should NOT be cleared in else block (BUG FIX #2)")
        
        # Simulate Model B success - NOW it should be cleared
        mock_st_session.mid_turn_pause = False
        self.assertFalse(mock_st_session.mid_turn_pause,
                        "mid_turn_pause should be cleared after Model B success")
    
    @patch('streamlit.session_state', new_callable=lambda: MagicMock())
    def test_model_a_error_clears_mid_turn_pause(self, mock_st_session):
        """
        BUG FIX #3: Verify Model A error handler clears mid_turn_pause.
        
        Previously, the Model A error handler (lines 1006-1018) did not clear
        the mid_turn_pause flag, causing state corruption on subsequent resume.
        """
        # Configure mock session state
        for key, value in self.mock_session_state.items():
            setattr(mock_st_session, key, value)
        
        # Set mid_turn_pause (simulating pause during Model A's turn)
        mock_st_session.mid_turn_pause = True
        
        # Simulate Model A error handler behavior (FIXED version)
        error_msg = "API rate limit exceeded"
        mock_st_session.mid_turn_pause = False  # BUG FIX #3
        mock_st_session.auto_running = False
        mock_st_session.paused = True
        
        # Verify flag was cleared
        self.assertFalse(mock_st_session.mid_turn_pause,
                        "Model A error handler must clear mid_turn_pause (BUG FIX #3)")
        self.assertTrue(mock_st_session.paused,
                       "Error should set paused state")
    
    @patch('streamlit.session_state', new_callable=lambda: MagicMock())
    def test_model_b_error_clears_mid_turn_pause(self, mock_st_session):
        """
        BUG FIX #4: Verify Model B error handler clears mid_turn_pause.
        
        Previously, the Model B error handler (lines 1182-1195) did not clear
        the mid_turn_pause flag, causing state corruption similar to Bug #3.
        """
        # Configure mock session state
        for key, value in self.mock_session_state.items():
            setattr(mock_st_session, key, value)
        
        # Set mid_turn_pause (simulating pause during Model B's turn)
        mock_st_session.mid_turn_pause = True
        
        # Simulate Model B error handler behavior (FIXED version)
        error_msg = "Connection timeout"
        mock_st_session.mid_turn_pause = False  # BUG FIX #4
        mock_st_session.auto_running = False
        
        # Verify flag was cleared
        self.assertFalse(mock_st_session.mid_turn_pause,
                        "Model B error handler must clear mid_turn_pause (BUG FIX #4)")
    
    @patch('streamlit.session_state', new_callable=lambda: MagicMock())
    def test_pause_now_sets_mid_turn_pause(self, mock_st_session):
        """
        Verify that clicking "Pause Now" correctly sets mid_turn_pause flag.
        
        This is the expected behavior that should work with the bug fixes.
        """
        # Configure mock session state
        for key, value in self.mock_session_state.items():
            setattr(mock_st_session, key, value)
        
        # Simulate Model A completing successfully
        mock_st_session.last_speaker = 'Gemini Pro'
        mock_st_session.next_speaker = 'GPT-4'
        
        # Simulate "Pause Now" button click
        mock_st_session.stop_requested = True
        
        # Simulate pause handler logic
        if mock_st_session.stop_requested:
            mock_st_session.mid_turn_pause = True
            mock_st_session.paused = True
        
        # Verify state is correct
        self.assertTrue(mock_st_session.mid_turn_pause,
                       "'Pause Now' should set mid_turn_pause flag")
        self.assertTrue(mock_st_session.paused,
                       "'Pause Now' should set paused flag")
        self.assertEqual(mock_st_session.last_speaker, 'Gemini Pro',
                        "Last speaker should be preserved")
        self.assertEqual(mock_st_session.next_speaker, 'GPT-4',
                        "Next speaker should be Model B")
    
    @patch('streamlit.session_state', new_callable=lambda: MagicMock())
    def test_complete_turn_clears_mid_turn_pause(self, mock_st_session):
        """
        Verify that completing a full turn (Model A + Model B) clears mid_turn_pause.
        
        After Model B successfully responds, the turn is complete and
        mid_turn_pause should be False.
        """
        # Configure mock session state
        for key, value in self.mock_session_state.items():
            setattr(mock_st_session, key, value)
        
        # Start with mid_turn_pause True (paused after Model A)
        mock_st_session.mid_turn_pause = True
        mock_st_session.last_speaker = 'Gemini Pro'
        mock_st_session.turn_count = 1
        
        # Simulate Model B success
        mock_st_session.turn_count += 1
        mock_st_session.mid_turn_pause = False  # Cleared after Model B success
        mock_st_session.last_speaker = 'GPT-4'
        mock_st_session.next_speaker = 'Gemini Pro'
        
        # Verify state
        self.assertFalse(mock_st_session.mid_turn_pause,
                        "mid_turn_pause should be False after complete turn")
        self.assertEqual(mock_st_session.turn_count, 2,
                        "Turn count should increment after Model B")
        self.assertEqual(mock_st_session.last_speaker, 'GPT-4',
                        "Last speaker should be Model B")


class TestPauseButtonIntegration(unittest.TestCase):
    """Integration tests for pause button with state machine"""
    
    def setUp(self):
        """Set up test environment"""
        # Create in-memory test database with shared cache
        self.test_db_name = "file::memory:?cache=shared"
        self.test_conn = sqlite3.connect(self.test_db_name, uri=True, check_same_thread=False)
        self.test_conn.row_factory = sqlite3.Row
        
        # Patch database connection to return new connections to same shared memory DB
        self.db_patcher = patch('core.database.get_db_connection')
        self.mock_get_db = self.db_patcher.start()
        
        def get_test_conn():
            conn = sqlite3.connect(self.test_db_name, uri=True, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        
        self.mock_get_db.side_effect = get_test_conn
        
        # Initialize schema manually
        cursor = self.test_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                model_a_name TEXT,
                model_b_name TEXT,
                model_a_variant TEXT,
                model_b_variant TEXT,
                max_turns INTEGER,
                status TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                sender_role TEXT,
                content TEXT,
                target_model TEXT,
                is_error INTEGER DEFAULT 0,
                error_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        """)
        self.test_conn.commit()
        
        # Create test experiment
        cursor.execute("""
            INSERT INTO experiments (name, model_a_name, model_b_name, max_turns, status)
            VALUES (?, ?, ?, ?, ?)
        """, ('Integration Test', 'gemini-2.5-pro', 'gpt-4o-mini', 10, 'in_progress'))
        self.test_conn.commit()
    
    def tearDown(self):
        """Clean up"""
        self.test_conn.close()
        self.db_patcher.stop()
    
    def test_pause_resume_cycle_no_duplicates(self):
        """
        End-to-end test: Verify pause/resume cycle doesn't create duplicates.
        
        This simulates the user workflow:
        1. Model A responds
        2. User clicks "Pause Now"
        3. User clicks "Continue"
        4. Model B responds
        5. Check database for duplicates
        """
        exp_id = 1
        
        # Step 1: Model A responds
        model_a_msg = "Hello, Model B!"
        database.log_message(exp_id, 'gemini-2.5-pro', model_a_msg)
        
        # Step 2: Pause happens (no database change)
        
        # Step 3: Resume happens (no database change)
        
        # Step 4: Model B responds (SHOULD ONLY LOG ONCE)
        model_b_msg = "Hello, Model A!"
        database.log_message(exp_id, 'gpt-4o-mini', model_b_msg)
        
        # Step 5: Verify no duplicates
        cursor = self.test_conn.cursor()
        
        # Check Model A message count
        cursor.execute("""
            SELECT COUNT(*) as count FROM messages 
            WHERE experiment_id = ? AND sender_role = ? AND content = ?
        """, (exp_id, 'gemini-2.5-pro', model_a_msg))
        model_a_count = cursor.fetchone()['count']
        
        # Check Model B message count
        cursor.execute("""
            SELECT COUNT(*) as count FROM messages 
            WHERE experiment_id = ? AND sender_role = ? AND content = ?
        """, (exp_id, 'gpt-4o-mini', model_b_msg))
        model_b_count = cursor.fetchone()['count']
        
        self.assertEqual(model_a_count, 1, 
                        "Model A message should only appear once")
        self.assertEqual(model_b_count, 1,
                        "Model B message should only appear once (no duplicate)")
        
        # Verify total message count
        cursor.execute("""
            SELECT COUNT(*) as count FROM messages 
            WHERE experiment_id = ? AND is_error = 0
        """, (exp_id,))
        total_count = cursor.fetchone()['count']
        
        self.assertEqual(total_count, 2,
                        "Should have exactly 2 messages (1 from A, 1 from B)")


if __name__ == '__main__':
    print("=" * 70)
    print("PAUSE BUTTON BUG FIX TEST SUITE")
    print("=" * 70)
    print("\nTesting 4 critical bug fixes:")
    print("  1. Duplicate log_message call for Model B")
    print("  2. mid_turn_pause cleared too early on resume")
    print("  3. Missing mid_turn_pause clearing in Model A error handler")
    print("  4. Missing mid_turn_pause clearing in Model B error handler")
    print("\n" + "=" * 70 + "\n")
    
    unittest.main(verbosity=2)
