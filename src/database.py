"""
"""

import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
import sqlite3

def execute_query(query, args) -> list | None:
    """
    Execute a query on the database

    Args:
        query (str): The query to execute
        args (tuple): The arguments to pass to the query
    Returns:
        The result of the query | None if error
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, args)
            out = cursor.fetchall()
            return out
    except Exception as e:
        print(f"Error executing query: {e}")
        return None


def get_db_connection():
    """
    Returns a connection to the database.
    """
    return sqlite3.connect('users.db')


def initialize_db():
    """
    Initializes the database with the necessary tables.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                login_number INTEGER NOT NULL,
                salt TEXT NOT NULL,
                hashed_password TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                phone_number TEXT,
                user_id INTEGER NOT NULL,
                age INTEGER,
                gender TEXT,
                ethnicity TEXT,
                high_school TEXT,
                high_school_grad_year INTEGER,
                gpa REAL,
                sat_score INTEGER,
                act_score INTEGER,
                favorite_subjects TEXT,
                extracurriculars TEXT,
                career_aspirations TEXT,
                preferred_major TEXT,
                clifton_strengths TEXT,
                personality_test_results TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                intended_college TEXT,
                intended_major TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')

        # Create chat history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create chat summary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()


class ChromaDB:
    def __init__(self, path, distance_metric: str = "cosine"):
        """
        Initialize the ChromaDB client and collection.

        Args:
            path (str): The path to the ChromaDB data directory.
            distance_metric (str): The distance metric to use for the collection.
        """
        self.client = chromadb.PersistentClient(
            path=path,
            settings=Settings(),
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE,
        )

        self.collection = self.client.get_or_create_collection(name="documents", metadata={"hnsw:space": distance_metric})

    def add_document(self, content, doc_id: str, user_id=None):
        
        if user_id:
            metadata = {"access": "private", "user_id": user_id}
        else:
            metadata = {"access": "public"}
         
        # Add document to ChromaDB
        self.collection.add(
            ids=[doc_id],  # Unique identifier for the document
            documents=[content],  # Document content
            metadatas=[metadata],  # Access control metadata
        )
        print(f"Document added successfully with ID: {doc_id}")



