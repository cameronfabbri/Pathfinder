"""
"""
import os
import sys
import time
import streamlit as st

from openai import OpenAI

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src import utils
from src import prompts
from src.user import User
from src.pdf_tools import parse_pdf_with_llama
from src.database import ChromaDB, execute_query

import re

def type_text(text, char_speed=0.03, sentence_pause=0.5):
    placeholder = st.empty()
    full_text = ""
    sentences = re.split('([.!?]+)', text)
    
    for sentence in sentences:
        for char in sentence:
            full_text += char
            placeholder.markdown(full_text + "▌")
            time.sleep(char_speed)
        
        # Pause after completing a sentence (if it ends with .!?)
        if sentence.strip() and sentence.strip()[-1] in '.!?':
            placeholder.markdown(full_text)
            time.sleep(sentence_pause)
    
    placeholder.markdown(full_text)


from src.database import get_db_connection

def store_conversation(conversation_id, user_id, agent_type, message):
    """
    Store a message in the conversation history.

    Args:
        conversation_id (int): The ID of the conversation.
        user_id (int): The ID of the user.
        agent_type (str): Type of agent (e.g., 'user', 'counselor', 'suny_agent').
        message (str): The message content.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        print('conversation_id:', conversation_id)
        print('user_id:', user_id)
        print('agent_type:', agent_type)
        print('message:', message)
        cursor.execute('''
            INSERT INTO conversation_history (conversation_id, user_id, agent_type, message)
            VALUES (?, ?, ?, ?)
        ''', (conversation_id, user_id, agent_type, message))
        conn.commit()


def create_new_conversation(user_id):
    """
    Start a new conversation for a user and return the conversation_id.

    Args:
        user_id (int): The user initiating the conversation.

    Returns:
        int: The conversation ID for the new conversation.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversation_history (user_id, agent_type, message)
            VALUES (?, ?, ?)
        ''', (user_id, 'user', 'Conversation started'))
        conversation_id = cursor.lastrowid
        conn.commit()
    return conversation_id


def log_message(user_id, session_id, sender, recipient, message):
    """
    Store a message in the conversation history.

    Args:
        user_id (int): The ID of the user.
        sender (str): The sender of the message.
        recipient (str): The recipient of the message.
        message (str): The message content.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversation_history (user_id, session_id, sender, recipient, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, session_id, sender, recipient, message))
        conn.commit()


def process_user_input(prompt):
    counselor_agent = st.session_state.counselor_agent
    suny_agent = st.session_state.suny_agent

    # Log user input
    log_message(st.session_state.user.user_id, st.session_state.user.session_id, 'user', 'counselor', prompt)

    counselor_agent.add_message("user", prompt)
    counselor_response = counselor_agent.invoke()

    counselor_response_str = counselor_response.choices[0].message.content
    counselor_response_json = utils.parse_json(counselor_response_str)

    recipient = counselor_response_json.get("recipient")
    counselor_message = counselor_response_json.get("message")

    if recipient == "suny":

        # Log the counselor message to the suny agent
        log_message(st.session_state.user.user_id, st.session_state.user.session_id, 'counselor', 'suny', counselor_message)

        st.chat_message('assistant').write('Contacting SUNY Agent...')
        st.session_state.counselor_suny_messages.append({"role": "counselor", "content": counselor_message})
        suny_agent.add_message("user", counselor_message)
        suny_response = suny_agent.invoke()

        if suny_response.choices[0].message.tool_calls:
            suny_response = suny_agent.handle_tool_call(suny_response)

        suny_response_str = utils.format_for_json(suny_response.choices[0].message.content)
        st.session_state.counselor_suny_messages.append({"role": "suny", "content": suny_response_str})
        suny_agent.add_message("assistant", suny_response_str)

        # Log the suny response to the counselor
        log_message(st.session_state.user.user_id, st.session_state.user.session_id, 'suny', 'counselor', suny_response_str)

        # Add the suny response to the counselor agent and invoke it so it rewords it
        counselor_agent.add_message("assistant", 'SUNY Agent responded with the following information:\n' + suny_response_str + '}')
        counselor_response = counselor_agent.invoke()

        counselor_response_str = counselor_response.choices[0].message.content
        counselor_response_json = utils.parse_json(counselor_response_str)
        counselor_message = counselor_response_json.get("message")

        # The response from the suny agent is added to the list of messages for
        # the counselor agent, and then we invoke the counselor agent so it
        # rephrases the information from the suny agent. We then want to replace
        # the information from the suny agent with the response from the
        # counselor agent, which is why we delete the last message.
        counselor_agent.delete_last_message()

    counselor_agent.add_message("assistant", counselor_message)
    st.session_state.user_messages.append({"role": "assistant", "content": counselor_message})

    # Log the counselor message to the user
    log_message(st.session_state.user.user_id, st.session_state.user.session_id, 'counselor', 'user', counselor_message)


def get_student_info(user: User) -> dict:
    """
    Get the login number and student info from the database

    Args:
        user (User): The user object

    Returns:
        student_info_dict (dict): The student info
    """

    student_info = execute_query("SELECT * FROM students WHERE user_id=?;", (user.user_id,))[0]

    return {
        'first_name': student_info[0],
        'last_name': student_info[1],
        #'email': student_info[2],
        #'phone_number': student_info[3],
        #'user_id': student_info[4],
        'age': student_info[5],
        'gender': student_info[6],
        'ethnicity': student_info[7],
        'high_school': student_info[8],
        'high_school_grad_year': student_info[9],
        'gpa': student_info[10],
        #'sat_score': student_info[11],
        #'act_score': student_info[12],
        'favorite_subjects': student_info[13],
        'extracurriculars': student_info[14],
        'career_aspirations': student_info[15],
        'preferred_major': student_info[16],
        'address': student_info[19],
        'city': student_info[20],
        'state': student_info[21],
        'zip_code': student_info[22],
        'intended_college': student_info[23],
        'intended_major': student_info[24],
    }


def update_student_info(user: User, student_info: dict):
    """
    Update the student info in the database

    Args:
        user (User): The user object
        student_info (dict): The student info
    Returns:
        None
    """
    query = f"UPDATE students SET {', '.join([f'{key}=?' for key in student_info])} WHERE user_id=?"
    print('QUERY')
    print(query)
    print('ARGS')
    print(tuple(list(student_info.values()) + [st.session_state.user.user_id]))
    execute_query(query, tuple(list(student_info.values()) + [st.session_state.user.user_id]))


def process_transcript(uploaded_file):
    upload_dir = 'uploads'
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    # Process the transcript using parse_pdf_with_llama
    transcript_text = parse_pdf_with_llama(file_path)

    # Insert into chromadb
    db = ChromaDB(path='./chroma_data')
    db.add_document(transcript_text, doc_id=uploaded_file.name, user_id=st.session_state.user.user_id)


def summarize_chat():
    """
    Summarize the chat and add it to the database

    Args:
        None
    Returns:
        summary (str): The summary of the chat
    """

    summary = None

    # Only summarize the chat if the counselor agent has received user messages
    num_user_messages = len([msg for msg in st.session_state.counselor_agent.messages if msg['role'] == 'user'])
    if num_user_messages > 0:
        st.session_state.counselor_agent.add_message("user", prompts.SUMMARY_PROMPT)
        response = st.session_state.counselor_agent.invoke()
        st.session_state.counselor_agent.delete_last_message()
        summary = response.choices[0].message.content
        summary = utils.parse_json(summary)['message']

        print("SUMMARY")
        print(summary)
        print('\n')
        print('\n------------------------MESSAGES----------------------------------\n')
        [print(x) for x in st.session_state.counselor_agent.messages]
        print('\n------------------------------------------------------------------\n')
    else:
        print("No summary to write")

    return summary


def write_summary_to_db(summary):
    """
    Write the summary to the database

    Args:
        summary (str): The summary of the chat
    Returns:
        None
    """
    query = "INSERT INTO chat_summary (user_id, summary) VALUES (?, ?)"
    args = (st.session_state.user.user_id, summary)
    print('Query:', query)
    print('Args:', args)
    res = execute_query(query, args)
    print('Chat summary updated')
    print('Result:', res)


def logout():

    summary = summarize_chat()

    if summary:
        write_summary_to_db(summary)

    # Clear the session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Rerun the script to return to the login page
    st.rerun()


def get_chat_summary_from_db(client: OpenAI) -> str:
    """
    Get the chat summary from the database

    Args:
        client (OpenAI): The OpenAI client
    Returns:
        summary (str): The chat summary
    """

    query = "SELECT summary FROM chat_summary WHERE user_id=? ORDER BY id DESC LIMIT 1;"

    # [0][0] because the execute_query uses fetchall(), not fetchone()
    summary = execute_query(query, (st.session_state.user.user_id,))[0][0]
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