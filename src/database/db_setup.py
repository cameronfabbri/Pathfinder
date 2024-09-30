"""
File describing the database with additional functions for interacting with the database.
"""
# Cameron Fabbri

import sqlite3
import chromadb

from typing import Any, Dict, List
from contextlib import contextmanager
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings

import logging
from functools import lru_cache
from dataclasses import dataclass
import src.assessment as assessment
from src.database.db_access import get_db_connection


@dataclass
class Document:
    document_id: int
    document_type: str
    filename: str
    filepath: str
    upload_date: str
    extracted_text: str
    processed: bool


def create_user_tables():
    """
    Creates the tables for the users.
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

    # Create students table for user info
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

    # Create student_bios table for summarized user info
    # These bios are generated by the LLM based on the Strengths Finders Assessment test
    # and updated as the user interacts with the counselor
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_summaries (
            user_id INTEGER PRIMARY KEY,
            summary TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
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
            processed BOOLEAN DEFAULT FALSE,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
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
        user_vars = '(user_id, first_name, last_name, age, gender, high_school, high_school_grad_year, address, city, state, zip_code)'
        user_vals = (1, 'Cameron', 'Fabbri', 16, 'Male', 'Northport High School', 2024, '123 Main St', 'Northport', 'New York', 11768)
        cursor.execute(f"INSERT INTO students {user_vars} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", user_vals)
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
