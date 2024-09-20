"""
"""

import os
import sys
import streamlit as st

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import pickle

from src import prompts
from src.auth import login
from src.assessment import answers
from src.utils import dict_to_str, parse_json
from src.database import execute_query, get_db_connection
from src.database import insert_user_responses, insert_strengths, get_top_strengths, get_bot_strengths
from src.run_tools import process_user_input, get_student_info, update_student_info, process_transcript, type_text
from src.constants import SYSTEM_DATA_DIR

opj = os.path.join


def main_chat_interface():
    st.title("💬 User-Counselor Chat")
    st.caption("🚀 Chat with your SUNY counselor")

    if len(st.session_state.user_messages) == 1:
        first_message = st.session_state.user_messages[0]["content"]

        # Add in the first message to the counselor agent if it's not already there
        if {"role": "assistant", "content": first_message} not in st.session_state.counselor_agent.messages:
            st.session_state.counselor_agent.add_message("assistant", first_message)
            print('Added first message to counselor agent')

    chat_container = st.container()

    st.session_state.counselor_agent.print_messages()
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
        process_user_input(prompt)
        st.session_state.messages_since_update += 1

        # Force a rerun to display the new messages
        st.rerun()

    #print('Messages since update:', st.session_state.messages_since_update)
    if st.session_state.messages_since_update > 200000000:
        st.session_state.messages_since_update = 0
        print('Updating student info...')
        current_student_info = get_student_info(st.session_state.user)
        current_student_info_str = dict_to_str(current_student_info, format=False)
        print('CURRENT STUDENT INFO')
        print(current_student_info_str)
        new_info_prompt = prompts.UPDATE_INFO_PROMPT
        new_info_prompt += f"\n**Student's Current Information:**\n{current_student_info_str}\n\n"
        new_info_prompt += f"**Conversation History:**\n{st.session_state.user_messages}\n\n"
        print('NEW INFO PROMPT')
        print(new_info_prompt, '\n')
        response = st.session_state.counselor_agent.client.chat.completions.create(
            model='gpt-4o-2024-08-06',
            messages=[
                {"role": "assistant", "content": new_info_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        ).choices[0].message.content

        print('\n')
        print('UPDATE INFO RESPONSE')
        print(response, '\n')

        response_json = parse_json(response)
        for key, value in response_json.items():
            if key in current_student_info:
                current_student_info[key] = value
        
        update_student_info(st.session_state.user, current_student_info)

        # Update the counselor agent's system prompt
        student_info = get_student_info(st.session_state.user)
        student_info_str = dict_to_str(current_student_info, format=False)
        st.session_state.counselor_agent.update_system_prompt(prompts.COUNSELOR_SYSTEM_PROMPT + student_info_str)

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
        
    top_strengths = get_top_strengths(user)
    bot_strengths = get_bot_strengths(user)

    # Display Strengths
    st.sidebar.markdown("---")
    st.sidebar.subheader("Top 5 Strengths")
    for theme, score, strength_level in top_strengths:
        st.sidebar.text(f"{theme}: {score} ({strength_level})")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Top 5 Weaknesses")
    for theme, score, strength_level in bot_strengths:
        st.sidebar.text(f"{theme}: {score} ({strength_level})")

    # Add transcript upload button to sidebar
    st.sidebar.markdown("---")  # Add a separator
    st.sidebar.subheader("Upload Transcript")
    uploaded_file = st.sidebar.file_uploader("Choose a file", type=["csv", "xlsx", "pdf", "txt"])
    if uploaded_file is not None:
        process_transcript(uploaded_file)


def first_time_user_page():
    responses_file = 'saved_responses.pkl'

    st.title("Welcome to SUNY Counselor Chat!")
    st.write("As this is your first time using our service, we'd like you to complete a brief assessment.")

    st.subheader("Strengths Assessment")
    st.write("Rate each statement on a scale of 1 to 5:")
    st.write("1 = Strongly Disagree, 2 = Disagree, 3 = Neutral, 4 = Agree, 5 = Strongly Agree")

    user_responses = {}

    with st.form("strengths_form"):
        submit = st.form_submit_button("Submit")

        # Fetch questions from the database
        questions = execute_query("SELECT themes.theme_name, questions.statement FROM questions JOIN themes ON questions.theme_id = themes.theme_id;")

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

        print('USER RESPONSES')
        print(user_responses)
        print('THEME SCORES')
        print(theme_scores)

        insert_user_responses(st.session_state.user.user_id, user_responses)
        insert_strengths(st.session_state.user.user_id, theme_scores)

        st.session_state.first_time_completed = True
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
    if "user" not in st.session_state:

        # Temp while testing
        #username = 'cameron'
        #password = 'fabbri'

        #user = login(username, password)
        user = None
        if user is not None:
            st.session_state.user = user
            st.success("Login successful")
            return user

        placeholder = st.empty()
        with placeholder.form("login"):
            st.markdown("#### Enter your credentials")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
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
