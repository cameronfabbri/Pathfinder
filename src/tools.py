from src.user import get_db_connection


suny_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_suny_school_info",
            "description": "Get the information about a SUNY school from its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "school_name": {
                        "type": "string",
                        "description": "The name of the SUNY school.",
                    },
                },
                "required": ["school_name"],
                "additionalProperties": False,
            },
        }
    }
]

counselor_tools = None
_counselor_tools = [
    {
        "type": "function",
        "function": {
            "name": "update_student_info",
            "description": "Update the student's information",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {
                        "type": "string",
                        "description": "The first name of the student.",
                    },
                    "last_name": {
                        "type": "string",
                        "description": "The last name of the student.",
                    },
                    "intended_college": {
                        "type": "string",
                        "description": "The intended college of the student.",
                    },
                },
                "required": ["first_name", "last_name", "intended_college"],
                "additionalProperties": False,
            }
        }
    }
]


def update_student_info(first_name, last_name, intended_college):
    user_id = 1
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE students SET first_name=?, last_name=?, intended_college=? WHERE user_id=?",
            (first_name, last_name, intended_college, user_id)
        )
        conn.commit()
    return "Student info updated successfully"
    #return '{"recipient": "user", "message": "Student info updated successfully - do not repeat this message to user"}'


def get_suny_school_info(school_name):
    return "Founded in 1816 and located in Potsdam, NY"


function_map = {
    "get_suny_school_info": get_suny_school_info,
    "update_student_info": update_student_info,
}