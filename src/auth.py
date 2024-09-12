"""
"""

import os
import hashlib
from src.database import execute_query, get_db_connection, initialize_db
from src.user import User



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