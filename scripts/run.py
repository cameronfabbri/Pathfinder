"""
Main script
"""
# Cameron Fabbri

import os
import sys
import icecream as ic
import streamlit as st

from openai import OpenAI
from functools import lru_cache

# Added for streamlit
# Need to run `streamlit scripts/run.py` to start the app
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src import utils
from src import prompts
from src import personas
from src import agent
from src import tools
from src import constants
from src import run_tools as rt
from src import interfaces as itf
from src import pdf_tools as pdft
from src.database import db_access as dba

#MODEL = 'gpt-4o'
MODEL = 'gpt-4o-mini'
#MODEL = 'gpt-4o-2024-08-06'


def initialize_st_vars():
    """
    Initialize session state variables if they don't exist
    """
    # TODO - remove after testing
    st.session_state.counselor_persona = 'David - The Mentor'

    if 'messages_since_update' not in st.session_state:
        st.session_state.messages_since_update = 0
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'counselor_agent' not in st.session_state:
        st.session_state.counselor_agent = None
    if 'suny_agent' not in st.session_state:
        st.session_state.suny_agent = None
    if 'counselor_user_messages' not in st.session_state:
        st.session_state.counselor_user_messages = []
    if 'counselor_suny_messages' not in st.session_state:
        st.session_state.counselor_suny_messages = []
    if 'counselor_persona' not in st.session_state:
        st.session_state.counselor_persona = None


def initialize_counselor_agent(client: OpenAI, student_md_profile: str):

    counselor_system_prompt = prompts.COUNSELOR_SYSTEM_PROMPT

    if st.session_state.counselor_persona == 'David - The Mentor':
        persona_prompt = personas.DAVID + '\n\n' + personas.DAVID_TRAITS
    elif st.session_state.counselor_persona == 'Emma - The Strategist':
        persona_prompt = personas.EMMA + '\n\n' + personas.EMMA_TRAITS
    elif st.session_state.counselor_persona == 'Liam - The Explorer':
        persona_prompt = personas.LIAM + '\n\n' + personas.LIAM_TRAITS

    counselor_system_prompt = counselor_system_prompt.replace('{{persona}}', persona_prompt)
    counselor_system_prompt = counselor_system_prompt.replace('{{student_md_profile}}', student_md_profile)

    return agent.Agent(
        client,
        name="Counselor",
        tools=None,
        model=MODEL,
        system_prompt=counselor_system_prompt,
        json_mode=True
    )


@lru_cache(maxsize=None)
def initialize_suny_agent(client: OpenAI):
    suny_system_prompt = prompts.SUNY_SYSTEM_PROMPT + '\n'
    for name in constants.UNIVERSITY_NAMES:
        suny_system_prompt += name + '\n'

    return agent.Agent(
        client,
        name="SUNY",
        tools=tools.suny_tools,
        model=MODEL,
        system_prompt=suny_system_prompt
    )


def check_assessment_completed(user_id):
    """
    Check if the user has completed the assessment.
    """
    top_strengths = dba.get_top_strengths(user_id)
    return bool(top_strengths)


def main():
    """
    Main function to run the Streamlit app
    `streamlit run scripts/run.py`
    """

    st.set_page_config(page_title="SUNY Counselor Chat", page_icon="💬", layout="wide")
    initialize_st_vars()

    if st.session_state.user is None:
        st.session_state.user = itf.streamlit_login()

    if st.session_state.user:

        # Load the message history for both user <-> counselor and counselor <-> suny
        # TODO - should we summarize the message history so we aren't using up tokens?
        message_history = dba.load_message_history(st.session_state.user.user_id)
        for message in message_history:
            sender = message['sender']
            recipient = message['recipient']
            message_content = {'role': sender, 'content': message['message']}
            
            # Add messages between counselor and user
            if (sender, recipient) in [('counselor', 'user'), ('user', 'counselor')]:
                st.session_state.counselor_user_messages.append(message_content)

            # Add messages between counselor and suny
            elif sender == 'counselor' and recipient == 'suny':
                st.session_state.counselor_suny_messages.append(message_content)

            # Add message history to agents

        st.sidebar.success(f"Logged in as: {st.session_state.user.username}")

        if not st.session_state.user.top_strengths:
            itf.assessment_page()
        else:
            st.session_state.user.reload_all_data()
            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("Logout"):
                    rt.logout()

            itf.display_student_info(st.session_state.user.user_id)

            if st.session_state.counselor_agent is None:
                client = utils.get_openai_client()
                st.session_state.counselor_agent = initialize_counselor_agent(
                    client, st.session_state.user.student_md_profile
                )

            if st.session_state.suny_agent is None:
                client = utils.get_openai_client()
                st.session_state.suny_agent = initialize_suny_agent(client)

            itf.main_chat_interface()
    else:
        st.error("Please log in to continue")


if __name__ == "__main__":
    main()