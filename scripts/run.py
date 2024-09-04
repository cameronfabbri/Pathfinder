"""
"""
import os
from openai import OpenAI

import json
from src import prompts
from src.tools import tools
from src.agent import Agent, BLUE, GREEN, ORANGE, RESET


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


def main():
    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    counselor_agent = Agent(client, name="Counselor", tools=None, system_prompt=prompts.COUNSELOR_SYSTEM_PROMPT)
    suny_agent = Agent(client, name="SUNY", tools=tools, system_prompt=prompts.SUNY_SYSTEM_PROMPT)

    user_input = 'What year was SUNY Potsdam founded?'

    while True:
        if not user_input:
            user_input = input(f"{BLUE}User{RESET}: ")
        else:
            print(f"{BLUE}User{RESET}: {user_input}")

        counselor_agent.add_message("user", user_input)
        counselor_response = counselor_agent.invoke()

        # Check if the response contains a tool call
        if counselor_response.choices[0].message.tool_calls:
            counselor_response = counselor_agent.handle_tool_call(counselor_response)

        counselor_response_str = counselor_response.choices[0].message.content

        # Parse out the recipient and message
        counselor_response_json = parse_json(counselor_response_str)

        recipient = counselor_response_json.get("recipient")
        counselor_message = counselor_response_json.get("message")

        counselor_agent.add_message("assistant", counselor_response_str)

        if recipient == "suny":
            print(f'{GREEN}Counselor{RESET} to {ORANGE}SUNY{RESET}: {counselor_message}')
            suny_agent.add_message("user", counselor_message)
            suny_response = suny_agent.invoke()

            if suny_response.choices[0].message.tool_calls:
                suny_response = suny_agent.handle_tool_call(suny_response)

            suny_response_str = format_for_json(suny_response.choices[0].message.content)

            suny_agent.add_message("assistant", suny_response_str)
            print(f'{ORANGE}SUNY{RESET} to {GREEN}Counselor{RESET}: {suny_response_str}')

            # Add SUNY response to counselor's message history
            counselor_agent.add_message("assistant", '{"recipient": "user", "message": ' + suny_response_str + '}')

            # Counselor then processes and responds to the user
            counselor_response = counselor_agent.invoke()
            counselor_response_str = counselor_response.choices[0].message.content
            counselor_response_json = parse_json(counselor_response_str)

            recipient = counselor_response_json.get("recipient")
            counselor_message = counselor_response_json.get("message")

        print(f'{GREEN}Counselor{RESET} to {BLUE}User{RESET}: {counselor_message}\n')

        # Reset user_input for the next iteration
        user_input = ''


if __name__ == "__main__":
    main()