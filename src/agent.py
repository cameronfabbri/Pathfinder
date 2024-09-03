"""
"""

import json
from src.tools import function_map, get_student_first_name_from_id, get_student_last_name_from_id

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

    def handle_tool_call(self, response):
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

            self.messages.append({"role": "assistant", "tool_calls": tool_call_message})
            self.messages.append(function_call_result_message)

        return self.invoke()