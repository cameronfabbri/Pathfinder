"""
"""

import json



def dict_to_str(info_dict: dict) -> str:
    """
    Convert a dictionary to a string

    Args:
        info_dict (dict): The info dictionary

    Returns:
        info_str (str): The info string
    """
    info_str = ""
    for key, value in info_dict.items():
        info_str += key.replace('_', ' ').title() + ": " + str(value) + "\n"
    return info_str


def format_for_json(input_string):
    """
    Takes a string and formats it properly for use in JSON.
    Escapes special characters like quotes and newlines.
    """
    # Use json.dumps to handle escaping
    formatted_string = json.dumps(input_string)
    
    # Remove the surrounding double quotes added by json.dumps
    return formatted_string[1:-1]


def parse_json(message):
    """
    Parses a string as JSON, with special handling for the JSON format used by the agents.
    """
    try:
        return json.loads(message)
    except:
        print('Could not parse message as JSON')
        print(message)
        exit()