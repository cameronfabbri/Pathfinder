"""
"""
import os
from openai import OpenAI

import json
from src import prompts
from src.tools import tools
from src.agent import Agent


def main():
    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    counselor_agent = Agent(client, name="counselor", tools=None, system_prompt=prompts.COUNSELOR_SYSTEM_PROMPT)

    suny_agent = Agent(client, name="suny", tools=tools, system_prompt=prompts.SUNY_SYSTEM_PROMPT)

    user_input = 'What year was SUNY Potsdam founded?'

    while True:
        if not user_input:
            user_input = input("You: ")
        counselor_agent.add_message("user", user_input)
        counselor_response = counselor_agent.invoke()

        # Check if the response contains a tool call
        if counselor_response.choices[0].message.tool_calls:
            counselor_response = counselor_agent.handle_tool_call(counselor_response)

        counselor_response_str = counselor_response.choices[0].message.content

        # Parse out the recipient and message
        try:
            counselor_response_json = json.loads(counselor_response_str)
        except:
            print('Could not parse counselor response as JSON')
            print(counselor_response_str)
            exit()

        recipient = counselor_response_json.get("recipient")
        counselor_message = counselor_response_json.get("message")

        if recipient == "suny":
            print(f'Counselor to SUNY: {counselor_message}')
            suny_agent.add_message("user", counselor_message)
            suny_response = suny_agent.invoke()

            if suny_response.choices[0].message.tool_calls:
                suny_response = suny_agent.handle_tool_call(suny_response)

            suny_response_str = suny_response.choices[0].message.content

            suny_agent.add_message("assistant", suny_response_str)
            print(f'SUNY to Counselor: {suny_response_str}')

            # Add SUNY response to counselor's message history
            counselor_agent.add_message("assistant", 'Response from SUNY: ' + suny_response_str)

            # Counselor then processes and responds to the user
            counselor_response = counselor_agent.invoke()
            counselor_response_str = counselor_response.choices[0].message.content
            try:
                counselor_response_json = json.loads(counselor_response_str)
            except:
                print('Could not parse counselor response as JSON')
                print(counselor_response_str)
                exit()

            recipient = counselor_response_json.get("recipient")
            counselor_message = counselor_response_json.get("message")

        counselor_agent.add_message("assistant", counselor_message)

        print(f'Counselor to User: {counselor_message}')

        print('\n')
        [print(x) for x in counselor_agent.messages]
        print('\n')

        # Reset user_input for the next iteration
        user_input = ''


if __name__ == "__main__":
    main()