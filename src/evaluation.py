"""
General functions for use in evaluation.
"""

from typing import Any, List, Tuple, Callable, Dict
import os
import json
import pickle

from openai import OpenAI

from src import agent
from src import utils
from src import assessment
from src import faithfulness
from src import run_tools
# from src.user import User
from src.agent import Message
from src.database import db_access as dba
from src.database import db_setup as dbs

from scripts import run
from scripts import run_cmd


COUNSELOR = 'counselor'
SUNY = 'suny'

USER = 'user'
ASSISTANT = 'assistant'


MODEL_DEFAULT = 'gpt-4o-mini'
OPENAI_API_KEY_ENV = 'PATHFINDER_OPENAI_API_KEY'



def run_counselor(
        message: str,
        prev_messages: List[Message],
        client: OpenAI,
        student_md_profile: str,
        ) -> List[Message]:
    """
    Functionally run counselor agent,
    using run_tools.process_user_input
    """

    counselor_agent = run.initialize_counselor_agent(client, student_md_profile)
    suny_agent = run.initialize_suny_agent(client)

    counselor_agent.messages = prev_messages
    run_tools.process_user_input(counselor_agent, suny_agent, None, None, message)
    return counselor_agent.messages


def run_suny(question: str, client: OpenAI) -> List[Message]:
    """
    Functionally run SUNY agent,
    using logic copied from run_tools.process_user_input.
    """

    suny_agent = run.initialize_suny_agent(client)

    message_dict = dict(
        phase='reviewing',
        recipient='suny',
        message=question
    )
    message_body = json.dumps(message_dict)

    message = Message(COUNSELOR, SUNY, USER, message_body)

    suny_agent.add_message(message)
    response = suny_agent.invoke()

    if response.choices[0].message.tool_calls:
        # note that in this cases, the original response is NOT
        # getting added as a message to the agent
        _, response, tc_messages = suny_agent.handle_tool_call(response)

    message = Message(SUNY, COUNSELOR, ASSISTANT, response.choices[0].message.content)
    suny_agent.add_message(message)

    return suny_agent.messages


def load_pickle(file_path: str) -> Any:
    """load something from a pickle file"""
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def save_pickle(obj: Any, file_path: str) -> None:
    """save something to a pickle file"""
    with open(file_path, 'wb') as f:
        pickle.dump(obj, f)


def caching(func: Callable, cache: Dict):
    """Cache the results of a single argument function."""
    def wrap(x):
        """Wrap the function."""
        res = cache.get(x)
        if res is not None:
            return res
        res = func(x)
        cache[x] = res
        return res
    return wrap
