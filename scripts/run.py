"""
Main script
"""
import os
import sys
import streamlit as st

from openai import OpenAI
from functools import lru_cache
from cryptography.fernet import Fernet

# Added for streamlit
# Need to run `streamlit scripts/run.py` to start the app
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src import utils
from src import prompts
from src import personas
from src.agent import Agent
from src.user import Document
from src.tools import suny_tools
from src.constants import UNIVERSITY_MAPPING
from src.pdf_tools import parse_pdf_with_llama
from src.database import get_top_strengths, get_bot_strengths, update_document_text
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
    if 'documents_uploaded' not in st.session_state:
        st.session_state.documents_uploaded = False


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

    #print(counselor_system_prompt)

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

def check_assessment_completed(user_id):
    """
    Check if the user has completed the assessment.
    """
    top_strengths = get_top_strengths(user_id)
    return bool(top_strengths)


def document_upload_page():
    st.title("Document Upload")

    st.write("Please upload all required documents before continuing.")

    # List of documents the user can upload
    accepted_documents = ['Transcript', 'SAT Scores', 'ACT Scores', 'Certification']

    # Initialize a list to store uploaded documents
    if 'uploaded_documents' not in st.session_state:
        st.session_state.uploaded_documents = []

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
    from werkzeug.utils import secure_filename
    filename = secure_filename(uploaded_file.name)

    # Generate a key (in practice, you'd want to store this securely)
    #key = generate_key()

    # Read the file data as bytes
    file_data = uploaded_file.read()

    # Encrypt the file data
    #encrypted_data = encrypt_file(file_data, key)

    # Save the encrypted file
    file_path = os.path.join(user_folder, filename)# + '.encrypted')
    with open(file_path, "wb") as f:
        #f.write(encrypted_data)
        f.write(file_data)

    # Update the database
    st.session_state.user.add_document(document_type, filename, file_path)

    # Store the key securely (this is a placeholder - implement secure key storage)
    #save_encryption_key(user_id, document_type, key)


def generate_key():
    return Fernet.generate_key()

def encrypt_file(file_data: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(file_data)


def process_document(user_id: int, document: Document) -> None:
    """
    Process the document and update the database

    Args:
        user_id (int): The ID of the user.
        document (Document): The document to process.
    Returns:
        None
    """

    # Process the transcript using parse_pdf_with_llama
    transcript_text = '\n'.join([x.text for x in parse_pdf_with_llama(document.filepath)])

    # Update the database
    update_document_text(user_id, document.document_id, transcript_text)


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

        #if 'assessment_completed' not in st.session_state:
        #    st.session_state.assessment_completed = check_assessment_completed(st.session_state.user.user_id)

        # TODO - remove after testing
        #st.session_state.documents_uploaded = True
    
        #if 'assessment_completed' not in st.session_state:
        #    st.session_state.assessment_completed = False

        top_strengths = get_top_strengths(st.session_state.user.user_id)
        if not top_strengths:
            assessment_page()

            # After taking the assessment, update the user's top_strengths and weaknesses
            #st.session_state.user.load_strengths_weaknesses()
            #st.session_state.user.load_assessment_responses()
            #st.session_state.assessment_completed = True
        elif not st.session_state.documents_uploaded:
            document_upload_page()
        else:
            top_strengths = get_top_strengths(st.session_state.user.user_id)
            bot_strengths = get_bot_strengths(st.session_state.user.user_id)

            print('top_strengths:', top_strengths)

            print('Documents uploaded:', st.session_state.user.documents)
            for document in st.session_state.user.documents:
                if not document.processed:
                    print('Processing document:', document.filepath)
                    process_document(st.session_state.user.user_id, document)

            print('USER')
            print(st.session_state.user)

            # TODO - remove after testing
            st.session_state.counselor_persona = 'David - The Mentor'

            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("Logout"):
                    logout()

            st.sidebar.success(f"Logged in as: {st.session_state.user.username}")
            display_student_info(st.session_state.user.user_id)

            if st.session_state.counselor_agent is None:
                client = utils.get_openai_client()
                student_info_str = utils.dict_to_str(get_student_info(st.session_state.user.user_id), format=False)
                st.session_state.counselor_agent = initialize_counselor_agent(client, student_info_str, top_strengths, bot_strengths)

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