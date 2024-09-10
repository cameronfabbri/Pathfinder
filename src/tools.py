from src.user import get_db_connection


suny_tools = [
    {
        "type": "function",
        "function": {
            "name": "show_campus_map",
            "description": "Display the campus map of the chosen SUNY school. Call this if a user asks to see the campus map.",
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


def show_campus_map(school_name: str):
    return f"Here is the campus map for {school_name}"


function_map = {
    "show_campus_map": show_campus_map,
}
