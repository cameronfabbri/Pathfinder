"""
"""

import os
import sys
import streamlit as st

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import pickle

from src import auth
from src import agent
from src import utils
from src import prompts
from src import run_tools as rt
from src.assessment import answers
from src.database import db_access as dba
from src.constants import SYSTEM_DATA_DIR

opj = os.path.join


def main_chat_interface():
    st.title("💬 User-Counselor Chat")
    st.caption("🚀 Chat with your SUNY counselor")

    #st.session_state.counselor_agent.print_messages()

    if len(st.session_state.user_messages) == 1:
        first_message = st.session_state.user_messages[0]["content"]

        # Add in the first message to the counselor agent if it's not already there
        if {"role": "assistant", "content": first_message} not in st.session_state.counselor_agent.messages:
            st.session_state.counselor_agent.add_message("assistant", first_message)
            print('Added first message to counselor agent')

    chat_container = st.container()

    #st.session_state.counselor_agent.print_messages()
    prompt = st.chat_input("Type your message here...")
    
    # Display chat messages in the container
    with chat_container:
        for msg in st.session_state.user_messages:
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                if isinstance(msg['content'], str):
                    st.chat_message(msg["role"]).write(msg["content"])
            else:
                print(f"Debug: Skipping invalid message format: {msg}")

    if prompt:

        # Add user message to session
        st.session_state.user_messages.append({"role": "user", "content": prompt})

        # Process user input and get response
        rt.process_user_input(prompt)
        st.session_state.messages_since_update += 1

        # Force a rerun to display the new messages
        st.rerun()

    si = st.session_state.user.student_info.values()
    nsi = None in si or 'None' in si
    if st.session_state.messages_since_update > 2 and nsi:
        print('Updating student info...')
        st.session_state.messages_since_update = 0
        current_student_info = dba.get_student_info(st.session_state.user.user_id)
        current_student_info_str = utils.dict_to_str(current_student_info, format=False)
        new_info_prompt = prompts.UPDATE_INFO_PROMPT
        new_info_prompt += f"\n**Student's Current Information:**\n{current_student_info_str}\n\n"
        new_info_prompt += f"**Conversation History:**\n{st.session_state.user_messages}\n\n"
        response = st.session_state.counselor_agent.client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "assistant", "content": new_info_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        ).choices[0].message.content

        response_json = utils.parse_json(response)
        for key, value in response_json.items():
            if key in current_student_info:
                current_student_info[key] = value
        
        dba.update_student_info(st.session_state.user.user_id, current_student_info)

        # Load new info into the user object
        st.session_state.user.reload_all_data()
        #student_info = dba.get_student_info(st.session_state.user.user_id)
        #student_info_str = utils.dict_to_str(student_info, format=False)
        #st.session_state.counselor_agent.update_system_prompt(prompts.COUNSELOR_SYSTEM_PROMPT + student_info_str)
        # Update the counselor agent's system prompt
        st.session_state.counselor_agent.system_prompt = prompts.COUNSELOR_SYSTEM_PROMPT.replace(
            '{{student_md_profile}}', st.session_state.user.student_md_profile
        )
        print('NEW COUNSELOR SYSTEM PROMPT:')
        print(st.session_state.counselor_agent.system_prompt)

        st.rerun()


