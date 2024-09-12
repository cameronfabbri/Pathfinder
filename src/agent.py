"""
"""

import json
from src.tools import function_map
from src.logger import log_messages

# Add these color constants at the top of the file
BLUE = "\033[94m"
GREEN = "\033[92m"
ORANGE = "\033[93m"
RESET = "\033[0m"


def format_content(content):
    try:
        # Try to parse the content as JSON
        parsed = json.loads(content)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        # If it's not valid JSON, return the original content
        return content


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
        self.color = self._get_color()

    def _get_color(self):
        if self.name.lower() == "user":
            return BLUE
        elif self.name.lower() == "counselor":
            return GREEN
        elif self.name.lower() == "suny":
            return ORANGE
        return ""

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})

    def delete_last_message(self):
        if len(self.messages) > 1:
            self.messages.pop()

    def invoke(self):

        # Log messages before invoking the API
        log_messages(self.name, self.messages)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            response_format={ "type": "json_object" } if self.json_mode else None,
            temperature=self.temperature
        )

        return response

    def print_messages(self):
        print(f'Agent {self.color}{self.name}{RESET}:')
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
        print('\n', 40 * '-', '\n')

    def handle_tool_call(self, response):
        for tool_call in response.choices[0].message.tool_calls:
            print(f"{self.color}{self.name}{RESET}: Handling tool call: {tool_call.function.name}")
            arguments = json.loads(tool_call.function.arguments)
            print(f"{self.color}{self.name}{RESET}: Arguments: {arguments}")

            result = function_map[tool_call.function.name](**arguments)
            print(f"{self.color}{self.name}{RESET}: Result: {result}")

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

            self.messages.append({"role": "assistant", "tool_calls": tool_call_message})
            self.messages.append(function_call_result_message)

            print('MESSAGES')
            [print(x) for x in self.messages]

        return self.invoke()