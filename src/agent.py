"""
File containing the Agent class and functionality for the Agent
"""
# Cameron Fabbri
import json

from dataclasses import dataclass

from src.tools import function_map
from src.utils import RESET, get_color, get_openai_client

from src import utils


def format_content(content):
    try:
        # Try to parse the content as JSON
        parsed = json.loads(content)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        # If it's not valid JSON, return the original content
        return content


def quick_call(
        model: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.0) -> str:
    """
    """

    client = get_openai_client()
    return client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=temperature,
        response_format={ "type": "json_object" } if json_mode else None
    ).choices[0].message.content


@dataclass
class Message:
    sender: str # student, counselor, or suny
    recipient: str # student, counselor, or suny
    role: str # user, assistant, or tool
    message: str
    tool_call: dict | None = None


class Agent:
    def __init__(
            self,
            client,
            name: str,
            tools,
            system_prompt: str,
            model: str = 'gpt-4o-2024-08-06',
            json_mode: bool = False,
            temperature: float = 0.0) -> None:
        """

        """

        self.client = client
        self.name = name
        self.tools = tools
        self.system_prompt = system_prompt
        self.model = model
        self.json_mode = json_mode
        self.temperature = temperature
        self.messages = [Message(role="system", sender="", recipient="", message=self.system_prompt)]
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
        self.messages[0].message['content'] = self.system_prompt

    def add_message(self, message: Message):
        self.messages.append(message)

    def delete_last_message(self) -> None:
        if len(self.messages) > 1:
            self.messages.pop()

    def messages_to_llm_messages(self) -> list[dict]:
        result = []
        for msg in self.messages:
            if msg.sender == 'counselor' and msg.recipient == 'suny':
                content = utils.extract_content_from_message(msg.message)
            else:
                content = msg.message
            message_dict = {
                "role": msg.role,
                "content": content
            }
            # Only the role assisstant can have the tool calling stuff in it,
            # but when the role is tool, it needs the tool call id
            if msg.tool_call is not None and msg.role == 'assistant':
                message_dict['tool_calls'] = msg.tool_call
            if msg.role == 'tool':
                message_dict['tool_call_id'] = msg.tool_call[0]['id']
            result.append(message_dict)
        return result

    def invoke(self) -> str:
        """ Call the model and return the response. """

        print('Calling messages_to_llm_messages...')
        return self.client.chat.completions.create(
            model=self.model,
            messages=self.messages_to_llm_messages(),
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
        """
        """

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

            print('TOOL_CALL_MESSAGE')
            print(tool_call_message, '\n\n')
            print('FUNCTION_CALL_RESULT_MESSAGE')
            print(function_call_result_message, '\n\n')

            tc_message = Message(
                sender="",
                recipient="",
                role="assistant",
                message="",
                tool_call=tool_call_message
            )
            self.add_message(tc_message)

            fc_message = Message(
                sender="",
                recipient="",
                role="tool",
                message=function_call_result_message['content'],
                tool_call=tool_call_message
            )
            self.add_message(fc_message)

        return function_result, self.invoke()
