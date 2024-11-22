"""
General evaluation of conselor agent.
"""

from typing import Any, Dict, List, Optional
from typing import Any, List, Tuple
import os
import json
import pickle

from openai import OpenAI

from src import agent
from src import utils
from src import assessment
from src import faithfulness
from src import evaluation as ev
from src.user import User, UserProfile
from src.agent import Message
from src.database import db_access as dba
from src.database import db_setup as dbs

from src import run_tools

from scripts import run
from scripts import run_cmd


USER_PROMPTS = [
    'hi',
    '3.4',
    'I like math and finance',
    'band and lacrosse',
    'not right now',
    'that makes sense',
    'my dad is an accountant, so maybe that',
    'yes'
]


def main():
    """Main program."""
    client = OpenAI(api_key=os.getenv(ev.OPENAI_API_KEY_ENV))

    counselor_cache_file_name = 'counselor_cache.pkl'
    counselor_messages_file_name = 'counselor_messages.pkl'

    if os.path.isfile(counselor_cache_file_name):
        cache = ev.load_pickle(counselor_cache_file_name)
    else:
        cache = {}

    user_id = 1
    user = User(user_id, username='test', session_id=1)
    user_profile = UserProfile(user_id)

    theme_scores = run_cmd.load_assessment_responses(assessment.answers)
    dba.insert_user_responses(user_id, assessment.answers)
    dba.insert_strengths(user_id, theme_scores)
    dba.insert_assessment_analysis(user_id, run_cmd.ASSESSMENT_ANALYSIS)

    if os.path.isfile(counselor_messages_file_name):
        messages = ev.load_pickle(counselor_messages_file_name)
    else:
        messages = _prep_counselor_conversation(USER_PROMPTS, client, user_profile.student_md_profile)
        ev.save_pickle(messages, counselor_messages_file_name)

    counselor = lambda x: ev.run_counselor(x, messages, client, user_profile.student_md_profile)
    counselor = ev.wrap_cache(counselor, cache)

    question = 'which school has the best economics program?'

    print('messages before run:', len(messages))

    messages_response = counselor(question)

    print('messages after run:', len(messages_response))

    ev.save_pickle(cache, counselor_cache_file_name)


def _prep_counselor_conversation(user_prompts: List[str], client: OpenAI, student_md_profile: str):
    """
    Run a sequence of user messages to prepare a starting
    message history state for the counselor agent."""

    counselor_agent = run.initialize_counselor_agent(client, student_md_profile)
    suny_agent = run.initialize_suny_agent(client)

    for user_prompt in user_prompts:
        run_tools.process_user_input(counselor_agent, suny_agent, None, None, user_prompt)

    return counselor_agent.messages


if __name__ == '__main__':
    main()
