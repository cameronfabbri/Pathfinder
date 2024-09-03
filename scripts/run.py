import os
from openai import OpenAI

import json
from src import prompts
from src.functions import tools

class Agent:
    def __init__(self, client, tools, system_prompt: str):
        self.client = client
        self.tools = tools
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})

    def invoke(self):
        return self.client.chat.completions.create(
            model='gpt-4o', messages=self.messages, tools=self.tools
        )


def get_student_first_name_from_id(student_id):
    return "Cameron"

def get_student_last_name_from_id(student_id):
    return "Fabbri"


function_map = {
    "get_student_first_name_from_id": get_student_first_name_from_id,
    "get_student_last_name_from_id": get_student_last_name_from_id
}


def handle_tool_call(response, agent):
    for tool_call in response.choices[0].message.tool_calls:
        arguments = json.loads(tool_call.function.arguments)

        result = function_map[tool_call.function.name](arguments)

        args_and_result = {
            **arguments,
            "result": result
        }

        # Message containing the arguments and result of the tool call
        function_call_result_message = {
            "role": "tool",
            "content": json.dumps(args_and_result),
            "tool_call_id": tool_call.id
        }

        tool_call_message = [
            {
                "function": {
                    "arguments": json.dumps(arguments),
                    "name": tool_call.function.name
                },
                "id": tool_call.id,
                "type": "function"
            }
        ]

        agent.messages.append({"role": "assistant", "tool_calls": tool_call_message})
        agent.messages.append(function_call_result_message)

    return agent.invoke()


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
            response = handle_tool_call(response, counselor_agent)

        response_str = response.choices[0].message.content

        counselor_agent.add_message('assistant', response_str)
        print("Counselor: ", response_str, '\n')

        # Reset user_input for the next iteration
        user_input = ''

if __name__ == "__main__":
    main()