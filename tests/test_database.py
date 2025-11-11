"""
Test script to verify database functionality.
Run this before testing the full application.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import database

print("Testing database setup...")

# Initialize database
database.setup_database()
print("✓ Database tables created")

# Create a test experiment
exp_id = database.create_experiment(
    "Test Model A",
    "Test Model B",
    "You are model A",
    "You are model B"
)
print(f"✓ Created experiment with ID: {exp_id}")

# Log some test messages
database.log_message(exp_id, "researcher", "Hello, this is a test message")
database.log_message(exp_id, "Test Model A", "Response from model A")
database.log_message(exp_id, "Test Model B", "Response from model B")
print("✓ Logged 3 test messages")

# Verify data was written
import sqlite3
conn = sqlite3.connect(database.DB_NAME)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM experiments")
exp_count = cursor.fetchone()[0]
print(f"✓ Total experiments in database: {exp_count}")

cursor.execute("SELECT COUNT(*) FROM messages WHERE experiment_id = ?", (exp_id,))
msg_count = cursor.fetchone()[0]
print(f"✓ Total messages for experiment {exp_id}: {msg_count}")

conn.close()

print("\n✅ All database tests passed!")
print(f"Database file created: {database.DB_NAME}")
