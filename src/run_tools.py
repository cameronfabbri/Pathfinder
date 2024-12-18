"""
Tools for running the application.
"""
# Cameron Fabbri
import os
import re
import sys
import json
import time
import logging
from typing import Callable

import streamlit as st

from icecream import ic

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.user import User
from src.agent import Message, Agent
from src.database import db_access as dba

from src import constants
from src import prompts, utils

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


def build_counselor_prompt(student_md_profile: str) -> str:
    """
    Builds the counselor system prompt using the student's info and counselor persona.
    """
    counselor_system_prompt = prompts.COUNSELOR_SYSTEM_PROMPT
    counselor_system_prompt = counselor_system_prompt.replace('{{persona}}', constants.PERSONA_PROMPT)
    counselor_system_prompt = counselor_system_prompt.replace('{{student_md_profile}}', student_md_profile)
    return counselor_system_prompt


# TODO - pass session state to this function
def load_message_history() -> None:
    """
    Load the message history from the database and add it to the session state
    """
    message_history = dba.load_message_history(st.session_state.user.user_id)

    for message in message_history:

        if message['chat_id'] != st.session_state.chat_id:
            continue

        tool_call = message['tool_call']
        if tool_call is not None:
            tool_call = json.loads(tool_call)

        m = Message(
            sender=message['sender'],
            recipient=message['recipient'],
            role=message['role'],
            message=message['message'],
            chat_id=message['chat_id'],
            tool_call=tool_call
        )

        if message['agent_name'] == 'counselor':
            st.session_state.counselor_agent.add_message(m)
        elif message['agent_name'] == 'suny':
            st.session_state.suny_agent.add_message(m)


def log_message(user_id: int, session_id: int, chat_id: int, message: Message, agent_name: str) -> None:
    """
    Logs a message to the database.

    Args:
        user_id (int): The ID of the user.
        session_id (int): The ID of the session.
        message (Message): The message to log.
        agent_name (str): The name of the agent that sent the message.
    Returns:
        None
    """
    tool_call = None
    if message.tool_call is not None:
        tool_call = json.dumps(message.tool_call)

    conn = dba.get_user_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversation_history (session_id, chat_id, role, sender, recipient, message, agent_name, tool_call)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, chat_id, message.role, message.sender, message.recipient, message.message, agent_name, tool_call))
    conn.commit()


def process_user_input(
        counselor_agent: Agent,
        suny_agent: Agent,
        user: User | None,
        chat_fn: Callable | None,
        prompt: str,
        chat_id: int
) -> None:
    """
    Process the user input and send it to the counselor agent

    Args:
        counselor_agent (Agent): The counselor agent
        suny_agent (Agent): The suny agent
        user (User): The user
        chat_fn (Callable): The chat function
        prompt (str): The prompt from the user
    Returns:
        None
    """

    message = Message(
        sender="student",
        recipient="counselor",
        role="user",
        message=prompt,
        chat_id=chat_id
    )

    if user is not None:
        # Log user input
        log_message(
            user.user_id,
            user.session_id,
            chat_id,
            message=message,
            agent_name='counselor'
        )
    counselor_agent.add_message(message)
    counselor_response = counselor_agent.invoke(chat_id=chat_id)

    counselor_response_str = counselor_response.choices[0].message.content
    counselor_response_json = utils.parse_json(counselor_response_str)

    recipient = counselor_response_json.get("recipient")
    phase = counselor_response_json.get("phase")

    if recipient.lower() == "suny":

        message = Message(
            sender="counselor",
            recipient="suny",
            role="user",
            message=counselor_response_str
        )

        if user is not None:
            # Log the counselor message to the suny agent
            log_message(
                user.user_id,
                user.session_id,
                chat_id,
                message=message,
                agent_name='suny'
                )

        if chat_fn is not None:
            chat_fn('assistant').write('Contacting SUNY Agent...')

        suny_agent.add_message(message)
        suny_response = suny_agent.invoke(chat_id=chat_id)

        if suny_response.choices[0].message.tool_calls:
            _, suny_response, tc_messages = suny_agent.handle_tool_call(
                suny_response
            )

            if user is not None:
                for tcm in tc_messages:
                    log_message(
                        user.user_id,
                        user.session_id,
                        chat_id,
                        tcm,
                        'suny'
                    )

        message = Message(
            sender="suny",
            recipient="counselor",
            role="assistant",
            message=suny_response.choices[0].message.content,
        )
        suny_agent.add_message(message)

        if user is not None:
            log_message(
                user.user_id,
                user.session_id,
                chat_id,
                message=message,
                agent_name='suny'
            )

        counselor_response_str = json.dumps({
            'phase': phase,
            'recipient': 'student',
            'message': suny_response.choices[0].message.content
        })

    message = Message(
        sender="counselor",
        recipient="student",
        role="assistant",
        message=counselor_response_str,
        chat_id=chat_id
    )
    counselor_agent.add_message(message)

    if user is not None:
        # Log the counselor message to the user
        log_message(
            user.user_id,
            user.session_id,
            chat_id,
            message=message,
            agent_name='counselor'
        )


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
    num_user_messages = len([x for x in st.session_state.counselor_agent.messages if x.role == 'user'])
    if num_user_messages > 0:
        message = Message(
            sender="student",
            recipient="counselor",
            role="user",
            message=prompts.SUMMARY_PROMPT,
            chat_id=st.session_state.chat_id
        )
        st.session_state.counselor_agent.add_message(message)
        response = st.session_state.counselor_agent.invoke(chat_id=st.session_state.chat_id)
        st.session_state.counselor_agent.delete_last_message()
        summary = response.choices[0].message.content
        summary = utils.parse_json(summary)['message']
    else:
        print("No summary to write")

    return summary


def write_summary_to_db(summary) -> None:
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


def logout() -> None:
    """
    Logout the user and clear the session state
    """
    summary = summarize_chat()

    if summary:
        write_summary_to_db(summary)

    # Clear the session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Rerun the script to return to the login page
    st.rerun()
