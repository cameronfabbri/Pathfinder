tools = [
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


def get_suny_school_info(school_name):
    return "Founded in 1816 and located in Potsdam, NY"


function_map = {
    "get_suny_school_info": get_suny_school_info,
}