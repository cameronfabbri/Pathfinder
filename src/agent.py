"""
File containing the Agent class and functionality for the Agent
"""

# Cameron Fabbri
import json

from typing import Any, Dict, List
from dataclasses import dataclass

import tiktoken

from src import utils
from src.tools import function_map
from src.utils import RESET, get_color, get_openai_client

MAX_INPUT_TOKENS = 32000


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
    sender: str     # student, counselor, or suny
    recipient: str  # student, counselor, or suny
    role: str       # user, assistant, or tool
    message: str
    chat_id: int
    tool_call: List[dict] | None = None


class Agent:
    def __init__(
            self,
            client,
            name: str,
            tools,
            system_prompt: str,
            #model: str = 'gpt-4o-2024-08-06',
            model: str,
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
        self.messages = []
        #self.messages = [Message(role="system", sender="", recipient="", message=self.system_prompt, chat_id=-1)]
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
        #self.messages[0].message['content'] = self.system_prompt

    def add_message(self, message: Message):
        self.messages.append(message)

    def delete_last_message(self) -> None:
        if len(self.messages) > 1:
            self.messages.pop()

    def messages_to_llm_messages(self, messages: list[Message]) -> list[dict]:
        result = []
        for msg in messages:
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

        messages = []
        messages.append(Message(role="system", sender="", recipient="", message=self.system_prompt, chat_id=-1))
        messages.extend(self.messages)

        # Make sure messages don't exceed context length
        # TODO: we could choose max_tokens based on the model
        encoding = tiktoken.encoding_for_model(self.model)
        messages = self.messages_to_llm_messages(messages)
        messages = filter_messages_token_count(messages, MAX_INPUT_TOKENS, encoding)

        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
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
                print(f"Role: {message.role}")
                if message.message is not None:
                    print("Content:")
                    formatted_content = format_content(message.message)
                    print(f"{formatted_content}\n")
                if message.tool_call is not None:
                    print("Tool Calls:")
                    for tool_call in message.tool_call:
                        print(f"Tool: {tool_call['function']['name']}")
                        print(f"Arguments: {format_content(tool_call['function']['arguments'])}\n")
                #if message.tool_call_id is not None:
                #    print(f"Tool Call ID: {message.tool_call_id}")
                print('-' * 40)
        print('\n', 100 * '=', '\n')

    def handle_tool_call(self, response, chat_id: int):
        """
        """

        tc_messages = []
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

            tc_message = Message(
                sender="",
                recipient="",
                role="assistant",
                message="",
                tool_call=tool_call_message,
                chat_id=chat_id
            )

            fc_message = Message(
                sender="",
                recipient="",
                role="tool",
                message=function_call_result_message['content'],
                tool_call=tool_call_message,
                chat_id=chat_id
            )

            self.add_message(tc_message)
            self.add_message(fc_message)

            tc_messages.append(tc_message)
            tc_messages.append(fc_message)

        return function_result, self.invoke(), tc_messages


def filter_messages_token_count(
        messages: List[Dict[str, str]],
        max_tokens: int,
        encoding: tiktoken.Encoding) -> List[Dict[str, Any]]:

    """
    Filter messages to fit within a certain token count.
    Keeps the system message and messages from the end backward
    until the limit is reached.
    """

    assert len(messages) > 0
    system_message, *other_messages = messages
    print('other messages:', len(other_messages))
    assert system_message['role'] == 'system', 'expected first message role=system'

    tokens_org = sum([
        utils.count_tokens(x['content'], encoding)
        for x in messages
    ])

    total_tokens = utils.count_tokens(system_message['content'], encoding)

    res = [system_message]
    if total_tokens > max_tokens:
        raise Exception(f'System mesage length > {max_tokens}')

    messages_keep = []
    for msg in reversed(other_messages):
        tokens = utils.count_tokens(msg['content'], encoding)
        if total_tokens + tokens > max_tokens:
            break
        messages_keep.append(msg)
        total_tokens += tokens

    res.extend(reversed(messages_keep))

    print(
        f'token count filter: {len(messages)} messages @ {tokens_org} tokens -> ' +
        f'{len(res)} messages @ {total_tokens} tokens')

    return res
