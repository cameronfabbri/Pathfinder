"""
File holding the database access functions.
"""
# Cameron Fabbri
import logging
import sqlite3

from typing import Tuple
from functools import lru_cache

from openai import OpenAI

from src import prompts
from src import constants
import os


@lru_cache(maxsize=None)
def get_user_db_connection(user_id: int) -> sqlite3.Connection:
    """
    Returns a connection to the database.
    """
    db_path = os.path.join(constants.SQL_DB_DIR, f'user_{user_id}.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@lru_cache(maxsize=None)
def get_db_connection() -> sqlite3.Connection:
    """
    Returns a connection to the database.
    """
    #conn = sqlite3.connect(os.path.join(os.getcwd(), 'data', 'users.db'), check_same_thread=False)
    db_path = os.path.join(constants.SQL_DB_DIR, 'users.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def execute_query(conn, query, args=None) -> list | None:
    """
    Execute a query on the database

    Args:
        query (str): The query to execute
        args (tuple): The arguments to pass to the query
    Returns:
        The result of the query | None if error
    """
    try:
        #conn = get_db_connection()
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


def parse_sql_result(cursor: sqlite3.Cursor):
    """ Parse the result of a SQL query into a dictionary. """
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def load_message_history(user_id: int):
    """ Loads the message history of the user. """
    conn = get_user_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id, sender, recipient, role, message, timestamp, agent_name, tool_call FROM conversation_history
        ORDER BY timestamp ASC
    """)
    return parse_sql_result(cursor)


def get_student_info(user_id: int):
    """
    Gets all of the information from the students table for the given user_id
    """
    conn = get_user_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    result = cursor.fetchone()
    student_info = {}
    if result:
        columns = [column[0] for column in cursor.description]
        for column_name, value in zip(columns, result):
            student_info[column_name] = value
    return student_info


def load_assessment_responses(user_id: int):
    conn = get_user_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT questions.statement, user_responses.response
        FROM user_responses
        JOIN questions ON user_responses.question_id = questions.question_id
    ''')
    return [
        (row['statement'], row['response'])
        for row in cursor.fetchall()
    ]


def get_topbot_strengths(user_id: int, k: int) -> Tuple[list, list]:
    """
    Get the top k strengths and bottom k strengths of the user.

    Args:
        user_id (int): The user ID
        k (int): The number of strengths to get
    Returns:
        top_strengths (list): The top strengths
        bot_strengths (list): The bottom strengths
    """
    conn = get_user_db_connection(user_id)
    cursor = conn.cursor()

    # Load top strengths
    cursor.execute('''
        SELECT themes.theme_name, theme_results.total_score, theme_results.strength_level
        FROM theme_results
        JOIN themes ON theme_results.theme_id = themes.theme_id
        ORDER BY theme_results.total_score DESC
        LIMIT ?
    ''', (k,))
    top_strengths = [
        {
            'theme_name': row['theme_name'],
            'total_score': row['total_score'],
            'strength_level': row['strength_level']
        }
        for row in cursor.fetchall()
    ]

    # Load weaknesses (bottom strengths)
    cursor.execute('''
        SELECT themes.theme_name, theme_results.total_score, theme_results.strength_level
        FROM theme_results
        JOIN themes ON theme_results.theme_id = themes.theme_id
        ORDER BY theme_results.total_score ASC
        LIMIT ?
    ''', (k,))
    bot_strengths = [
        {
            'theme_name': row['theme_name'],
            'total_score': row['total_score'],
            'strength_level': row['strength_level']
        }
        for row in cursor.fetchall()
    ]

    return top_strengths, bot_strengths


def update_student_info(user_id: int, student_info: dict) -> None:
    """
    Update the student info in the database

    Args:
        user_id (int): The user ID
        student_info (dict): The student info
    Returns:
        None
    """

    # Define a whitelist of allowed columns to update
    # TODO - define this in db_setup and import it
    allowed_columns = {
        'first_name', 'last_name', 'email', 'phone_number', 'address',
        'city', 'state', 'zip_code', 'age', 'gender', 'high_school',
        'high_school_grad_year', 'gpa', 'sat_score', 'act_score',
        'favorite_subjects', 'extracurriculars', 'career_aspirations',
        'preferred_major', 'other_majors', 'top_school', 'safety_school',
        'other_schools'
    }

    # Filter student_info to include only allowed columns
    filtered_info = {key: value for key, value in student_info.items() if key in allowed_columns}

    if not filtered_info:
        logging.info("No valid fields to update.")
        return

    # Build the SET part of the query with placeholders
    set_clause = ', '.join([f"{key}=?" for key in filtered_info.keys()])

    # The SQL query with parameter placeholders
    query = f"UPDATE students SET {set_clause}"

    # Prepare the parameters tuple
    parameters = tuple(filtered_info.values())

    try:
        conn = get_user_db_connection(user_id)
        cursor = conn.cursor()
        cursor.execute(query, parameters)
        conn.commit()
        logging.info(f"Student info updated successfully for user_id: {user_id}")
    except sqlite3.Error as e:
        logging.error(f"An error occurred while updating student info: {e}")


def get_chat_summary_from_db(client: OpenAI, user_id: int) -> str:
    """
    Get the chat summary from the database

    Args:
        client (OpenAI): The OpenAI client
    Returns:
        summary (str): The chat summary
    """

    query = "SELECT summary FROM chat_summary ORDER BY id DESC LIMIT 1;"

    # [0][0] because the execute_query uses fetchall(), not fetchone()
    conn = get_user_db_connection(user_id)
    summary = execute_query(conn, query)[0][0]
    prompt = prompts.WELCOME_BACK_PROMPT.format(summary=summary)
    response = client.chat.completions.create(
        model='gpt-4o-2024-08-06',
        messages=[
            {"role": "assistant", "content": prompt},
        ],
        temperature=0.0
    )
    first_message = response.choices[0].message.content
    return first_message


def insert_user_responses(user_id, responses):
    """
    Insert the responses to the assessment test into the user_responses table.

    Args:
        user_id (int): The ID of the user.
        responses (dict): The user responses.
    Returns:
        None
    """
    conn = get_user_db_connection(user_id)
    cursor = conn.cursor()

    # Insert user responses into the user_responses table
    for statement, score in responses.items():
        cursor.execute("SELECT question_id FROM questions WHERE statement=?", (statement,))
        question_id = cursor.fetchone()[0]

        #print('Inserted response:', statement, score)
        cursor.execute(
            "INSERT INTO user_responses (question_id, response) VALUES (?, ?)",
            (question_id, score)
        )

    conn.commit()


def insert_assessment_analysis(user_id: int, analysis: str) -> None:
    """
    Insert the assessment analysis into the assessment_analysis table.
    """
    conn = get_user_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO assessment_analysis (analysis) VALUES (?)", (analysis,))
    conn.commit()


def load_assessment_analysis(user_id: int) -> str:
    """
    Load the assessment analysis from the assessment_analysis table.
    """
    query = "SELECT analysis FROM assessment_analysis ORDER BY analysis_id DESC LIMIT 1;"
    conn = get_user_db_connection(user_id)
    return execute_query(conn, query)[0][0]


def insert_strengths(user_id, strengths):
    """
    Insert the Strengths scores into the theme_results table.

    Args:
        user_id (int): The ID of the user.
        strengths (dict): The Strengths scores.
    Returns:
        None
    """
    conn = get_user_db_connection(user_id)
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

        cursor.execute(
            "INSERT INTO theme_results (theme_id, total_score, strength_level) VALUES (?, ?, ?)",
            (theme_id, score, strength_level)
        )

    conn.commit()