"""
"""

import json

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