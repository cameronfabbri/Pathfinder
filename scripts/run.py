"""
Main script
"""
# Cameron Fabbri

import os
import sys
import streamlit as st

from openai import OpenAI
from functools import lru_cache
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename

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

DEBUG = False
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
    if 'user_messages' not in st.session_state:
        st.session_state.user_messages = []
    if 'counselor_suny_messages' not in st.session_state:
        st.session_state.counselor_suny_messages = []
    if 'counselor_persona' not in st.session_state:
        st.session_state.counselor_persona = None
    if 'documents_uploaded' not in st.session_state:
        st.session_state.documents_uploaded = False
    if 'uploaded_documents' not in st.session_state:
        st.session_state.uploaded_documents = []


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


def document_upload_page():
    st.title("Document Upload")

    st.write("Please upload all required documents before continuing.")

    # List of documents the user can upload
    accepted_documents = ['Transcript', 'SAT Scores', 'ACT Scores', 'Certification']

    # Document type selection
    doc_type = st.selectbox("Select document type", accepted_documents)

    # File uploader
    uploaded_file = st.file_uploader(f"Upload {doc_type}", type=['pdf', 'docx', 'txt'], key="document_uploader")

    # Add Document button
    if st.button("Upload Document"):
        if uploaded_file is not None:
            st.session_state.uploaded_documents.append((doc_type, uploaded_file))
            st.success(f"{doc_type} added successfully!")
        else:
            st.warning("Please select a file before adding.")

    # Display added documents
    if st.session_state.uploaded_documents:
        st.subheader("Added Documents:")
        for doc_type, file in st.session_state.uploaded_documents:
            st.write(f"{doc_type}: {file.name}")

    # Continue button
    if st.button("Continue"):
        st.session_state.documents_uploaded = True
        if st.session_state.uploaded_documents:
            for doc_type, file in st.session_state.uploaded_documents:
                save_uploaded_file(st.session_state.user.user_id, doc_type, file)
            
            st.success("All documents uploaded successfully!")
            st.session_state.uploaded_documents = []  # Clear the list after successful upload
            st.rerun()


def save_uploaded_file(user_id, document_type, uploaded_file):
    # Create user-specific directory if it doesn't exist
    user_folder = os.path.join('uploads', str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    # Sanitize the file name
    filename = secure_filename(uploaded_file.name)

    # Generate a key (in practice, you'd want to store this securely)
    #key = generate_key()

    # Read the file data as bytes
    file_data = uploaded_file.read()

    # Encrypt the file data
    #encrypted_data = encrypt_file(file_data, key)

    filepath = os.path.join(user_folder, filename)# + '.encrypted')
    with open(filepath, "wb") as f:
        #f.write(encrypted_data)
        f.write(file_data)

    extracted_text = '\n'.join([x.text for x in pdft.parse_pdf_with_llama(filepath)])

    # Update the database
    st.session_state.user.add_document(
        document_type, filename, filepath, extracted_text, processed=True
    )

    # Store the key securely (this is a placeholder - implement secure key storage)
    #save_encryption_key(user_id, document_type, key)



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

        if not st.session_state.user.top_strengths:
            itf.assessment_page()
            
        #elif not st.session_state.documents_uploaded:
        #    document_upload_page()
        else:

            st.session_state.user.reload_all_data()

            #top_strengths = dba.get_top_strengths(st.session_state.user.user_id)
            #bot_strengths = dba.get_bot_strengths(st.session_state.user.user_id)

            #markdown = st.session_state.user.build_markdown()

            #print('Documents uploaded:', st.session_state.user.documents)
            #for document in st.session_state.user.documents:
            #    if not document.processed:
            #        print('Processing document:', document.filepath)
            #        process_document(st.session_state.user.user_id, document)

            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("Logout"):
                    rt.logout()

            st.sidebar.success(f"Logged in as: {st.session_state.user.username}")
            itf.display_student_info(st.session_state.user.user_id)

            if st.session_state.counselor_agent is None:
                client = utils.get_openai_client()
                st.session_state.counselor_agent = initialize_counselor_agent(
                    client, st.session_state.user.student_md_profile
                )

            if st.session_state.suny_agent is None:
                client = utils.get_openai_client()
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
                        first_message = dba.get_chat_summary_from_db(st.session_state.user.user_id)
                    except:
                        print('\nNo chat summary found in database, did you quit without logging out?\n')
                        first_message = f"Hello {st.session_state.user.username}, welcome back to the chat!"
                st.session_state.user_messages = [{"role": "assistant", "content": first_message}]
                st.session_state.counselor_agent.add_message("assistant", first_message)
            
            if not st.session_state.counselor_suny_messages:
                st.session_state.counselor_suny_messages = []

            with col1:
                itf.main_chat_interface()

    else:
        st.error("Please log in to continue")



if __name__ == "__main__":
    main()