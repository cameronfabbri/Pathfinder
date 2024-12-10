"""
"""

import bcrypt
import logging
import sqlite3

from src.user import User
from src.database import db_access as dba, db_setup as dbs



def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt.

    Args:
        password (str): The plaintext password.

    Returns:
        str: The hashed password.
    """
    # Generate a salt and hash the password
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    # Return the hashed password as a string
    return hashed_pw.decode('utf-8')


def login(username: str, password: str) -> User:
    """
    Authenticate a user.

    Args:
        username (str): The username.
        password (str): The plaintext password.

    Returns:
        User: The authenticated user object or None if authentication fails.
    """

    try:
        conn = dba.get_db_connection()
        cursor = conn.cursor()

        # Fetch the hashed password from the database
        cursor.execute("SELECT id, session_id, hashed_password FROM users WHERE username=?", (username,))
        result = cursor.fetchone()

        if result:
            user_id, session_id, stored_hashed_password = result

            # Verify the entered password against the stored hashed password
            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
                # Update session_id
                cursor.execute("UPDATE users SET session_id = session_id + 1 WHERE username=?", (username,))
                conn.commit()
                return User(user_id, username, session_id + 1)
            else:
                logging.warning(f"Incorrect password for user: {username}")
        else:
            logging.warning(f"User not found: {username}")
    except sqlite3.Error as e:
        logging.error(f"Database error during login for user {username}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during login for user {username}: {e}")
    return None


def signup(first_name: str, last_name: str, age: int, gender: str, username: str, password: str) -> User:
    """
    Register a new user and create corresponding student information.

    Args:
        first_name (str): First name.
        last_name (str): Last name.
        age (int): Age.
        gender (str): Gender.
        username (str): Desired username.
        password (str): Desired password.

    Returns:
        User: The newly created user object or None if signup fails.
    """

    try:
        conn = dba.get_db_connection()
        cursor = conn.cursor()

        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            logging.warning(f"Username already exists: {username}")
            return -1

        hashed_password = hash_password(password)

        cursor.execute(
            "INSERT INTO users (username, session_id, hashed_password) VALUES (?, ?, ?)",
            (username, 0, hashed_password)
        )
        conn.commit()

        cursor.execute("SELECT id, session_id FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        user_id, session_id = result

        # Create the user databases
        print(f'Initializing user databases for {username} with user_id {user_id}')
        dbs.initialize_user_dbs(user_id)
        print('Done')

        # Insert default student information
        conn2 = dba.get_user_db_connection(user_id)
        cursor2 = conn2.cursor()
        user_vars = '(first_name, last_name, age, gender)'
        user_vals = (first_name, last_name, age, gender)
        cursor2.execute(f"INSERT INTO students {user_vars} VALUES (?, ?, ?, ?)", user_vals)
        conn2.commit()
        logging.info(f"User created successfully: {username}")

        return User(user_id, username, session_id)
    except sqlite3.Error as e:
        logging.error(f"Database error during signup for user {username}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during signup for user {username}: {e}")

    return None