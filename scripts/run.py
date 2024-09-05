"""
"""
import os
import sys
import streamlit as st
from openai import OpenAI

# Added for streamlit
# Need to run `streamlit scripts/run.py` to start the app
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src import utils
from src import prompts
from src.tools import tools
from src.user import User, login
from src.database import ChromaDB
from src.pdf_tools import parse_pdf_with_llama
from src.agent import Agent, BLUE, GREEN, ORANGE, RESET

def streamlit_login():
    if "user" not in st.session_state:
        placeholder = st.empty()

        with placeholder.form("login"):
            st.markdown("#### Enter your credentials")
            #email = st.text_input("Email")
            #password = st.text_input("Password", type="password")
            username = 'cameron'
            password = 'fabbri'
            submit = st.form_submit_button("Login")

        if submit:
            user = login(username, password)
            if user:
                st.session_state.user = user
                placeholder.empty()
                st.success("Login successful")
                return user
            else:
                st.error("Login failed")
        return None
    return st.session_state.user


def main():
    st.set_page_config(page_title="SUNY Counselor Chat", page_icon="💬", layout="wide")

    user = streamlit_login()
    if user:
        st.sidebar.success(f"Logged in as: {user.username}")

        if "counselor_agent" not in st.session_state:
            client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
            st.session_state.counselor_agent = Agent(client, name="Counselor", tools=None, system_prompt=prompts.COUNSELOR_SYSTEM_PROMPT, json_mode=True)
            st.session_state.suny_agent = Agent(client, name="SUNY", tools=tools, system_prompt=prompts.SUNY_SYSTEM_PROMPT)
        
        if "user_messages" not in st.session_state:
            st.session_state.user_messages = [{"role": "assistant", "content": "Hello! How can I assist you with SUNY-related questions today?"}]
        
        if "counselor_suny_messages" not in st.session_state:
            st.session_state.counselor_suny_messages = []

        user_chat_column, counselor_suny_chat_column = st.columns(2)

        with user_chat_column:
            main_chat_interface()

        with counselor_suny_chat_column:
            counselor_suny_chat_interface()

    else:
        st.error("Please log in to continue")


def main_chat_interface():
    st.title("💬 User-Counselor Chat")
    st.caption("🚀 Chat with your SUNY counselor")

    #for msg in st.session_state.user_messages:
    #    st.chat_message(msg["role"]).write(msg["content"])

    #if prompt := st.chat_input("Type your message here..."):
    #    st.session_state.user_messages.append({"role": "user", "content": prompt})
    #    st.chat_message("user").write(prompt)
    #    process_user_input(prompt)
    #    st.rerun()

    chat_container = st.container()

    prompt = st.chat_input("Type your message here...")

    # Display chat messages in the container
    with chat_container:
        for msg in st.session_state.user_messages:
            st.chat_message(msg["role"]).write(msg["content"])

    # Process the user input
    if prompt:
        # Add user message to chat history
        st.session_state.user_messages.append({"role": "user", "content": prompt})

        # Process user input and get response
        process_user_input(prompt)

        # Force a rerun to display the new messages
        st.rerun()


def counselor_suny_chat_interface():
    st.title("🤖 Counselor-SUNY Chat")
    st.caption("Communication between Counselor and SUNY agents")

    for msg in st.session_state.counselor_suny_messages:
        st.chat_message(msg["role"]).write(msg["content"])


def process_user_input(prompt):
    counselor_agent = st.session_state.counselor_agent
    suny_agent = st.session_state.suny_agent

    counselor_agent.add_message("user", prompt)
    counselor_response = counselor_agent.invoke()

    if counselor_response.choices[0].message.tool_calls:
        counselor_response = counselor_agent.handle_tool_call(counselor_response)

    counselor_response_str = counselor_response.choices[0].message.content
    counselor_response_json = utils.parse_json(counselor_response_str)

    recipient = counselor_response_json.get("recipient")
    counselor_message = counselor_response_json.get("message")

    counselor_agent.add_message("assistant", counselor_response_str)

    if recipient == "suny":
        st.chat_message('assistant').write('Contacting SUNY Agent...')
        st.session_state.counselor_suny_messages.append({"role": "counselor", "content": counselor_message})
        suny_agent.add_message("user", counselor_message)
        suny_response = suny_agent.invoke()

        if suny_response.choices[0].message.tool_calls:
            suny_response = suny_agent.handle_tool_call(suny_response)

        suny_response_str = utils.format_for_json(suny_response.choices[0].message.content)
        st.session_state.counselor_suny_messages.append({"role": "suny", "content": suny_response_str})
        suny_agent.add_message("assistant", suny_response_str)

        counselor_agent.add_message("assistant", '{"recipient": "user", "message": ' + suny_response_str + '}')
        counselor_response = counselor_agent.invoke()
        counselor_response_str = counselor_response.choices[0].message.content
        counselor_response_json = utils.parse_json(counselor_response_str)
        counselor_message = counselor_response_json.get("message")

    st.session_state.user_messages.append({"role": "assistant", "content": counselor_message})

if __name__ == "__main__":
    main()