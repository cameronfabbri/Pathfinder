"""
"""

import os
import sqlite3
import hashlib
import getpass

class User:
    def __init__(self, username, user_id):
        #self.first_name = first_name
        #self.last_name = last_name
        self.username = username
        self.user_id = user_id

    def __str__(self):
        return f"{self.username}"


# Database connection and setup
def initialize_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            hashed_password TEXT NOT NULL
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
def login():
    conn = initialize_db()
    cursor = conn.cursor()
    
    # Get username and password input
    #username = input("Enter username: ")
    #password = getpass.getpass("Enter password: ")
    username = 'cameron'
    password = 'fabbri'
    
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
        print(f"User created successfully! Your user ID is {user_id}\n")

    conn.close()

    return User(username, user_id)
