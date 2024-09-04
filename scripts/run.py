"""
"""
import os
import hashlib
import chromadb
from openai import OpenAI
from getpass import getpass

import json
from src import utils
from src import prompts
from src.tools import tools
from src.agent import Agent, BLUE, GREEN, ORANGE, RESET

from src.user import login


def main():

    login()

    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    counselor_agent = Agent(client, name="Counselor", tools=None, system_prompt=prompts.COUNSELOR_SYSTEM_PROMPT)
    suny_agent = Agent(client, name="SUNY", tools=tools, system_prompt=prompts.SUNY_SYSTEM_PROMPT)

    user_input = 'What year was SUNY Potsdam founded?'
    user_input = ''

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
        counselor_response_json = utils.parse_json(counselor_response_str)

        recipient = counselor_response_json.get("recipient")
        counselor_message = counselor_response_json.get("message")

        counselor_agent.add_message("assistant", counselor_response_str)

        if recipient == "suny":
            print(f'{GREEN}Counselor{RESET} to {ORANGE}SUNY{RESET}: {counselor_message}')
            suny_agent.add_message("user", counselor_message)
            suny_response = suny_agent.invoke()

            if suny_response.choices[0].message.tool_calls:
                suny_response = suny_agent.handle_tool_call(suny_response)

            suny_response_str = utils.format_for_json(suny_response.choices[0].message.content)

            suny_agent.add_message("assistant", suny_response_str)
            print(f'{ORANGE}SUNY{RESET} to {GREEN}Counselor{RESET}: {suny_response_str}')

            # Add SUNY response to counselor's message history
            counselor_agent.add_message("assistant", '{"recipient": "user", "message": ' + suny_response_str + '}')

            # Counselor then processes and responds to the user
            counselor_response = counselor_agent.invoke()
            counselor_response_str = counselor_response.choices[0].message.content
            counselor_response_json = utils.parse_json(counselor_response_str)

            recipient = counselor_response_json.get("recipient")
            counselor_message = counselor_response_json.get("message")

        print(f'{GREEN}Counselor{RESET} to {BLUE}User{RESET}: {counselor_message}\n')

        # Reset user_input for the next iteration
        user_input = ''


if __name__ == "__main__":
    main()