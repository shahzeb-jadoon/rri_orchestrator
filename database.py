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
        start_time TEXT NOT NULL,
        model_a_name TEXT NOT NULL,
        model_b_name TEXT NOT NULL,
        model_a_prompt TEXT,
        model_b_prompt TEXT,
        max_turns INTEGER
    );
    """)
    
    # Store all messages from all experiments
    # experiment_id links back to the experiments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY (experiment_id) REFERENCES experiments (id)
    );
    """)
    
    conn.commit()
    conn.close()

def create_experiment(model_a, model_b, prompt_a, prompt_b, max_turns) -> int:
    """
    Logs a new experiment in the database and returns the new experiment's ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    start_time = datetime.datetime.now().isoformat()
    
    cursor.execute(
        """
        INSERT INTO experiments (start_time, model_a_name, model_b_name, model_a_prompt, model_b_prompt, max_turns)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (start_time, model_a, model_b, prompt_a, prompt_b, max_turns)
    )
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def log_message(experiment_id: int, sender: str, content: str):
    """
    Log a single message to the database.
    
    Args:
        experiment_id: ID of the experiment this message belongs to
        sender: Role of the sender ("researcher", model name, etc.)
        content: The actual message text
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.datetime.now().isoformat()
    
    cursor.execute(
        """
        INSERT INTO messages (experiment_id, timestamp, sender_role, content)
        VALUES (?, ?, ?, ?)
        """,
        (experiment_id, timestamp, sender, content)
    )
    
    conn.commit()
    conn.close()
