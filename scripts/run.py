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
from src.agent import Agent
from src.tools import suny_tools
from src.database import ChromaDB
from src.run_tools import get_student_info
from src.pdf_tools import parse_pdf_with_llama
from src.database import execute_query, get_top_strengths, get_bot_strengths
from src.interfaces import streamlit_login, display_student_info, main_chat_interface, counselor_suny_chat_interface, first_time_user_page


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


def main():
    st.set_page_config(page_title="SUNY Counselor Chat", page_icon="💬", layout="wide")

    if 'messages_since_update' not in st.session_state:
        st.session_state.messages_since_update = 0

    user = streamlit_login()

    if user:
        if user.login_number == 0 and 'first_time_completed' not in st.session_state:
            first_time_user_page()
        else:
            col1, col2, col3 = st.columns([1,1,1])
            with col3:
                if st.button("Logout"):
                    logout()

            st.sidebar.success(f"Logged in as: {user.username}")
            display_student_info(user)

            student_info_str = utils.dict_to_str(get_student_info(user), format=False)

            if "counselor_agent" not in st.session_state:
                client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
                counselor_system_prompt = prompts.COUNSELOR_SYSTEM_PROMPT + student_info_str

                top_strengths = get_top_strengths(user)
                bot_strengths = get_bot_strengths(user)
                strengths_prompt = '**Strengths from Assessment:**\n'
                for theme, score, strength_level in top_strengths:
                    strengths_prompt += f"{theme}: {score} ({strength_level})\n"

                weaknesses_prompt = '\n\n**Weaknesses from Assessment:**\n'
                for theme, score, strength_level in bot_strengths:
                    weaknesses_prompt += f"{theme}: {score} ({strength_level})\n"

                counselor_system_prompt += '\n\n' + strengths_prompt + weaknesses_prompt

                print('COUNSELOR SYSTEM PROMPT')
                print(counselor_system_prompt)

                st.session_state.counselor_agent = Agent(
                    client,
                    name="Counselor",
                    tools=None,
                    model='gpt-4o-2024-08-06',
                    system_prompt=counselor_system_prompt,
                    json_mode=True
                )
                st.session_state.suny_agent = Agent(
                    client,
                    name="SUNY",
                    tools=suny_tools,
                    model='gpt-4o-2024-08-06',
                    system_prompt=prompts.SUNY_SYSTEM_PROMPT
                )

                #log_messages('counselor', st.session_state.counselor_agent.messages)
                #log_messages('suny', st.session_state.suny_agent.messages)
            
            if "user_messages" not in st.session_state:
                if user.login_number == 0:
                    first_message = prompts.WELCOME_MESSAGE
                else:
                    try:
                        first_message = get_chat_summary_from_db(client)
                    except:
                        print('\nNo chat summary found in database, did you quit without logging out?\n')
                        first_message = prompts.WELCOME_MESSAGE
                st.session_state.user_messages = [{"role": "assistant", "content": first_message}]
            
            if "counselor_suny_messages" not in st.session_state:
                st.session_state.counselor_suny_messages = []

            user_chat_column, counselor_suny_chat_column = st.columns(2)

            with user_chat_column:
                main_chat_interface()

            with counselor_suny_chat_column:
                counselor_suny_chat_interface()

    else:
        st.error("Please log in to continue")


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



if __name__ == "__main__":
    main()