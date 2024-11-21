"""
Evaluation methods!
"""

from typing import List
from typing import Any
import os
import json
import pickle

from openai import OpenAI

from src import assessment
from src.user import User
from src.agent import Message
from src.database import db_access as dba
from src.database import db_setup as dbs

from scripts import run
from scripts import run_cmd

COUNSELOR = 'counselor'
SUNY = 'suny'

USER = 'user'
ASSISTANT = 'assistant'


OPENAI_API_KEY_ENV = 'PATHFINDER_OPENAI_API_KEY'


def run_suny(client: OpenAI, question: str) -> List[Message]:
    """
    Functionally run SUNY client,
    using logic from run_tools.process_user_input.
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


def caching(func, cache):
    """Cache the results of a single argument function."""
    def wrap(x):
        res = cache.get(x)
        if res is not None:
            return res
        res = func(x)
        cache[x] = res
        return res
    return wrap


def main():
    """Main program."""

    suny_cache_file_name = 'suny_cache.pkl'
    if os.path.isfile(suny_cache_file_name):
        suny_cache = load_pickle(suny_cache_file_name)
    else:
        suny_cache = {}

    client = OpenAI(api_key=os.getenv(OPENAI_API_KEY_ENV))

    user_id = 1
    user = User(user_id, username='test', session_id=1)

    # set up user

    dbs.initialize_db()

    theme_scores = run_cmd.load_assessment_responses(assessment.answers)
    dba.insert_user_responses(user_id, assessment.answers)
    dba.insert_strengths(user_id, theme_scores)
    dba.insert_assessment_analysis(user_id, run_cmd.ASSESSMENT_ANALYSIS)

    suny = lambda x: run_suny(client, x)
    suny = caching(suny, suny_cache)

    question = 'Could you provide information on which SUNY schools have the best economics programs?'
    messages = suny(question)

    print(messages)

    save_pickle(suny_cache, suny_cache_file_name)


if __name__ == '__main__':
    main()
