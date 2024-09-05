"""
"""

import json
from src.tools import function_map

# Add these color constants at the top of the file
BLUE = "\033[94m"
GREEN = "\033[92m"
ORANGE = "\033[93m"
RESET = "\033[0m"

class Agent:
    def __init__(self, client, name, tools, system_prompt: str, json_mode: bool = False, temperature: float = 0.0):
        self.client = client
        self.name = name
        self.tools = tools
        self.system_prompt = system_prompt
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
        return self.client.chat.completions.create(
            model='gpt-4o',
            messages=self.messages,
            tools=self.tools,
            response_format={ "type": "json_object" } if self.json_mode else None,
            temperature=self.temperature
        )

    def print_messages(self):
        print(f'Agent {self.color}{self.name}{RESET}:')
        [print(x) for x in self.messages]
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