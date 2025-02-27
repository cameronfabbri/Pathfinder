"""
General functions for use in evaluation.
"""

from typing import Any, List, Tuple, Callable, Dict, Optional
import json
import pickle

import xlsxwriter
from openai import OpenAI

from src import run_tools
from src.agent import Message

from scripts import run


COUNSELOR = 'counselor'
SUNY = 'suny'

USER = 'user'
ASSISTANT = 'assistant'


MODEL_DEFAULT = 'gpt-4o-mini'
OPENAI_API_KEY_ENV = 'PATHFINDER_OPENAI_API_KEY'


def run_counselor(
        question: str,
        prev_messages: List[Message],
        client: OpenAI,
        student_md_profile: str,
        temperature: float
        ) -> Optional[List[Message]]:
    """
    Functionally run counselor agent,
    using run_tools.process_user_input
    """

    # create new agents
    counselor_agent = run.initialize_counselor_agent(client, student_md_profile)
    suny_agent = run.initialize_suny_agent(client)

    counselor_agent.temperature = temperature
    suny_agent.temperature = temperature

    # patch in messages
    counselor_agent.messages = list(prev_messages)

    print('suny messages before:', len(suny_agent.messages))

    # run
    try:
        run_tools.process_user_input(counselor_agent, suny_agent, None, None, question)
    except Exception as e:
        print(e)
        # probably some kind of request too long or rate limit error. IMO this should be handled by the agent
        return None

    # this makes a couple assumptions but I think they are safe
    assert len(counselor_agent.messages) == len(prev_messages) + 2

    print('previous messages:', len(prev_messages))
    print('total messages:', len(counselor_agent.messages))

    print('suny messages after:', len(suny_agent.messages))
    print('---')

    # return the two new messages
    return counselor_agent.messages[-2:]


def run_suny(question: str, client: OpenAI, temperature: float) -> List[Message]:
    """
    Functionally run SUNY agent,
    using logic copied from run_tools.process_user_input.
    """

    suny_agent = run.initialize_suny_agent(client)
    suny_agent.temperature = temperature

    message_dict = dict(
        phase='reviewing',
        recipient='suny',
        message=question
    )
    message_body = json.dumps(message_dict)

    message = Message(COUNSELOR, SUNY, USER, message_body, chat_id=0)

    suny_agent.add_message(message)
    response = suny_agent.invoke()

    if response.choices[0].message.tool_calls:
        # note that in this cases, the original response is NOT
        # getting added as a message to the agent
        _, response, tc_messages = suny_agent.handle_tool_call(response, chat_id=0)

    message = Message(SUNY, COUNSELOR, ASSISTANT, response.choices[0].message.content, chat_id=0)
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


def wrap_cache(func: Callable, cache: Dict):
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


def save_xlsx(file_path: str, rows: List[Dict]) -> None:
    """Save records to an excel file."""

    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet(name='Results')

    # Enable text wrapping for all cells
    wrap_format = workbook.add_format({'text_wrap': True})
    worksheet.set_column('A:Z', None, wrap_format)

    # Set width of third column (C) to 40
    worksheet.set_column('C:C', 80, wrap_format)

    worksheet.write_row(0, 0, list(rows[0].keys()))
    for idx, row in enumerate(rows):
        worksheet.write_row(idx + 1, 0, list(row.values()))

    workbook.close()
