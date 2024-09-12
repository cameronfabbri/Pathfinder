"""
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
from src.personas import DAVID, EMMA, LIAM
from src.database import ChromaDB
from src.pdf_tools import parse_pdf_with_llama
from src.tools import suny_tools
from src.user import User
from src.database import execute_query, get_db_connection
from src.auth import login
from src.agent import Agent, BLUE, GREEN, ORANGE, RESET


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


def display_student_info(user):
    st.sidebar.title("Student Information")

        # Add custom CSS for text wrapping
    st.markdown("""
        <style>
        [data-testid="stSidebar"] .stText {
            word-wrap: break-word;
            white-space: pre-wrap;      
        }
        </style>
    """, unsafe_allow_html=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM students WHERE user_id='{user.user_id}';")
        student_info = cursor.fetchone()
    
    if student_info:
        info_dict = {
            'Name': f"{student_info[0]} {student_info[1]}",
            'Age': student_info[5],
            'Gender': student_info[6],
            'Ethnicity': student_info[7],
            'High School': student_info[8],
            'Graduation Year': student_info[9],
            'GPA': student_info[10],
            'Favorite Subjects': student_info[13],
            'Extracurriculars': student_info[14],
            'Career Aspirations': student_info[15],
            'Preferred Major': student_info[16],
            'Intended College': student_info[23],
            'Intended Major': student_info[24]
        }
        
        for key, value in info_dict.items():
            st.sidebar.text(f"{key}: {value}")

    # Add transcript upload button to sidebar
    st.sidebar.markdown("---")  # Add a separator
    st.sidebar.subheader("Upload Transcript")
    uploaded_file = st.sidebar.file_uploader("Choose a file", type=["csv", "xlsx", "pdf", "txt"])
    if uploaded_file is not None:
        process_transcript(uploaded_file) 


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
    else:
        counselor_response_str = counselor_response.choices[0].message.content
        counselor_response_json = utils.parse_json(counselor_response_str)

        recipient = counselor_response_json.get("recipient")
        counselor_message = counselor_response_json.get("message")

        counselor_agent.add_message("assistant", counselor_response_str)

        if recipient == "suny":
            #st.chat_message('assistant').write('Contacting SUNY Agent...')
            st.session_state.counselor_suny_messages.append({"role": "counselor", "content": counselor_message})
            suny_agent.add_message("user", counselor_message)
            suny_response = suny_agent.invoke()

            if suny_response.choices[0].message.tool_calls:
                suny_response = suny_agent.handle_tool_call(suny_response)

            print('SUNY RESPONSE')
            print(suny_response)

            suny_response_str = utils.format_for_json(suny_response.choices[0].message.content)
            st.session_state.counselor_suny_messages.append({"role": "suny", "content": suny_response_str})
            suny_agent.add_message("assistant", suny_response_str)

            counselor_agent.add_message("assistant", '{"recipient": "user", "message": ' + suny_response_str + '}')
            counselor_response = counselor_agent.invoke()
            counselor_response_str = counselor_response.choices[0].message.content
            counselor_response_json = utils.parse_json(counselor_response_str)
            counselor_message = counselor_response_json.get("message")

        st.session_state.user_messages.append({"role": "assistant", "content": counselor_message})


def main_chat_interface():
    st.title("💬 User-Counselor Chat")
    st.caption("🚀 Chat with your SUNY counselor")

    #persona = None#display_counselor_options()

    #if persona:
    #    if persona == "David - The Mentor":
    #        st.info(DAVID)
    #    elif persona == "Emma - The Strategist":
    #        st.info(EMMA)
    #    elif persona == "Liam - The Explorer":
    #        st.info(LIAM)

    if len(st.session_state.user_messages) == 1:
        first_message = st.session_state.user_messages[0]["content"]

        # Add in the first message to the counselor agent if it's not already there
        if {"role": "assistant", "content": first_message} not in st.session_state.counselor_agent.messages:
            st.session_state.counselor_agent.add_message("assistant", first_message)

    chat_container = st.container()

    prompt = st.chat_input("Type your message here...")
    
    # Display chat messages in the container
    #pdf_path = '/Users/cameronfabbri/canton/www.canton.edu/media/pdf/campus_map.pdf'
    with chat_container:
        #with open(pdf_path, "rb") as pdf_file:
        #    pdf_content = pdf_file.read()
        #pdf_viewer(pdf_content, width=1000, height=700)
        #for msg in st.session_state.user_messages:
        #    content = msg.get('content').replace('\n', ' ')
        #    st.chat_message(msg["role"]).write(content)
        for msg in st.session_state.user_messages:
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                if isinstance(msg['content'], str):
                    st.chat_message(msg["role"]).write(msg["content"])
            else:
                print(f"Debug: Skipping invalid message format: {msg}")

    #st.session_state.messages_since_update += 1
    #print('MESSAGES SINCE UPDATE:', st.session_state.messages_since_update)
    #print('\n\n--------------START COUNSELOR MESSAGES--------------')
    #[print(x) for x in st.session_state.counselor_agent.messages]
    #print('---------------END COUNSELOR MESSAGES---------------')
    #print('\n\n--------------START STREAMLIT MESSAGES--------------')
    #[print(x) for x in st.session_state.user_messages]
    #print('---------------END STREAMLIT MESSAGES---------------')

    # Process the user input
    if prompt:
        # Add user message to chat history
        st.session_state.user_messages.append({"role": "user", "content": prompt})

        # Process user input and get response
        process_user_input(prompt)

        # Force a rerun to display the new messages
        st.rerun()

    st.session_state.messages_since_update += 1
    print('Messages since update:', st.session_state.messages_since_update)
    if st.session_state.messages_since_update > 3:
        st.session_state.messages_since_update = 0
        print('Updating student info...')
        current_student_info = get_student_info(st.session_state.user)
        current_student_info_str = utils.dict_to_str(current_student_info)
        print('CURRENT STUDENT INFO')
        print(current_student_info_str)
        new_info_prompt = prompts.UPDATE_INFO_PROMPT
        new_info_prompt += f"\n**Student's Current Information:**\n{current_student_info_str}\n\n"
        new_info_prompt += f"**Conversation History:**\n{st.session_state.user_messages}\n\n"
        print('NEW INFO PROMPT')
        print(new_info_prompt, '\n')
        response = st.session_state.counselor_agent.client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "assistant", "content": new_info_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        ).choices[0].message.content

        print('\n')
        print('UPDATE INFO RESPONSE')
        print(response, '\n')

        response_json = utils.parse_json(response)
        for key, value in response_json.items():
            if key in current_student_info:
                current_student_info[key] = value
        
        update_student_info(st.session_state.user, current_student_info)


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
        model='gpt-4o',
        messages=[
            {"role": "assistant", "content": prompt},
        ],
        temperature=0.0
    )
    first_message = response.choices[0].message.content
    return first_message


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
        #'clifton_strengths': student_info[17],
        #'personality_test_results': student_info[18],
        'address': student_info[19],
        'city': student_info[20],
        'state': student_info[21],
        'zip_code': student_info[22],
        'intended_college': student_info[23],
        'intended_major': student_info[24],
    }


def main():
    st.set_page_config(page_title="SUNY Counselor Chat", page_icon="💬", layout="wide")

    if 'messages_since_update' not in st.session_state:
        st.session_state.messages_since_update = 0

    user = streamlit_login()

    if user:

        col1, col2, col3 = st.columns([1,1,1])
        with col3:
            if st.button("Logout"):
                logout()

        st.sidebar.success(f"Logged in as: {user.username}")
        display_student_info(user)

        student_info_str = utils.dict_to_str(get_student_info(user))

        if "counselor_agent" not in st.session_state:
            client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
            st.session_state.counselor_agent = Agent(
                client,
                name="Counselor",
                tools=None,
                model='gpt-4o-mini',
                system_prompt=prompts.COUNSELOR_SYSTEM_PROMPT + student_info_str,
                json_mode=True
            )
            st.session_state.suny_agent = Agent(
                client,
                name="SUNY",
                tools=suny_tools,
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


def display_counselor_options():
    st.subheader("Choose your counselor!")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.image("data/david.jpg", width=150)
    with col2:
        st.image("data/emma.jpg", width=150)
    with col3:
        st.image("data/liam.jpg", width=150)

    return st.radio(
        "Counselor Selection",
        ("David - The Mentor", "Emma - The Strategist", "Liam - The Explorer"),
        horizontal=True,
        label_visibility="collapsed",
        index=None
    )


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
    execute_query(query, tuple(list(student_info.values()) + [st.session_state.user.user_id]))

if __name__ == "__main__":
    main()