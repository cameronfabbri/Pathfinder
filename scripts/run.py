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
    counselor_agent = Agent(client, tools, prompts.COUNSELOR_SYSTEM_PROMPT)

    student_id = "1234567890"
    user_input = f"What is the first name and last name of the student with the ID {student_id}?"
    user_input = ''

    while True:
        if not user_input:
            user_input = input("You: ")
        counselor_agent.add_message("user", user_input)
        response = counselor_agent.invoke()

        # Check if the response contains a tool call
        if response.choices[0].message.tool_calls:
            response = counselor_agent.handle_tool_call(response)

        response_str = response.choices[0].message.content

        counselor_agent.add_message('assistant', response_str)
        print("Counselor: ", response_str, '\n')

        # Reset user_input for the next iteration
        user_input = ''

if __name__ == "__main__":
    main()