def display_student_info(user_id: int):
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

    student_info = dba.get_student_info(user_id)
 
    if student_info:
        for key, value in student_info.items():
            st.sidebar.text(f"{key}: {value}")
        
    #top_strengths = dba.get_top_strengths(user_id)
    #bot_strengths = dba.get_bot_strengths(user_id)

    # Display Strengths
    st.sidebar.markdown("---")
    st.sidebar.subheader("Top 5 Strengths")
    for theme, score, strength_level in st.session_state.user.top_strengths:
        st.sidebar.text(f"{theme}: {score} ({strength_level})")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Top 5 Weaknesses")
    for theme, score, strength_level in st.session_state.user.bot_strengths:
        st.sidebar.text(f"{theme}: {score} ({strength_level})")

    # Add transcript upload button to sidebar
    st.sidebar.markdown("---")  # Add a separator
    st.sidebar.subheader("Upload File")
    uploaded_file = st.sidebar.file_uploader("Choose a file", type=["csv", "xlsx", "pdf", "txt"])
    if uploaded_file is not None:
        document_type = st.sidebar.selectbox("Select Document Type", ["Transcript", "SAT Score", "ACT Score", "Certification", "Other"])
        if st.sidebar.button("Process File"):
            rt.process_uploaded_file(uploaded_file, document_type, user_id)
            st.sidebar.success("File processed successfully!")
    """

    st.subheader("Upload File")
    uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "pdf", "txt"])
    if uploaded_file is not None:
        document_type = st.selectbox("Select Document Type", ["Transcript", "SAT Score", "ACT Score", "Certification", "Other"])
        if st.button("Process File"):
            rt.process_uploaded_file(uploaded_file, document_type, user_id)
            st.success("File processed successfully!")
    st.markdown("---")  # Add a separator
    """


def assessment_page():

    responses_file = 'saved_responses.pkl'

    st.title("Welcome to SUNY Counselor Chat!")
    st.write("As this is your first time using our service, we'd like you to complete a brief assessment.")

    st.subheader("Strengths Assessment")
    st.write("Rate each statement on a scale of 1 to 5:")
    st.write("1 = Strongly Disagree, 2 = Disagree, 3 = Neutral, 4 = Agree, 5 = Strongly Agree")

    user_responses = {}

    with st.form("strengths_form"):
        submit = st.form_submit_button("Submit BUTTON")

        # Fetch questions from the database
        questions = dba.execute_query("SELECT themes.theme_name, questions.statement FROM questions JOIN themes ON questions.theme_id = themes.theme_id;")

        # Group questions by theme
        theme_questions = {}
        for theme, question in questions:
            if theme not in theme_questions:
                theme_questions[theme] = []
            theme_questions[theme].append(question)

        # Display questions for each theme
        for theme, questions in theme_questions.items():
            st.subheader(theme)
            for question in questions:
                response = st.radio(
                    question,
                    options=[1, 2, 3, 4, 5],
                    format_func=lambda x: f"{x} - {['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'][x-1]}",
                    index=None
                )
                user_responses[question] = response
    
        user_responses = answers

    if submit:
        if None in user_responses.values():
            # Load saved responses if they exist
            user_responses = {}
            theme_scores = {}
            if os.path.exists(responses_file):
                with open(responses_file, 'rb') as f:
                    saved_data = pickle.load(f)
                    user_responses = saved_data['user_responses']
                    theme_scores = saved_data['theme_scores']
                st.success("Loaded saved responses for testing.")
            #st.error("Please answer all questions before submitting.")

        # Calculate theme scores
        theme_scores = {}
        for theme, questions in theme_questions.items():
            theme_score = sum(user_responses[q] for q in questions)
            theme_scores[theme] = theme_score

        # Save responses to pickle file
        with open(responses_file, 'wb') as f:
            pickle.dump({'user_responses': user_responses, 'theme_scores': theme_scores}, f)

        # Insert user assessment responses into the database
        dba.insert_user_responses(st.session_state.user.user_id, user_responses)

        #  Insert strengths and weaknesses into the database
        dba.insert_strengths(st.session_state.user.user_id, theme_scores)

        # Load the assessment responses from the database into the user object
        st.session_state.user.load_assessment_responses()

        # Load the strengths and weaknesses from the database into the user object
        st.session_state.user.load_topbot_strengths()

        if 0:
            # Insert summary into the database
            prompt = '**Strengths Finders Assessment Test**\n'
            for question, answer in st.session_state.user.assessment_responses:
                prompt += f'{question}: {answer}\n'
            response = agent.quick_call(
                model='gpt-4o-mini',
                system_prompt=prompts.SUMMARIZE_ASSESSMENT_PROMPT,
                user_prompt=prompt,
                json_mode=False
            )
        else:
            response = prompts.TEMP_RESPONSE 

        conn = dba.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO student_summaries (user_id, summary) VALUES (?, ?)',
            (st.session_state.user.user_id, response)
        )
        conn.commit()

        #print('Response:', response)

        # Reload all user data
        st.session_state.user.reload_all_data()

        st.rerun()


