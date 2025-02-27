"""
File holding the main Streamlit interface.
"""
# Cameron Fabbri
import os
import sys
import json
import pickle

import streamlit_chat
import streamlit as st

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src import agent, auth, prompts, run_tools as rt, utils
from src.user import UserProfile
from src.agent import Message
from src.database import db_access as dba
from src.constants import (COUNSELOR_AVATAR_STYLE, STUDENT_AVATAR_STYLE,
                           SYSTEM_DATA_DIR)
from src.assessment import answers

opj = os.path.join


def move_focus() -> None:
    """
    Move the focus to the chat input area.
    """
    st.components.v1.html(
        f"""
            <script>
                var textarea = window.parent.document.querySelectorAll("textarea[type=textarea]");
                for (var i = 0; i < textarea.length; ++i) {{
                    textarea[i].focus();
                }}
            </script>
        """,
    )


def place_header() -> None:
    """
    Place the header at the top of the page with no extra gap.
    """
    st.markdown(
        """
        <div class='fixed-header'></div>
        <style>
            /* Adjust positioning of the header */
            div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
                position: sticky;
                top: 0;
                background-color: #0e1118;
                z-index: 9999; /* Ensure header is above all other elements */
                margin: 0;
                padding: 0;
            }
            .fixed-header {
                border-bottom: 1px solid black;
                margin: 0;
                padding: 0;
            }
            .chat-container {
                height: 400px;
                overflow-y: auto;
                margin-top: 0; /* Ensure no gap below header */
            }
        </style>
        """,
        unsafe_allow_html=True
    )


