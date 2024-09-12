"""
"""
import os
import sys
import streamlit as st

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src import utils
from src.user import User
from src.database import execute_query


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
            st.chat_message('assistant').write('Contacting SUNY Agent...')
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
        'address': student_info[19],
        'city': student_info[20],
        'state': student_info[21],
        'zip_code': student_info[22],
        'intended_college': student_info[23],
        'intended_major': student_info[24],
    }


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
    print('QUERY')
    print(query)
    print('ARGS')
    print(tuple(list(student_info.values()) + [st.session_state.user.user_id]))
    execute_query(query, tuple(list(student_info.values()) + [st.session_state.user.user_id]))