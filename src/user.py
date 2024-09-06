"""
"""

import os
import sqlite3
import hashlib
import getpass


class User:
    def __init__(self, user_id, username, login_number):
        self.user_id = user_id
        self.username = username
        self.login_number = login_number
        self.load_user_info() 

    def __str__(self):
        user_info_str = (
            f"User: {self.username} \nID: {self.user_id} \nFirst Name: {self.first_name} \nLast Name: {self.last_name}\n" +
            f"Email: {self.email}\nPhone Number: {self.phone_number}\nAge: {self.age}\nGender: {self.gender}\n" +
            f"Ethnicity: {self.ethnicity}\nHigh School: {self.high_school}\nHigh School Grad Year: {self.high_school_grad_year}\n" +
            f"GPA: {self.gpa}\nSAT Score: {self.sat_score}\nACT Score: {self.act_score}\nFavorite Subjects: {self.favorite_subjects}\n" +
            f"Extracurriculars: {self.extracurriculars}\nCareer Aspirations: {self.career_aspirations}\nPreferred Major: {self.preferred_major}\n" +
            f"Clifton Strengths: {self.clifton_strengths}\nPersonality Test Results: {self.personality_test_results}\n" +
            f"Address: {self.address}\nCity: {self.city}\nState: {self.state}\nZip Code: {self.zip_code}\n" +
            f"Intended College: {self.intended_college}\nIntended Major: {self.intended_major}\nLogin Number: {self.login_number}"
        )
        return user_info_str

    def load_user_info(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE user_id=?", (self.user_id,))
            result = cursor.fetchone()
            if result:
                (
                    self.first_name, self.last_name, self.email, self.phone_number, _,
                    self.age, self.gender, self.ethnicity, self.high_school,
                    self.high_school_grad_year, self.gpa, self.sat_score, self.act_score,
                    self.favorite_subjects, self.extracurriculars, self.career_aspirations,
                    self.preferred_major, self.clifton_strengths, self.personality_test_results,
                    self.address, self.city, self.state, self.zip_code, self.intended_college,
                    self.intended_major
                ) = result
            else:
                print(f"No student information found for user ID {self.user_id}")

    def get_user_info(self):
        return self.__str__()

    def save(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE students SET 
                    first_name = ?, last_name = ?, email = ?, phone_number = ?, age = ?, gpa = ?, 
                    sat_score = ?, act_score = ?, favorite_subjects = ?, career_aspirations = ?,
                    high_school = ?, high_school_grad_year = ?, ethnicity = ?, 
                    clifton_strengths = ?, personality_test_results = ?, address = ?, 
                    city = ?, state = ?, zip_code = ?, intended_college = ?, intended_major = ?
                WHERE user_id = ?
            ''', (self.first_name, self.last_name, self.email, self.phone_number, self.age, 
                self.gpa, self.sat_score, self.act_score, self.favorite_subjects, 
                self.career_aspirations, self.high_school, self.high_school_grad_year, self.ethnicity, 
                self.clifton_strengths, self.personality_test_results, self.address, 
                self.city, self.state, self.zip_code, self.intended_college, self.intended_major, self.user_id
                )
            )
            conn.commit()

    def add_chat_history(self, message):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_history (user_id, message) VALUES (?, ?)", 
                        (self.user_id, message))
            conn.commit()


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
    initialize_db()

    with get_db_connection() as conn:
        cursor = conn.cursor()
    
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
                cursor.execute("UPDATE users SET login_number = login_number + 1 WHERE username=?", (username,))
                conn.commit()
            else:
                print("Incorrect password.")
        else:
            # If user does not exist, create a new user with hashed and salted password
            salt, hashed_password = hash_password(password)
            cursor.execute("INSERT INTO users (username, salt, hashed_password, login_number) VALUES (?, ?, ?, ?)", 
                        (username, salt.decode('latin1'), hashed_password, 0))
            conn.commit()

            cursor.execute("SELECT id, salt, hashed_password FROM users WHERE username=?", (username,))
            result = cursor.fetchone()
            user_id = result[0]

            print(f"User created successfully! Your user ID is {user_id}\n")

            user_vars = '(user_id, first_name, last_name, age, gender, ethnicity, high_school, high_school_grad_year, address, city, state, zip_code)'
            user_vals = (user_id, 'Cameron', 'Fabbri', 16, 'male', 'white', 'Northport High School', 2024, '123 Main St', 'Northport', 'New York', 11768)
            cursor.execute(f"INSERT INTO students {user_vars} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", user_vals)
            conn.commit()
            print(f"User info created successfully!\n")

        cursor.execute("SELECT login_number FROM users WHERE username=?", (username,))
        login_number = cursor.fetchone()[0]

    return User(user_id, username, login_number)

def select_from_db(query, args):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, args)
        out = cursor.fetchall()
    return out

def get_db_connection():
    """
    Returns a connection to the database.
    """
    return sqlite3.connect('users.db')