# TODO: pass in session state as a parameter
def main_chat_interface() -> None:
    """
    The main chat interface.
    """
    place_header()
    st.markdown(
        """
        <div class='fixed-header'>
            <h1>💬 SUNY Counselor Chat</h1>
            <p>🚀 Chat with your SUNY counselor</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Initialize the conversation if it's empty
    if len(st.session_state.counselor_agent.messages) == 0:
        first_message_content = json.dumps({
            'phase': 'introductory',
            'recipient': 'student',
            'message': prompts.FIRST_MESSAGE.format(name=st.session_state.user_profile.student_info['first_name'])
        })
        first_message = Message(
            role='assistant',
            sender='counselor',
            recipient='student',
            message=first_message_content,
            chat_id=st.session_state.chat_id
        )
        st.session_state.counselor_agent.add_message(first_message)
        rt.log_message(
            st.session_state.user.user_id,
            st.session_state.user.session_id,
            st.session_state.chat_id,
            message=first_message,
            agent_name='counselor'
        )

    # Chat container with scrollable area
    chat_container = st.container()
    with chat_container:
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        for idx, msg in enumerate(st.session_state.counselor_agent.messages):
            #print('st.session_state.chat_id:', st.session_state.chat_id)
            #print('msg.chat_id:', msg.chat_id)
            #print('content:', msg.message, '\n')
            if msg.chat_id == -1:
                print('&'* 100)
                print('\n\nskipping system message\n\n')
                print('&'* 100)
                continue
            if msg.chat_id == st.session_state.chat_id:
                if msg.sender == 'student':
                    streamlit_chat.message(msg.message, is_user=True, key=f'user_{idx}', avatar_style=STUDENT_AVATAR_STYLE)
                elif msg.sender == 'counselor' and msg.recipient == 'student':
                    message = utils.extract_content_from_message(msg.message)
                    streamlit_chat.message(message, is_user=False, key=f'assistant_{idx}', avatar_style=COUNSELOR_AVATAR_STYLE)
        st.markdown("</div>", unsafe_allow_html=True)

    # Chat input at the bottom
    prompt = st.chat_input("Type your message here...")

    # Add a clear chat button
    if st.button("Clear Chat"):
        update_student_info_from_chat()
        st.session_state.messages_since_update = 0
        st.session_state.chat_id += 1
        st.session_state.counselor_agent.messages = []
        st.session_state.suny_agent.messages = []
        st.rerun()

    if prompt:
        # Add user message to session
        key = len([x for x in st.session_state.counselor_agent.messages if x.role == 'user'])
        streamlit_chat.message(
            prompt,
            is_user=True,
            key=f'user_input_{key}',
            avatar_style=STUDENT_AVATAR_STYLE
        )

        # Process user input and get response
        rt.process_user_input(st.session_state.counselor_agent, st.session_state.suny_agent, st.session_state.user, st.chat_message, prompt, st.session_state.chat_id)
        st.session_state.messages_since_update += 1

        # Rerun to display the new messages
        st.rerun()

    # Update the student info every 5 messages if the student info is not complete
    si = st.session_state.user_profile.student_info.values()
    nsi = None in si or 'None' in si
    if st.session_state.messages_since_update >= 2 and nsi:
        update_student_info_from_chat()
        st.rerun()


def update_student_info_from_chat() -> None:
    """
    Updates the student info from the chat history if there's any new information.
    """

    st.session_state.messages_since_update = 0
    current_student_info = dba.get_student_info(st.session_state.user.user_id)
    current_student_info_str = utils.dict_to_str(current_student_info, format=False)
    new_info_prompt = prompts.UPDATE_INFO_PROMPT
    new_info_prompt += f"\n**Student's Current Information:**\n{current_student_info_str}\n\n"

    # Taking the [1:] because we don't need the system message
    convo_history = ''
    for message in st.session_state.counselor_agent.messages[1:]:
        convo_history += f"sender: {message.sender}\n"
        convo_history += f"recipient: {message.recipient}\n"
        convo_history += f"message: {message.message}\n\n"
    new_info_prompt += f"**Conversation History:**\n{convo_history}\n\n"

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
    st.session_state.user_profile.reload_all_data()

    # Update the counselor agent's system prompt
    st.session_state.counselor_agent.system_prompt = rt.build_counselor_prompt(st.session_state.user_profile.student_md_profile)


def display_student_info(user_profile: UserProfile) -> None:
    """
    Displays the student info in the sidebar.
    """

    # TODO - pass in sidebar too

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

    if user_profile.student_info:
        for key, value in user_profile.student_info.items():
            st.sidebar.text(f"{key}: {value}")

    # Display Strengths
    st.sidebar.markdown("---")
    st.sidebar.subheader("Top 5 Strengths")
    for strength_dict in user_profile.top_strengths:
        st.sidebar.text(f"{strength_dict['theme_name']}: {strength_dict['total_score']} ({strength_dict['strength_level']})")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Top 5 Weaknesses")
    for strength_dict in user_profile.bot_strengths:
        st.sidebar.text(f"{strength_dict['theme_name']}: {strength_dict['total_score']} ({strength_dict['strength_level']})")


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
        conn = dba.get_user_db_connection(st.session_state.user.user_id)
        query = "SELECT themes.theme_name, questions.statement FROM questions JOIN themes ON questions.theme_id = themes.theme_id;"
        questions = dba.execute_query(conn, query)

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
            st.error("Please answer all questions before submitting.")

        # Calculate theme scores
        theme_scores = {}
        for theme, questions in theme_questions.items():
            theme_score = sum(user_responses[q] for q in questions)
            theme_scores[theme] = theme_score

        # Save responses to pickle file
        #with open(responses_file, 'wb') as f:
        #    pickle.dump({'user_responses': user_responses, 'theme_scores': theme_scores}, f)

        # Insert user assessment responses into the database
        dba.insert_user_responses(st.session_state.user.user_id, user_responses)

        # Generate strengths summary
        user_prompt = '[question] | Score: [score]\n'
        for question, score in user_responses.items():
            user_prompt += f'{question} | Score: {score}\n'
        response = agent.quick_call(
            model='gpt-4o-mini',
            system_prompt=prompts.SUMMARIZE_ASSESSMENT_PROMPT,
            user_prompt=user_prompt)

        #  Insert strengths and weaknesses into the database
        dba.insert_strengths(st.session_state.user.user_id, theme_scores)

        # Insert assessment analysis into the database
        dba.insert_assessment_analysis(st.session_state.user.user_id, response)

        st.rerun()


def display_counselor_options():
    st.subheader("Choose your counselor")

    from src.personas import (DAVID_WELCOME_MESSAGE, EMMA_WELCOME_MESSAGE,
                              LIAM_WELCOME_MESSAGE)
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
            username = st.text_input("Username", value='')
            password = st.text_input("Password", type="password", value='')
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
        def validate_password(password: str) -> tuple[bool, str]:
            """Check password meets minimum requirements"""
            if len(password) < 8:
                return False, "Password must be at least 8 characters long"
            if not any(c.isupper() for c in password):
                return False, "Password must contain at least one uppercase letter"
            if not any(c.islower() for c in password):
                return False, "Password must contain at least one lowercase letter"
            if not any(c.isdigit() for c in password):
                return False, "Password must contain at least one number"
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                return False, "Password must contain at least one special character"
            return True, ""

        with st.form("signup_form"):
            st.markdown("#### Sign Up")
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            age = st.number_input("Age", min_value=1, max_value=100)
            gender = st.selectbox("Gender", options=["Male", "Female", "Other"])
            new_username = st.text_input("Username")
            new_password1 = st.text_input("Password", type="password")
            new_password2 = st.text_input("Password", type="password",
                help="Password must be at least 8 characters and contain uppercase, lowercase, numbers and special characters")
            signup_code = st.text_input("Signup Code")
            signup_submit = st.form_submit_button("Sign Up")

        if signup_submit:
            if new_password1 != new_password2:
                st.error("Passwords do not match")
            elif not all([first_name, last_name, new_username, new_password1]):
                st.error("Please fill in all fields to sign up.")
            else:
                # Validate signup code
                if not auth.validate_signup_code(signup_code):
                    st.error("Invalid signup code")
                else:
                    # Validate password
                    is_valid, error_msg = validate_password(new_password1)
                    if not is_valid:
                        st.error(error_msg)
                    else:
                        # Attempt signup
                        user = auth.signup(first_name, last_name, age, gender, new_username, new_password1, signup_code)
                        if user == -1:
                            st.error("Username already exists.")
                        elif user is not None:
                            st.session_state.user = user
                            login_placeholder.empty()
                            st.success("Sign up successful. You are now logged in.")
                            st.rerun()

    return st.session_state.user


def counselor_suny_chat_interface():
    st.title("🤖 Counselor-SUNY Chat")
    st.caption("Communication between Counselor and SUNY agents")

    for msg in st.session_state.counselor_suny_messages:
        st.chat_message(msg["role"]).write(msg["content"])
