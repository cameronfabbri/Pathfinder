"""
"""
# Cameron Fabbri

import os
import re
import sys
import time
import sqlite3
import streamlit as st

import logging

from openai import OpenAI

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src import utils
from src import prompts
from src.database import db_access as dba
from src.pdf_tools import parse_pdf_with_llama

opj = os.path.join

# Configure logging
logging.basicConfig(level=logging.INFO)


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


def log_message(user_id, session_id, sender, recipient, message):
    """
    Store a message in the conversation history.

    Args:
        user_id (int): The ID of the user.
        sender (str): The sender of the message.
        recipient (str): The recipient of the message.
        message (str): The message content.
    """
    conn = dba.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversation_history (user_id, session_id, sender, recipient, message)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, session_id, sender, recipient, message))
    conn.commit()


def parse_counselor_response(response):

    counselor_response_str = response.choices[0].message.content
    counselor_response_json = utils.parse_json(counselor_response_str)

    recipient = counselor_response_json.get("recipient")
    counselor_message = counselor_response_json.get("message")

    return recipient, counselor_message


def process_user_input(prompt):
    counselor_agent = st.session_state.counselor_agent
    suny_agent = st.session_state.suny_agent

    # Log user input
    log_message(st.session_state.user.user_id, st.session_state.user.session_id, 'user', 'counselor', prompt)

    counselor_agent.add_message("user", prompt)
    counselor_response = counselor_agent.invoke()

    print('COUNSELOR MESSAGES')
    counselor_agent.print_messages(True)

    print('NEXT MESSAGE')
    print(counselor_response)

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
            _, suny_response = suny_agent.handle_tool_call(suny_response)

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

    elif 0:#recipient == "system":
        # Call update student bio function

        # TODO - what if the student says something like "my gpa is a 3.4, which
        # suny schools should I apply to?" Then this part won't work as expected
        # because I'm now assuming the response is for the counselor to respond
        # to the user.
        print('recipient == system')
        print('counselor_message:', counselor_message, '\n')

        counselor_agent.add_message("assistant", counselor_message)
        log_message(st.session_state.user.user_id, st.session_state.user.session_id, 'counselor', 'system', counselor_message)
        recipient, counselor_message = parse_counselor_response(counselor_agent.invoke())
        print('invoked()')
        print('recipient:', recipient)
        print('counselor_message:', counselor_message, '\n')

    counselor_agent.add_message("assistant", counselor_message)
    st.session_state.user_messages.append({"role": "assistant", "content": counselor_message})

    # Log the counselor message to the user
    log_message(st.session_state.user.user_id, st.session_state.user.session_id, 'counselor', 'user', counselor_message)


def process_uploaded_file(uploaded_file, document_type, user_id):
    """
    Process the uploaded file and add it to the database

    Args:
        uploaded_file (File): The uploaded file
        document_type (str): The type of document
        user_id (int): The user ID
    Returns:
        None
    """
    upload_dir = opj('uploads', str(user_id))
    os.makedirs(upload_dir, exist_ok=True)

    filename, extension = os.path.splitext(os.path.basename(uploaded_file.name))

    filepath = os.path.join(upload_dir, filename + extension)
    idx = 0
    while os.path.exists(filepath):
        filepath = os.path.join(upload_dir, filename + f'_{idx}' + extension)
        idx += 1

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getvalue())

    # Process the transcript using parse_pdf_with_llama
    transcript_text = '\n'.join([x.text for x in parse_pdf_with_llama(filepath)])

    #client = utils.get_openai_client()
    print('Document type:', document_type)


    return transcript_text

    # Insert into chromadb
    #db = ChromaDB(path='./chroma_data')
    #db.add_document(transcript_text, doc_id=uploaded_file.name, user_id=st.session_state.user.user_id)


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
        """
        from src.agent import Agent
        client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
        agent = Agent(
            client,
            name="Agent",
            tools=None,
            model='gpt-4o-mini',
            system_prompt="You are a helpful assistant that summarizes the conversation. Do not include a title or any other formatting. Just the summary.",
            json_mode=False
        )
        agent.add_message("user", prompts.SUMMARY_PROMPT)
        response = agent.invoke()
        """
        summary = response.choices[0].message.content
        print('summary response', summary)
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
    res = dba.execute_query(query, args)
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
