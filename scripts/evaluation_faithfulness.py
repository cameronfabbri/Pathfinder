"""
Faithfulness evaluation of SUNY agent.
"""

from typing import Any, List, Tuple
import os
import json

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

from scripts import run_cmd


def main():
    """Main program."""

    temperature = 1.0
    n_iter = 3

    client = OpenAI(api_key=os.getenv(ev.OPENAI_API_KEY_ENV))

    suny_cache_file_name = 'suny_cache.pkl'
    if os.path.isfile(suny_cache_file_name):
        cache = ev.load_pickle(suny_cache_file_name)
    else:
        cache = {}

    print(list(cache.keys()))

    # set up user

    dbs.create_auth_tables()
    user_id = dbs.initialize_test_user('test')

    theme_scores = run_cmd.load_assessment_responses(assessment.answers)
    dba.insert_user_responses(user_id, assessment.answers)
    dba.insert_strengths(user_id, theme_scores)
    dba.insert_assessment_analysis(user_id, run_cmd.ASSESSMENT_ANALYSIS)

    suny = lambda x: ev.run_suny(x, client, temperature)

    questions = [
        'Could you provide information on which SUNY schools have the best economics programs?',
        # 'What is the cheapest school to get a computer science degree at?',
        # 'Which school should I go to if I want to study piano?',
        # 'What is the best school?',              # doesn't invoke tool
        # 'What is the best school for nursing?'   # fail with too many tokens
    ]

    rows = []

    for question_org in questions:
        for idx in range(n_iter):

            key = (question_org, idx)
            messages = cache.get(key)

            if messages is None:
                messages = suny(question_org)
                cache[key] = messages

            question, docs, answer = _extract_rag_info(messages)
            print()
            print('~~~~ ' * 8)

            print(question)

            print('~~~~ ' * 8)

            print(docs)

            print('~~~~ ' * 8)

            print(answer)

            print('~~~~ ' * 8)

            # TODO: we could cache this too
            def llm(prompt: str) -> str:
                """Call an LLM."""
                # TODO: handle errors gracefully
                return agent.quick_call(
                    model=ev.MODEL_DEFAULT,
                    system_prompt='You are a helpful AI assistant.',
                    user_prompt=prompt,
                    json_mode=False,
                    temperature=0.0
                )

            total_score, verdicts, scores = faithfulness.faithfulness(question, docs, answer, llm)

            for x in verdicts:
                print(x)

            print('~~~~ ' * 8)

            print()

            print(total_score)

            row = dict(
                question=question,
                idx=idx,
                answer=answer,
                score=total_score
            )
            rows.append(row)

    ev.save_xlsx('faithfulness.xlsx', rows)

    ev.save_pickle(cache, suny_cache_file_name)


def _extract_rag_info(messages: List[Message]) -> Tuple[str, str, str]:
    # TODO: gracefully handle case where there is no tool call

    assert len(messages) == 5

    # first message is system prompt
    assert messages[0].role == 'system'

    assert messages[1].role == 'user'
    question = utils.extract_content_from_message(messages[1].message)

    assert messages[2].role == 'assistant'

    assert messages[3].role == 'tool'
    docs = json.loads(messages[3].message)['result']

    assert messages[4].role == 'assistant'
    answer = messages[4].message

    return question, docs, answer


if __name__ == '__main__':
    main()
