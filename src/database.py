"""
File describing the database with additional functions for interacting with the database.
"""

import sqlite3
import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings

import src.assessment as assessment


def execute_query(query, args=None) -> list | None:
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
            if args is not None:
                cursor.execute(query, args)
            else:
                cursor.execute(query)
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


def get_top_strengths(user):
    """
    Get the top 5 strengths for the user.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Fetch Strengths data
        cursor.execute('''
            SELECT themes.theme_name, theme_results.total_score, theme_results.strength_level
            FROM theme_results
            JOIN themes ON theme_results.theme_id = themes.theme_id
            WHERE theme_results.user_id = ?
            ORDER BY theme_results.total_score DESC
            LIMIT 5
        ''', (user.user_id,))
        return cursor.fetchall()


def get_bot_strengths(user):
    """
    Get the bottom 5 strengths for the user.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT themes.theme_name, theme_results.total_score, theme_results.strength_level
            FROM theme_results
            JOIN themes ON theme_results.theme_id = themes.theme_id
            WHERE theme_results.user_id = ?
            ORDER BY theme_results.total_score ASC
            LIMIT 5
        ''', (user.user_id,))
        return cursor.fetchall()


def insert_user_responses(user_id, responses):
    """
    Insert the user responses into the user_responses table.

    Args:
        user_id (int): The ID of the user.
        responses (dict): The user responses.
    Returns:
        None
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Insert user responses into the user_responses table
        for statement, score in responses.items():
            cursor.execute("SELECT question_id FROM questions WHERE statement=?", (statement,))
            question_id = cursor.fetchone()[0]
            
            cursor.execute(
                "INSERT INTO user_responses (user_id, question_id, response) VALUES (?, ?, ?)", 
                (user_id, question_id, score)
            )

        conn.commit()


def insert_strengths(user_id, strengths):
    """
    Insert the Strengths scores into the theme_results table.

    Args:
        user_id (int): The ID of the user.
        strengths (dict): The Strengths scores.
    Returns:
        None
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Insert Strengths scores into the theme_results table
        for theme, score in strengths.items():
            cursor.execute("SELECT theme_id FROM themes WHERE theme_name=?", (theme,))
            theme_id = cursor.fetchone()[0]
            
            # Determine strength level based on the score
            if score >= 13:
                strength_level = 'Strong strength'
            elif score >= 10:
                strength_level = 'Moderate strength'
            elif score >= 7:
                strength_level = 'Developing strength'
            else:
                strength_level = 'Potential for growth'

            print(f"User ID: {user_id}, Theme ID: {theme_id}, Score: {score}, Strength Level: {strength_level}")
            cursor.execute(
                "INSERT INTO theme_results (user_id, theme_id, total_score, strength_level) VALUES (?, ?, ?, ?)", 
                (user_id, theme_id, score, strength_level)
            )

        conn.commit()


def create_user_tables():
    """
    Creates the tables for the users.
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
                strengths TEXT,
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
        conn.commit()


def create_chat_tables():
    """
    Creates the tables for the chat.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

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


def create_assessment_tables():
    """
    Creates the tables for the assessment.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Table to store the four key domains
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS domains (
                domain_id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain_name TEXT NOT NULL
            );
        ''')

        # Table to store the 34 Strengths themes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS themes (
                theme_id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain_id INTEGER NOT NULL,
                theme_name TEXT NOT NULL,
                FOREIGN KEY (domain_id) REFERENCES domains(domain_id)
            );
        ''')

        # Table to store questions/statements for each theme
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme_id INTEGER NOT NULL,
                statement TEXT NOT NULL,
                FOREIGN KEY (theme_id) REFERENCES themes(theme_id)
            );
        ''')

        # Table to store user responses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                response INTEGER CHECK(response BETWEEN 1 AND 5),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (question_id) REFERENCES questions(question_id)
            );
        ''')

        # Table to store results per theme
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS theme_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                theme_id INTEGER NOT NULL,
                total_score INTEGER CHECK(total_score BETWEEN 3 AND 15),
                strength_level TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (theme_id) REFERENCES themes(theme_id)
            );
        ''')
        conn.commit()


def initialize_db():
    """
    Initializes the database with the necessary tables and data.
    """
    create_user_tables()
    create_chat_tables()
    create_assessment_tables()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if domains table is empty
        cursor.execute("SELECT COUNT(*) FROM domains")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO domains (domain_name) VALUES (?)", assessment.domains)
            cursor.executemany("INSERT INTO themes (domain_id, theme_name) VALUES (?, ?)", assessment.themes)
            cursor.executemany("INSERT INTO questions (theme_id, statement) VALUES (?, ?)", assessment.questions)
            print("Assessment data initialized successfully.")
        else:
            print("Assessment data already exists. Skipping initialization.")


class ChromaDB:
    def __init__(self, path: str, name: str, distance_metric: str = "cosine"):
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

        self.collection = self.client.get_or_create_collection(name=name, metadata={"hnsw:space": distance_metric})

    def add_document(self, content, doc_id: str, metadata: dict = None, user_id=None, verbose=False):
        
        if metadata is None:
            metadata = {}

        if user_id:
            metadata["access"] = "private"
            metadata["user_id"] = user_id
        else:
            metadata["access"] = "public"
         
        # Add document to ChromaDB
        self.collection.add(
            ids=[doc_id],  # Unique identifier for the document
            documents=[content],  # Document content
            metadatas=[metadata],  # Access control metadata
        )
        if verbose:
            print(f"Document added successfully with ID: {doc_id}")

