import sqlite3
import datetime

DB_NAME = "rri_lab.db"

def get_db_connection():
    """
    Create a connection to the SQLite database.
    Uses row_factory to return rows as dict-like objects instead of tuples.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """
    Initialize the database schema if it doesn't exist.
    
    Two main tables:
    - experiments: Stores metadata about each conversation session
    - messages: Stores every message exchanged in all experiments
    
    This structure allows easy querying of individual experiments
    and reconstruction of full conversation histories.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Store experiment configuration and metadata
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        start_time TEXT NOT NULL,
        model_a_name TEXT NOT NULL,
        model_b_name TEXT NOT NULL,
        model_a_prompt TEXT,
        model_b_prompt TEXT,
        max_turns INTEGER,
        deleted_at TEXT,
        model_a_variant TEXT,
        model_b_variant TEXT,
        status TEXT DEFAULT 'completed'
    );
    """)
    
    # Migrate existing tables to add new columns if they don't exist
    try:
        cursor.execute("ALTER TABLE experiments ADD COLUMN name TEXT")
    except:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE experiments ADD COLUMN deleted_at TEXT")
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE experiments ADD COLUMN model_a_variant TEXT")
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE experiments ADD COLUMN model_b_variant TEXT")
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE experiments ADD COLUMN status TEXT DEFAULT 'completed'")
    except:
        pass
    
    # Store all messages from all experiments
    # experiment_id links back to the experiments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        content TEXT NOT NULL,
        is_error INTEGER DEFAULT 0,
        error_type TEXT,
        FOREIGN KEY (experiment_id) REFERENCES experiments (id)
    );
    """)
    
    # Add new columns to messages table if they don't exist
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN is_error INTEGER DEFAULT 0")
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN error_type TEXT")
    except:
        pass
    
    conn.commit()
    conn.close()

def create_experiment(model_a, model_b, prompt_a, prompt_b, max_turns, model_a_variant=None, model_b_variant=None, name=None) -> int:
    """
    Logs a new experiment in the database and returns the new experiment's ID.
    
    Args:
        model_a: Provider name (e.g., "Google Gemini")
        model_b: Provider name (e.g., "OpenAI")
        prompt_a: System prompt for Model A
        prompt_b: System prompt for Model B
        max_turns: Maximum conversation turns
        model_a_variant: Specific model variant (e.g., "gemini-2.0-flash")
        model_b_variant: Specific model variant (e.g., "gpt-4-turbo")
        name: Custom name for the experiment
    
    Returns:
        New experiment ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    start_time = datetime.datetime.now().isoformat()
    
    # Auto-generate name if not provided
    if not name:
        name = f"{model_a} vs {model_b} - {start_time[:16]}"
    
    cursor.execute(
        """
        INSERT INTO experiments (name, start_time, model_a_name, model_b_name, model_a_prompt, model_b_prompt, max_turns, model_a_variant, model_b_variant)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, start_time, model_a, model_b, prompt_a, prompt_b, max_turns, model_a_variant, model_b_variant)
    )
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def log_message(experiment_id: int, sender: str, content: str, is_error: bool = False, error_type: str = None):
    """
    Log a single message to the database.
    
    Args:
        experiment_id: ID of the experiment this message belongs to
        sender: Role of the sender ("researcher", model name, etc.)
        content: The actual message text
        is_error: Whether this message represents an error
        error_type: Type of error (e.g., "rate_limit", "api_error", "network_error")
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.datetime.now().isoformat()
    
    cursor.execute(
        """
        INSERT INTO messages (experiment_id, timestamp, sender_role, content, is_error, error_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (experiment_id, timestamp, sender, content, 1 if is_error else 0, error_type)
    )
    
    conn.commit()
    conn.close()

