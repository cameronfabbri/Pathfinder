"""
"""

import os
import hashlib
import streamlit as st

from src.database import get_db_connection, initialize_db
from src.user import User


def hash_password(password, salt=None):
    if not salt:
        salt = os.urandom(16)
    
    # Hash the password with the salt using SHA-256
    hashed_pw = hashlib.sha256(salt + password.encode()).hexdigest()
    return salt, hashed_pw


def login(username: str, password: str) -> User:
    """
    Function to check if user exists, or create new one if they don't
    """

    initialize_db()

    with get_db_connection() as conn:
        cursor = conn.cursor()
    
        # Check if the username exists
        cursor.execute("SELECT id, salt, hashed_password FROM users WHERE username=?", (username,))
        result = cursor.fetchone()

        if result:
            # If user exists, check the password
            user_id, stored_salt, stored_hashed_password = result

            # Convert stored salt from string back to bytes
            stored_salt = stored_salt.encode('latin1')
            
            # Hash the entered password with the stored salt
            _, hashed_password = hash_password(password, stored_salt)
            
            if hashed_password == stored_hashed_password:
                print(f"Login successful! Welcome, {username}!")
                print(f"Your user ID is {user_id}\n")
                cursor.execute("UPDATE users SET session_id = session_id + 1 WHERE username=?", (username,))
                conn.commit()
            else:
                print("Incorrect password.")
        
        cursor.execute("SELECT session_id FROM users WHERE username=?", (username,))
        session_id = cursor.fetchone()[0]
        return User(user_id, username, session_id)


def signup(first_name: str, last_name: str, age: int, gender: str, username: str, password: str) -> User:
    """
    Function to create a new user and student in the database

    Args:
        first_name (str): The first name of the student
        last_name (str): The last name of the student
        age (int): The age of the student
        gender (str): The gender of the student
        username (str): The username of the student
        password (str): The password of the student
    Returns:
        User: The user object
    """

    initialize_db()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        salt, hashed_password = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, session_id, salt, hashed_password) VALUES (?, ?, ?, ?)", 
            (username, 0, salt.decode('latin1'), hashed_password)
        )
        conn.commit()

        cursor.execute("SELECT id, session_id, salt, hashed_password FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        user_id = result[0]
        session_id = result[1]

        user_vars = '(user_id, first_name, last_name, age, gender, ethnicity, high_school, high_school_grad_year, address, city, state, zip_code)'
        user_vals = (user_id, first_name, last_name, age, gender, 'None', 'Northport High School', 2024, '123 Main St', 'Northport', 'New York', 11768)
        cursor.execute(f"INSERT INTO students {user_vars} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", user_vals)
        conn.commit()
        print(f"User info created successfully!\n")

        cursor.execute("SELECT session_id FROM users WHERE username=?", (username,))
        session_id = cursor.fetchone()[0]

    return User(user_id, username, session_id)