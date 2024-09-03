tools = [
    {
        "type": "function",
        "function": {
            "name": "get_student_first_name_from_id",
            "description": "Get the student's first name from their ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "The student's ID.",
                    },
                },
                "required": ["student_id"],
                "additionalProperties": False,
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_last_name_from_id",
            "description": "Get the student's last name from their ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "The student's ID.",
                    },
                },
                "required": ["student_id"],
                "additionalProperties": False,
            },
        }
    }
]