def display_counselor_options():
    st.subheader("Choose your counselor")

    from src.personas import DAVID_WELCOME_MESSAGE, EMMA_WELCOME_MESSAGE, LIAM_WELCOME_MESSAGE
    from src.run_tools import type_text

    col1, col2, col3 = st.columns(3)

    with col1:
        st.image(opj(SYSTEM_DATA_DIR, 'counselors/david.jpg'), width=150)
    with col2:
        st.image(opj(SYSTEM_DATA_DIR, 'counselors/emma.jpg'), width=150)
    with col3:
        st.image(opj(SYSTEM_DATA_DIR, 'counselors/liam.jpg'), width=150)

    def on_counselor_select():
        if st.session_state.counselor_select != st.session_state.previous_counselor:
            st.session_state.previous_counselor = st.session_state.counselor_select
            st.session_state.show_welcome_message = True

    persona = st.radio(
        "Select your counselor",
        ("David - The Mentor", "Emma - The Strategist", "Liam - The Explorer"),
        horizontal=True,
        label_visibility="collapsed",
        index=None,
        key="counselor_select",
        on_change=on_counselor_select
    )

    if "show_welcome_message" not in st.session_state:
        st.session_state.show_welcome_message = False
    if "previous_counselor" not in st.session_state:
        st.session_state.previous_counselor = None

    if st.session_state.show_welcome_message and persona:
        welcome_message = ""
        if persona == "David - The Mentor":
            welcome_message = DAVID_WELCOME_MESSAGE
        elif persona == "Emma - The Strategist":
            welcome_message = EMMA_WELCOME_MESSAGE
        elif persona == "Liam - The Explorer":
            welcome_message = LIAM_WELCOME_MESSAGE
        
        if welcome_message:
            type_text(welcome_message, char_speed=0.00001)
        st.session_state.show_welcome_message = False

    with st.form("counselor_form"):
        submit = st.form_submit_button("Select")

    print('PERSONA', persona)
    if submit and persona:
        st.session_state.counselor_persona = persona
        st.session_state.counselor_chosen = True
        st.rerun()


def streamlit_login():
    """
    Handles user login and signup using Streamlit interface.
    """
    login_placeholder = st.empty()

    # Create tabs for Login and Signup
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        with st.form("login_form"):
            st.markdown("#### Login")
            username = st.text_input("Username", value='test')
            password = st.text_input("Password", type="password", value='test')
            login_submit = st.form_submit_button("Login")

        if login_submit:
            user = auth.login(username, password)
            if user:
                st.session_state.user = user
                login_placeholder.empty()
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Login failed")

    with signup_tab:
        with st.form("signup_form"):
            st.markdown("#### Sign Up")
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            age = st.number_input("Age", min_value=1, max_value=100)
            gender = st.selectbox("Gender", options=["Male", "Female", "Other"])
            new_username = st.text_input("Choose a Username")
            new_password = st.text_input("Choose a Password", type="password")
            signup_submit = st.form_submit_button("Sign Up")

        if signup_submit:
            if first_name and last_name and new_username and new_password:
                user = auth.signup(first_name, last_name, age, gender, new_username, new_password)
                if user:
                    st.session_state.user = user
                    login_placeholder.empty()
                    st.success("Sign up successful. You are now logged in.")
                    st.rerun()
                else:
                    st.error("Sign up failed. Username may already exist.")
            else:
                st.error("Please fill in all fields to sign up.")

    return st.session_state.user


def counselor_suny_chat_interface():
    st.title("🤖 Counselor-SUNY Chat")
    st.caption("Communication between Counselor and SUNY agents")

    for msg in st.session_state.counselor_suny_messages:
        st.chat_message(msg["role"]).write(msg["content"])
