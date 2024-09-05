"""
"""

import os
import sqlite3
import hashlib
import getpass

class User:
    def __init__(self, username, user_id):
        self.username = username
        self.user_id = user_id

    def __str__(self):
        return f"{self.username}"


# Database connection and setup
def initialize_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            hashed_password TEXT NOT NULL
        )
    ''')
    conn.commit()

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
            application_status TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    ''')
    conn.commit()

    # Create chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            login_number INTEGER NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    return conn

# Function to hash and salt password
def hash_password(password, salt=None):
    if not salt:
        # Generate a new salt if not provided
        salt = os.urandom(16)
    
    # Hash the password with the salt using SHA-256
    hashed_pw = hashlib.sha256(salt + password.encode()).hexdigest()
    return salt, hashed_pw

# Function to check if user exists, or create new one if they don't
def login(username, password):
    conn = initialize_db()
    cursor = conn.cursor()
    
    # Get username and password input
    #username = input("Enter username: ")
    #password = getpass.getpass("Enter password: ")
    #username = 'cameron'
    #password = 'fabbri'
    
    # Check if the username exists
    cursor.execute("SELECT id, salt, hashed_password FROM users WHERE username=?", (username,))
    result = cursor.fetchone()

    if result:
        # If user exists, check the password
        user_id, stored_salt, stored_hashed_password = result
        stored_salt = stored_salt.encode('latin1')  # Convert stored salt from string back to bytes
        
        # Hash the entered password with the stored salt
        _, hashed_password = hash_password(password, stored_salt)
        
        if hashed_password == stored_hashed_password:
            print(f"Login successful! Welcome, {username}!")
            print(f"Your user ID is {user_id}\n")
        else:
            print("Incorrect password.")
    else:
        # If user does not exist, create a new user with hashed and salted password
        salt, hashed_password = hash_password(password)
        cursor.execute("INSERT INTO users (username, salt, hashed_password) VALUES (?, ?, ?)", 
                       (username, salt.decode('latin1'), hashed_password))
        conn.commit()

        cursor.execute("SELECT id, salt, hashed_password FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        user_id = result[0]

        print(f"User created successfully! Your user ID is {user_id}\n")

        cursor.execute("INSERT INTO students (user_id, age) VALUES (?, ?)", (user_id, 16))
        conn.commit()
        print(f"User info created successfully!\n")

    conn.close()

    return User(username, user_id)
