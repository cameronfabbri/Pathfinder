"""
"""
# Cameron Fabbri
import os
import re
import sys
import time
import logging
import sqlite3

import streamlit as st

from openai import OpenAI
from icecream import ic

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src import prompts, utils
from src.database import db_access as dba
from src.agent import Message

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


# TODO - pass session state to this function
def load_message_history():
    message_history = dba.load_message_history(st.session_state.user.user_id)
    for message in message_history:

        m = Message(
            sender=message['sender'],
            recipient=message['recipient'],
            role=message['role'],
            message=message['message']
        )

        if message['agent_name'] == 'counselor':
            st.session_state.counselor_agent.add_message(m)
        elif message['agent_name'] == 'suny':
            st.session_state.suny_agent.add_message(m)


def log_message(user_id, session_id, message, agent_name):#role, sender, recipient, message, agent_name):
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
        INSERT INTO conversation_history (user_id, session_id, role, sender, recipient, message, agent_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, session_id, message.role, message.sender, message.recipient, message.message, agent_name))
    conn.commit()


def parse_counselor_response(response):

    counselor_response_str = response.choices[0].message.content
    counselor_response_json = utils.parse_json(counselor_response_str)

    recipient = counselor_response_json.get("recipient")
    counselor_message = counselor_response_json.get("message")

    return recipient, counselor_message


def process_user_input(counselor_agent, suny_agent, prompt: str, stm):
    """
    Process the user input and send it to the counselor agent
    """

    message = Message(
        sender="student",
        recipient="counselor",
        role="user",
        message=prompt
    )

    # Log user input
    if stm is not None:
        log_message(
            stm.session_state.user.user_id,
            stm.session_state.user.session_id,
            message=message,
            agent_name='counselor'
        )
    counselor_agent.add_message(message)
    counselor_response = counselor_agent.invoke()

    counselor_response_str = counselor_response.choices[0].message.content
    counselor_response_json = utils.parse_json(counselor_response_str)

    recipient = counselor_response_json.get("recipient")
    #counselor_message = counselor_response_json.get("message")
    #phase = counselor_response_json.get("phase")

    if recipient.lower() == "suny":

        message = Message(
            sender="counselor",
            recipient="suny",
            role="user",
            message=counselor_response_str
        )

        # Log the counselor message to the suny agent
        if stm is not None:
            log_message(
                stm.session_state.user.user_id,
                stm.session_state.user.session_id,
                message=message,
                agent_name='suny'
            )

            stm.chat_message('assistant').write('Contacting SUNY Agent...')
            #stm.session_state.counselor_suny_messages.append({"role": "counselor", "content": counselor_message})

        suny_agent.add_message(message)
        suny_response = suny_agent.invoke()

        if suny_response.choices[0].message.tool_calls:
            _, suny_response = suny_agent.handle_tool_call(suny_response)

        #suny_response_str = utils.format_for_json(suny_response.choices[0].message.content)
        #if stm is not None:
        #    stm.session_state.counselor_suny_messages.append({"role": "suny", "content": suny_response_str})
        message = Message(
            sender="suny",
            recipient="counselor",
            role="assistant",
            message=suny_response.choices[0].message.content,
        )
        suny_agent.add_message(message)

        if stm is not None:
            log_message(
                stm.session_state.user.user_id,
                stm.session_state.user.session_id,
                message=message,
                agent_name='suny'
            )

        # Add the suny response to the counselor agent and invoke it so it rewords it
        counselor_agent.add_message(message)

        counselor_response = counselor_agent.invoke()

        counselor_response_str = counselor_response.choices[0].message.content
        #counselor_response_json = utils.parse_json(counselor_response_str)
        #counselor_message = counselor_response_json.get("message")

        # The response from the suny agent is added to the list of messages for
        # the counselor agent, and then we invoke the counselor agent so it
        # rephrases the information from the suny agent. We then want to replace
        # the information from the suny agent with the response from the
        # counselor agent, which is why we delete the last message.
        counselor_agent.delete_last_message()

    message = Message(
        sender="counselor",
        recipient="student",
        role="assistant",
        message=counselor_response_str
    )
    counselor_agent.add_message(message)
    if stm is not None:

        # Log the counselor message to the user
        log_message(
            stm.session_state.user.user_id,
            stm.session_state.user.session_id,
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
    num_user_messages = len([msg for msg in st.session_state.counselor_user_messages if msg['role'] == 'user'])
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
