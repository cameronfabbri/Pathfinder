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
# from src.user import User
from src.agent import Message
from src.database import db_access as dba
from src.database import db_setup as dbs

from scripts import run
from scripts import run_cmd



def main():
    """Main program."""

    counselor_cache_file_name = 'suny_cache.pkl'
    if os.path.isfile(counselor_cache_file_name):
        cache = ev.load_pickle(counselor_cache_file_name)
    else:
        cache = {}

    client = OpenAI(api_key=os.getenv(ev.OPENAI_API_KEY_ENV))

    user_id = 1
    # User = User(user_id, username='test', session_id=1)

    theme_scores = run_cmd.load_assessment_responses(assessment.answers)
    dba.insert_user_responses(user_id, assessment.answers)
    dba.insert_strengths(user_id, theme_scores)
    dba.insert_assessment_analysis(user_id, run_cmd.ASSESSMENT_ANALYSIS)

    counselor = lambda x: ev.run_counselor(client, x)
    counselor = ev.caching(counselor, cache)

    ev.save_pickle(cache, suny_cache_file_name)


if __name__ == '__main__':
    main()
