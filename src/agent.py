"""
"""

import json

from src.tools import function_map
from src.utils import get_color, RESET, get_openai_client


def format_content(content):
    try:
        # Try to parse the content as JSON
        parsed = json.loads(content)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        # If it's not valid JSON, return the original content
        return content


def quick_call(model, system_prompt, user_prompt, json_mode: bool = False, temperature: float = 0.0):
    client = get_openai_client()
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=temperature,
        response_format={ "type": "json_object" } if json_mode else None
    ).choices[0].message.content


class Agent:
    def __init__(self, client, name, tools, system_prompt: str, model: str = 'gpt-4o-2024-08-06', json_mode: bool = False, temperature: float = 0.0):
        self.client = client
        self.name = name
        self.tools = tools
        self.system_prompt = system_prompt
        self.model = model
        self.json_mode = json_mode
        self.temperature = temperature
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.color = get_color(self.name)

    def update_system_prompt(self, new_prompt: str) -> None:
        """
        Update the system prompt.

        Args:
            new_prompt (str): The new system prompt.
        Returns:
            None
        """
        self.system_prompt = new_prompt
        self.messages[0]["content"] = self.system_prompt

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def delete_last_message(self) -> None:
        if len(self.messages) > 1:
            self.messages.pop()

    def invoke(self) -> str:
        """ Call the model and return the response. """

        return self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            response_format={"type": "json_object"} if self.json_mode else None,
            temperature=self.temperature
        )

    def print_messages(self, verbose: bool = False) -> None:
        print('\n', 100 * '=', '\n')
        print(f'Agent {self.color}{self.name}{RESET} Messages:')
        if verbose:
            [print(x, '\n') for x in self.messages]
        else:
            for message in self.messages:
                print(f"Role: {message['role']}")
                if 'content' in message and message['content'] is not None:
                    print("Content:")
                    formatted_content = format_content(message['content'])
                    print(f"{formatted_content}\n")
                if 'tool_calls' in message:
                    print("Tool Calls:")
                    for tool_call in message['tool_calls']:
                        print(f"Tool: {tool_call['function']['name']}")
                        print(f"Arguments: {format_content(tool_call['function']['arguments'])}\n")
                if 'tool_call_id' in message:
                    print(f"Tool Call ID: {message['tool_call_id']}")
                print('-' * 40)
        print('\n', 100 * '=', '\n')

    def handle_tool_call(self, response):
        for tool_call in response.choices[0].message.tool_calls:
            print(f"{self.color}{self.name}{RESET}: Handling tool call: {tool_call.function.name}")
            arguments = json.loads(tool_call.function.arguments)
            print(f"{self.color}{self.name}{RESET}: Arguments: {arguments}")

            function_result = function_map[tool_call.function.name](**arguments)

            args_and_result = {
                **arguments,
                "result": function_result
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

            self.messages.append({"role": "assistant", "tool_calls": tool_call_message})
            self.messages.append(function_call_result_message)

        return function_result, self.invoke()