def update_experiment_status(experiment_id: int, status: str):
    """
    Update the status of an experiment.
    
    Args:
        experiment_id: ID of the experiment
        status: New status ('completed', 'error', 'stopped', 'in_progress')
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE experiments SET status = ? WHERE id = ?",
        (status, experiment_id)
    )
    
    conn.commit()
    conn.close()

def get_all_experiments():
    """
    Retrieve all non-deleted experiments with basic metadata.
    
    Returns:
        List of dicts containing experiment info
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            e.id,
            e.name,
            e.start_time,
            e.model_a_name,
            e.model_b_name,
            e.model_a_prompt,
            e.model_b_prompt,
            e.max_turns,
            e.model_a_variant,
            e.model_b_variant,
            COUNT(m.id) as message_count
        FROM experiments e
        LEFT JOIN messages m ON e.id = m.experiment_id
        WHERE e.deleted_at IS NULL
        GROUP BY e.id
        ORDER BY e.start_time DESC
    """)
    
    experiments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return experiments

def get_experiment_messages(experiment_id: int):
    """
    Retrieve all messages for a specific experiment.
    
    Args:
        experiment_id: The ID of the experiment
        
    Returns:
        List of dicts containing message info
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            id,
            experiment_id,
            timestamp,
            sender_role,
            content
        FROM messages
        WHERE experiment_id = ?
        ORDER BY timestamp ASC
    """, (experiment_id,))
    
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def get_experiment_by_id(experiment_id: int):
    """
    Retrieve a specific experiment's details.
    
    Args:
        experiment_id: The ID of the experiment
        
    Returns:
        Dict containing experiment info or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            id,
            name,
            start_time,
            model_a_name,
            model_b_name,
            model_a_prompt,
            model_b_prompt,
            max_turns,
            model_a_variant,
            model_b_variant,
            deleted_at
        FROM experiments
        WHERE id = ?
    """, (experiment_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def rename_experiment(experiment_id: int, new_name: str):
    """
    Rename an experiment.
    
    Args:
        experiment_id: The ID of the experiment to rename
        new_name: The new name for the experiment
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE experiments
        SET name = ?
        WHERE id = ?
    """, (new_name, experiment_id))
    
    conn.commit()
    conn.close()

def soft_delete_experiment(experiment_id: int):
    """
    Soft delete an experiment by setting deleted_at timestamp.
    Experiment can be recovered within 30 days.
    
    Args:
        experiment_id: The ID of the experiment to delete
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    deleted_time = datetime.datetime.now().isoformat()
    
    cursor.execute("""
        UPDATE experiments
        SET deleted_at = ?
        WHERE id = ?
    """, (deleted_time, experiment_id))
    
    conn.commit()
    conn.close()

def recover_experiment(experiment_id: int):
    """
    Recover a soft-deleted experiment.
    
    Args:
        experiment_id: The ID of the experiment to recover
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE experiments
        SET deleted_at = NULL
        WHERE id = ?
    """, (experiment_id,))
    
    conn.commit()
    conn.close()

def get_deleted_experiments():
    """
    Get all soft-deleted experiments that are still recoverable (< 30 days).
    
    Returns:
        List of dicts containing deleted experiment info
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate 30 days ago
    thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
    
    cursor.execute("""
        SELECT 
            e.id,
            e.name,
            e.start_time,
            e.deleted_at,
            e.model_a_name,
            e.model_b_name,
            e.model_a_variant,
            e.model_b_variant,
            e.max_turns,
            COUNT(m.id) as message_count
        FROM experiments e
        LEFT JOIN messages m ON e.id = m.experiment_id
        WHERE e.deleted_at IS NOT NULL
        AND e.deleted_at > ?
        GROUP BY e.id
        ORDER BY e.deleted_at DESC
    """, (thirty_days_ago,))
    
    experiments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return experiments

def permanently_delete_old_experiments():
    """
    Permanently delete experiments that have been soft-deleted for more than 30 days.
    This should be run periodically (e.g., daily cron job).
    
    Returns:
        Number of experiments permanently deleted
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate 30 days ago
    thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
    
    # Get IDs of experiments to delete
    cursor.execute("""
        SELECT id FROM experiments
        WHERE deleted_at IS NOT NULL
        AND deleted_at <= ?
    """, (thirty_days_ago,))
    
    exp_ids = [row['id'] for row in cursor.fetchall()]
    
    if exp_ids:
        # Delete messages first (foreign key constraint)
        placeholders = ','.join('?' * len(exp_ids))
        cursor.execute(f"""
            DELETE FROM messages
            WHERE experiment_id IN ({placeholders})
        """, exp_ids)
        
        # Delete experiments
        cursor.execute(f"""
            DELETE FROM experiments
            WHERE id IN ({placeholders})
        """, exp_ids)
    
    conn.commit()
    conn.close()
    
    return len(exp_ids)
