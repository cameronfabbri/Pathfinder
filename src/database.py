"""
File describing the database with additional functions for interacting with the database.
"""

import sqlite3
import chromadb

from typing import Any, Dict, List
from contextlib import contextmanager
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings

import logging
from functools import lru_cache

import src.assessment as assessment

#@contextmanager
def get_db_connection() -> sqlite3.Connection:
    """
    Returns a connection to the database.
    """
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn
    #yield conn
    #conn.close()


@lru_cache(maxsize=None)
def get_db_connection() -> sqlite3.Connection:
    """
    Returns a connection to the database.
    """
    conn = sqlite3.connect('users.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
    #yield conn
    #conn.close()


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
        conn = get_db_connection()
        cursor = conn.cursor()
        if args:
            cursor.execute(query, args)
        else:
            cursor.execute(query)
        result = cursor.fetchall()
        conn.commit()
        return result
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        return None


def get_top_strengths(user_id):
    """
    Get the top 5 strengths for the user.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
        
    # Fetch Strengths data
    cursor.execute('''
        SELECT themes.theme_name, theme_results.total_score, theme_results.strength_level
        FROM theme_results
        JOIN themes ON theme_results.theme_id = themes.theme_id
        WHERE theme_results.user_id = ?
        ORDER BY theme_results.total_score DESC
        LIMIT 5
    ''', (user_id,))
    return cursor.fetchall()


def get_bot_strengths(user_id):
    """
    Get the bottom 5 strengths for the user.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT themes.theme_name, theme_results.total_score, theme_results.strength_level
        FROM theme_results
        JOIN themes ON theme_results.theme_id = themes.theme_id
        WHERE theme_results.user_id = ?
        ORDER BY theme_results.total_score ASC
        LIMIT 5
    ''', (user_id,))
    return cursor.fetchall()


def insert_user_responses(user_id, responses):
    """
    Insert the responses to the assessment test into the user_responses table.
    
    Args:
        user_id (int): The ID of the user.
        responses (dict): The user responses.
    Returns:
        None
    """
    conn = get_db_connection()
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
    conn = get_db_connection()
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
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            session_id INTEGER NOT NULL,
            hashed_password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            user_id INTEGER NOT NULL,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone_number TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
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
            other_majors TEXT,
            top_school TEXT,
            safety_school TEXT,
            other_schools TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    ''')
    conn.commit()


def create_chat_tables():
    """
    Creates tables for chat history, counselor-SUNY interactions, and chat summaries.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table to store user-counselor-suny interactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            sender TEXT NOT NULL, -- user, counselor, or suny_agent
            recipient TEXT NOT NULL, -- user, counselor, or suny_agent
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Chat summaries for user-counselor conversation
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
    conn = get_db_connection()
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

    # TODO - remove after testing
    from src.auth import hash_password
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("test",))
    if cursor.fetchone()[0] == 0:
        hashed_password = hash_password("test")

        cursor.execute(
            "INSERT INTO users (username, session_id, hashed_password) VALUES (?, ?, ?)", 
            ("test", -1, hashed_password)
        )
        user_vars = '(user_id, first_name, last_name, age, gender, ethnicity, high_school, high_school_grad_year, address, city, state, zip_code)'
        user_vals = (1, 'Cameron', 'Fabbri', 16, 'Male', 'None', 'Northport High School', 2024, '123 Main St', 'Northport', 'New York', 11768)
        cursor.execute(f"INSERT INTO students {user_vars} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", user_vals)
        conn.commit()
    # End of TODO

    conn = get_db_connection()
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

        self.collection = self.client.get_or_create_collection(
            name=name, metadata={"hnsw:space": distance_metric}
        )

    @staticmethod
    def sanitize_metadata(metadata: dict) -> dict:
        def sanitize_value(value: Any) -> str:
            if isinstance(value, (str, int, float, bool)):
                return value
            elif value is None:
                return ''
            else:
                return str(value)

        return {key: sanitize_value(value) for key, value in metadata.items()}

    def insert_if_not_exists(self, content: str, doc_id: str, metadata: Dict[Any, Any]) -> bool:
        """
        Insert a document into the collection if it does not already exist.

        Args:
            content (str): The content of the document.
            doc_id (str): The ID of the document.
            metadata (dict): The metadata of the document.
        Returns:
            bool: True if the document was added, False otherwise.
        """
        if not self.document_exists(doc_id):
            sanitized_metadata = self.sanitize_metadata(metadata)
            self.add_document(content=content, doc_id=doc_id, metadata=sanitized_metadata)
            return True
        else:
            print(f"Document {doc_id} already exists.")
        return False

    def document_exists(self, doc_id: str) -> bool:
        """
        Check if a document exists in the collection.

        Args:
            doc_id (str): The ID of the document to check.
        Returns:
            bool: True if the document exists, False otherwise.
        """
        results = self.collection.get(ids=[doc_id], include=['metadatas'])
        return len(results['ids']) > 0

    def add_document(
            self, content, doc_id: str, metadata: dict = None, user_id=None, verbose=False) -> None:
        """
        Add a document to the collection.

        Args:
            content (str): The content of the document.
            doc_id (str): The ID of the document.
            metadata (dict): The metadata of the document.
            user_id (int): The ID of the user.
            verbose (bool): Whether to print verbose output.
        Returns:
            None
        """
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

    def get_document_by_id(self, doc_id: str):
        """
        Retrieve a document from the collection by its doc_id.

        Args:
            doc_id (str): The ID of the document to retrieve.
        Returns:
            dict: A dictionary containing the document's content, metadata, and embeddings (if available).
                  Returns None if the document is not found.
        """
        try:
            result = self.collection.get(
                ids=[doc_id],
                include=['documents', 'metadatas', 'embeddings']
            )
            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'document': result['documents'][0] if result['documents'] else None,
                    'metadata': result['metadatas'][0] if result['metadatas'] else None,
                    #'embedding': result['embeddings'][0] if result['embeddings'] else None
                }
            else:
                return None
        except Exception as e:
            print(f"{doc_id} not found: {e}")
            return ''

    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the collection to retrieve the most similar documents to the query text.

        Args:
            query_text (str): The text to query.
            top_k (int): The number of top results to return.

        Returns:
            List[Dict[str, Any]]: A list of documents with their content, metadata, and distances.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )

        documents = []
        for i in range(len(results['documents'][0])):
            documents.append({
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
            })
        return documents
