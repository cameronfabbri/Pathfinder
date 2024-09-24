"""
Main script
"""
import os
import sys
import streamlit as st

from openai import OpenAI
from streamlit_pdf_viewer import pdf_viewer
from functools import lru_cache

# Added for streamlit
# Need to run `streamlit scripts/run.py` to start the app
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src import utils
from src import prompts
from src import personas
from src.agent import Agent
from src.tools import suny_tools
from src.constants import UNIVERSITY_MAPPING
from src.database import get_top_strengths, get_bot_strengths
from src.run_tools import get_student_info, get_chat_summary_from_db, logout
from src.interfaces import streamlit_login, display_student_info, main_chat_interface, assessment_page

DEBUG = False
#MODEL = 'gpt-4o'
MODEL = 'gpt-4o-mini'
#MODEL = 'gpt-4o-2024-08-06'


def initialize_st_vars():
    """
    Initialize session state variables if they don't exist
    """

    if 'messages_since_update' not in st.session_state:
        st.session_state.messages_since_update = 0
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'counselor_agent' not in st.session_state:
        st.session_state.counselor_agent = None
    if 'suny_agent' not in st.session_state:
        st.session_state.suny_agent = None
    if 'user_messages' not in st.session_state:
        st.session_state.user_messages = []
    if 'counselor_suny_messages' not in st.session_state:
        st.session_state.counselor_suny_messages = []
    if 'counselor_persona' not in st.session_state:
        st.session_state.counselor_persona = None


@lru_cache(maxsize=None)
def get_openai_client():
    return OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))


def initialize_counselor_agent(client: OpenAI, student_info_str: str, top_strengths: list, bot_strengths: list):

    counselor_system_prompt = prompts.COUNSELOR_SYSTEM_PROMPT + student_info_str

    strengths_prompt = '**Strengths from Assessment:**\n'
    for theme, score, strength_level in top_strengths:
        strengths_prompt += f"{theme}: {score} ({strength_level})\n"

    weaknesses_prompt = '\n\n**Weaknesses from Assessment:**\n'
    for theme, score, strength_level in bot_strengths:
        weaknesses_prompt += f"{theme}: {score} ({strength_level})\n"

    counselor_system_prompt += '\n\n' + strengths_prompt + weaknesses_prompt

    if st.session_state.counselor_persona == 'David - The Mentor':
        persona_prompt = personas.DAVID + '\n\n' + personas.DAVID_TRAITS
    elif st.session_state.counselor_persona == 'Emma - The Strategist':
        persona_prompt = personas.EMMA + '\n\n' + personas.EMMA_TRAITS
    elif st.session_state.counselor_persona == 'Liam - The Explorer':
        persona_prompt = personas.LIAM + '\n\n' + personas.LIAM_TRAITS

    counselor_system_prompt = counselor_system_prompt.replace('PERSONA', persona_prompt)

    return Agent(
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
    for name in UNIVERSITY_MAPPING.values():
        suny_system_prompt += name + '\n'

    return Agent(
        client,
        name="SUNY",
        tools=suny_tools,
        model=MODEL,
        system_prompt=suny_system_prompt
    )


def main():
    """
    Main function to run the Streamlit app
    `streamlit run scripts/run.py`
    """
    st.set_page_config(page_title="SUNY Counselor Chat", page_icon="💬", layout="wide")

    initialize_st_vars()

    if st.session_state.user is None:
        st.session_state.user = streamlit_login()

    if st.session_state.user:

        top_strengths = get_top_strengths(st.session_state.user.user_id)
        bot_strengths = get_bot_strengths(st.session_state.user.user_id)

        if not top_strengths or not bot_strengths:
            assessment_page()
        else:

            # TODO - remove after testing
            st.session_state.counselor_persona = 'David - The Mentor'

            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("Logout"):
                    logout()

            st.sidebar.success(f"Logged in as: {st.session_state.user.username}")
            display_student_info(st.session_state.user.user_id)

            if st.session_state.counselor_agent is None:
                client = get_openai_client()
                student_info_str = utils.dict_to_str(get_student_info(st.session_state.user.user_id), format=False)
                st.session_state.counselor_agent = initialize_counselor_agent(client, student_info_str, top_strengths, bot_strengths)

            if st.session_state.suny_agent is None:
                client = get_openai_client()
                st.session_state.suny_agent = initialize_suny_agent(client)

            if not st.session_state.user_messages:
                if st.session_state.user.session_id == 0:
                    if not DEBUG:
                        first_message = utils.parse_json(
                            st.session_state.counselor_agent.invoke().choices[0].message.content
                        )['message']
                    else:
                        first_message = prompts.DEBUG_FIRST_MESSAGE.replace('NAME', st.session_state.user.username)
                else:
                    try:
                        first_message = get_chat_summary_from_db(st.session_state.user.user_id)
                    except:
                        print('\nNo chat summary found in database, did you quit without logging out?\n')
                        first_message = f"Hello {st.session_state.user.username}, welcome back to the chat!"
                st.session_state.user_messages = [{"role": "assistant", "content": first_message}]
                st.session_state.counselor_agent.add_message("assistant", first_message)
            
            if not st.session_state.counselor_suny_messages:
                st.session_state.counselor_suny_messages = []

            with col1:
                main_chat_interface()

    else:
        st.error("Please log in to continue")



if __name__ == "__main__":
    main()