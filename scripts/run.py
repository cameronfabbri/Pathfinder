"""
Main script
"""
# Cameron Fabbri

import os
import sys
import streamlit as st
from icecream import ic

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
from src.user import UserProfile
from src.database import db_setup as dbs
from src.database import db_access as dba

MODEL = 'gpt-4o'
#MODEL = 'gpt-4o-mini'
#MODEL = 'gpt-4o-2024-08-06'


def initialize_st_vars() -> None:
    """
    Initialize session state variables if they don't exist
    """

    st.session_state.counselor_persona = 'David - The Mentor'

    if 'messages_since_update' not in st.session_state:
        st.session_state.messages_since_update = 0
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'counselor_agent' not in st.session_state:
        st.session_state.counselor_agent = None
    if 'suny_agent' not in st.session_state:
        st.session_state.suny_agent = None
    if 'counselor_persona' not in st.session_state:
        st.session_state.counselor_persona = None
    if 'is_new_session' not in st.session_state:
        st.session_state.is_new_session = True
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None


def initialize_counselor_agent(client: OpenAI, student_md_profile: str) -> agent.Agent:
    """
    Initialize the counselor agent
    """
    counselor_system_prompt = rt.build_counselor_prompt(student_md_profile)

    return agent.Agent(
        client,
        name="Counselor",
        tools=None,
        model=MODEL,
        system_prompt=counselor_system_prompt,
        json_mode=True
    )


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
    top_strengths, _ = dba.get_topbot_strengths(user_id, k=1)
    ic(top_strengths)
    return bool(top_strengths)


def main():
    """
    Main function to run the Streamlit app
    `streamlit run scripts/run.py`
    """

    os.makedirs(constants.SQL_DB_DIR, exist_ok=True)
    dbs.create_auth_tables()

    st.set_page_config(page_title="SUNY Counselor Chat", page_icon="💬", layout="wide")
    initialize_st_vars()

    if st.session_state.user is None:
        st.session_state.user = itf.streamlit_login()

    if not st.session_state.user:
        st.error("Please log in to continue")
        return 

    st.sidebar.success(f"Logged in as: {st.session_state.user.username}")

    # If the assessment isn't finished
    if not check_assessment_completed(st.session_state.user.user_id):
        itf.assessment_page()
    else:
        st.session_state.user_profile = UserProfile(st.session_state.user.user_id)
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("Logout"):
                rt.logout()

        itf.display_student_info(st.session_state.user_profile)

        if st.session_state.counselor_agent is None:
            client = utils.get_openai_client()
            st.session_state.counselor_agent = initialize_counselor_agent(
                client, st.session_state.user_profile.student_md_profile
            )

        if st.session_state.suny_agent is None:
            client = utils.get_openai_client()
            st.session_state.suny_agent = initialize_suny_agent(client)

        # Load the message history for both user <-> counselor and counselor <-> suny
        # TODO - should we summarize the message history so we aren't using up tokens?
        if st.session_state.is_new_session:
            rt.load_message_history()
            st.session_state.is_new_session = False

        itf.main_chat_interface()


if __name__ == "__main__":
    main()