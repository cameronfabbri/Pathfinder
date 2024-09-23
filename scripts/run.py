"""
Main script
"""
import os
import sys
import streamlit as st

from openai import OpenAI
from streamlit_pdf_viewer import pdf_viewer

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
from src.interfaces import streamlit_login, display_student_info, main_chat_interface, counselor_suny_chat_interface, first_time_user_page, display_counselor_options

DEBUG = False
MODEL = 'gpt-4o'
MODEL = 'gpt-4o-mini'
MODEL = 'gpt-4o-2024-08-06'

def main():
    """
    Main function to run the Streamlit app
    `streamlit run scripts/run.py`
    """
    st.set_page_config(page_title="SUNY Counselor Chat", page_icon="💬", layout="wide")

    if 'messages_since_update' not in st.session_state:
        st.session_state.messages_since_update = 0

    user = streamlit_login()

    if user:

        top_strengths = get_top_strengths(user.user_id)
        bot_strengths = get_bot_strengths(user.user_id)

        if not top_strengths:
            first_time_user_page()
        else:

            # TODO - remove after testing
            st.session_state.counselor_persona = 'David - The Mentor'

            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("Logout"):
                    logout()

            st.sidebar.success(f"Logged in as: {user.username}")
            display_student_info(user.user_id)

            student_info_str = utils.dict_to_str(get_student_info(user.user_id), format=False)

            if "counselor_agent" not in st.session_state:
                client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
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

                st.session_state.counselor_agent = Agent(
                    client,
                    name="Counselor",
                    tools=None,
                    model=MODEL,
                    system_prompt=counselor_system_prompt,
                    json_mode=True
                )

                suny_system_prompt = prompts.SUNY_SYSTEM_PROMPT + '\n'
                for name in UNIVERSITY_MAPPING.values():
                    suny_system_prompt += name + '\n'

                st.session_state.suny_agent = Agent(
                    client,
                    name="SUNY",
                    tools=suny_tools,
                    model=MODEL,
                    system_prompt=suny_system_prompt
                )

            if "user_messages" not in st.session_state:
                print('user.session_id:', user.session_id)
                if user.session_id == 0:
                    if not DEBUG:
                        first_message = utils.parse_json(
                            st.session_state.counselor_agent.invoke().choices[0].message.content
                        )['message']
                    else:
                        first_message = prompts.DEBUG_FIRST_MESSAGE.replace('NAME', user.username)
                else:
                    try:
                        first_message = get_chat_summary_from_db(client)
                    except:
                        print('\nNo chat summary found in database, did you quit without logging out?\n')
                        first_message = f"Hello {user.username}, welcome back to the chat!"
                st.session_state.user_messages = [{"role": "assistant", "content": first_message}]
                st.session_state.counselor_agent.add_message("assistant", first_message)
            
            if "counselor_suny_messages" not in st.session_state:
                st.session_state.counselor_suny_messages = []

            with col1:
                main_chat_interface()

    else:
        st.error("Please log in to continue")



if __name__ == "__main__":
    main()