"""
File describing the database with additional functions for creating the database.
"""
# Cameron Fabbri
import logging
import sqlite3

from typing import Any, Dict, List
from functools import lru_cache
from contextlib import contextmanager
from dataclasses import dataclass

import src.assessment as assessment

from src.database.db_access import get_db_connection, get_user_db_connection


@dataclass
class Document:
    document_id: int
    document_type: str
    filename: str
    filepath: str
    upload_date: str
    extracted_text: str
    processed: bool


def create_auth_tables():
    """
    Creates the tables for authentication.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            session_id INTEGER NOT NULL,
            hashed_password TEXT NOT NULL
        )
    ''')

    conn.commit()


def create_user_tables(user_id: int):
    """
    Creates the tables for the users.
    """
    conn = get_user_db_connection(user_id)
    cursor = conn.cursor()

    # Create students table for user info
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
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
            other_schools TEXT
        );
    ''')

    # Create user_documents table for user documents
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_documents (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            extracted_text TEXT DEFAULT '',
            processed BOOLEAN DEFAULT FALSE
        );
    ''')

    conn.commit()


def create_chat_tables(user_id: int):
    """
    Creates tables for chat history, counselor-SUNY interactions, and chat summaries.
    """
    conn = get_user_db_connection(user_id)
    cursor = conn.cursor()

    # Table to store user-counselor-suny interactions
    # agent_name is the name of the agent that holds the message in its messages list
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL, -- user, assistant, or tool
            sender TEXT NOT NULL, -- student, counselor, or suny
            recipient TEXT NOT NULL, -- student, counselor, or suny
            message TEXT NOT NULL,
            agent_name TEXT NOT NULL, -- counselor, or suny
            tool_call TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Chat summaries for user-counselor conversation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()


def create_assessment_tables(user_id: int):
    """
    Creates the tables for the assessment.
    """
    conn = get_user_db_connection(user_id)
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
            question_id INTEGER NOT NULL,
            response INTEGER CHECK(response BETWEEN 1 AND 5),
            FOREIGN KEY (question_id) REFERENCES questions(question_id)
        );
    ''')

    # Table to store results per theme
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS theme_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_id INTEGER NOT NULL,
            total_score INTEGER CHECK(total_score BETWEEN 3 AND 15),
            strength_level TEXT,
            FOREIGN KEY (theme_id) REFERENCES themes(theme_id)
        );
    ''')

    # Table to store the assessment analysis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assessment_analysis (
            analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis TEXT NOT NULL
        );
    ''')

    # Check if domains table is empty
    cursor.execute("SELECT COUNT(*) FROM domains")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO domains (domain_name) VALUES (?)", assessment.domains)
        cursor.executemany("INSERT INTO themes (domain_id, theme_name) VALUES (?, ?)", assessment.themes)
        cursor.executemany("INSERT INTO questions (theme_id, statement) VALUES (?, ?)", assessment.questions)
        print("Assessment data initialized successfully.")
    else:
        print("Assessment data already exists. Skipping initialization.")

    conn.commit()


def initialize_user_dbs(user_id: int):
    """
    Initializes the user databases.
    """
    create_user_tables(user_id)
    create_chat_tables(user_id)
    create_assessment_tables(user_id)


def initialize_test_user(username: str):
    """
    Initializes the database with the necessary tables and data.
    """

    # TODO - remove after testing
    from src.auth import hash_password

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))

    if cursor.fetchone()[0] == 0:
        hashed_password = hash_password('test_password')

        cursor.execute(
            "INSERT INTO users (username, session_id, hashed_password) VALUES (?, ?, ?)",
            (username, -1, hashed_password)
        )

    conn.commit()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = cursor.fetchone()[0]

    initialize_user_dbs(user_id)

    conn2 = get_user_db_connection(user_id)
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT COUNT(*) FROM students")
    if cursor2.fetchone()[0] == 0:
        user_vars = '(first_name, last_name, age, gender, high_school, high_school_grad_year, address, city, state, zip_code)'
        user_vals = ('Cameron', 'Fabbri', 16, 'Male', 'Northport High School', 2024, '123 Main St', 'Northport', 'New York', 11768)
        cursor2.execute(f"INSERT INTO students {user_vars} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", user_vals)
        conn2.commit()

    return user_id