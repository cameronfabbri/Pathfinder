"""
General evaluation of conselor agent.
"""

from typing import Any, List, Tuple
import os
import json

from openai import OpenAI

from src import assessment
from src import evaluation as ev
from src.user import User, UserProfile
from src.agent import Message
from src.database import db_access as dba
from src.database import db_setup as dbs
from src import run_tools

from scripts import run
from scripts import run_cmd


USER_PROMPTS = [
    'Sounds good',
    'My gpa is a 3.4, I like math and finance, and I\'m in the school band and play lacrosse',
    'I feel strongly about them',
    'My dad is an accountant, so maybe that',
    'Let\'s focus on accounting for now.'
]


def main():
    """Main program."""

    temperature = 1.0
    n_iter = 3

    client = OpenAI(api_key=os.getenv(ev.OPENAI_API_KEY_ENV))

    counselor_cache_file_name = 'counselor_cache.pkl'
    counselor_messages_file_name = 'counselor_messages.pkl'

    if os.path.isfile(counselor_cache_file_name):
        cache = ev.load_pickle(counselor_cache_file_name)
    else:
        cache = {}

    dbs.create_auth_tables()
    user_id = dbs.initialize_test_user('test')

    theme_scores = run_cmd.load_assessment_responses(assessment.answers)
    dba.insert_user_responses(user_id, assessment.answers)
    dba.insert_strengths(user_id, theme_scores)
    dba.insert_assessment_analysis(user_id, run_cmd.ASSESSMENT_ANALYSIS)

    # user = User(user_id, username='test', session_id=1)
    user_profile = UserProfile(user_id)

    if os.path.isfile(counselor_messages_file_name):
        messages = ev.load_pickle(counselor_messages_file_name)
    else:
        messages = _prep_counselor_conversation(USER_PROMPTS, client, user_profile.student_md_profile)
        ev.save_pickle(messages, counselor_messages_file_name)

    counselor = lambda x: ev.run_counselor(
        x, messages, client, user_profile.student_md_profile,
        temperature)

    # These questions show fragility here with gpt-4o-mini.

    # Some variations work but others will try to call the
    # SUNY agent instead of responding to the user.

    # The problem may be with the SUNY agent trying
    # to perform RAG by specifying a school when there
    # is no reason to, and then no documents are found.
    # So the counselor agent asks the SUNY agent again.
    # (NOTE: this problem was caused by leftover messages
    # in the SUNY agent since it was being cached between evals.
    # I removed the caching but it still may be a problem
    # in real use cases.)

    # But the counselor agent also asks the SUNY agent again
    # even when this doesn't happen, so I'm not sure
    # if those two issues are related. (NOTE: they probably aren't)

    # There is also the case where the counselor responds
    # to the user but tells them to wait while
    # they query the SUNY agent.

    questions_and_evals = [
        # this particular question was really good at demonstrating the problem
        # with school names being erroneously aded to RAG tool calls (from previous
        # SUNY agent messages)
        #(
        #    'Which school has the best economics program?',
        #    lambda x: True
            # lambda x: (
            #     'buffalo state college' in x.lower() or
            #     'jamestown community college' in x.lower()
            # )
        #),
        ('Does Binghamton have a good accounting program?', lambda x: True),
        ('What\'s the cost of tuition at Buffalo state?', lambda x: x is not None and 'university at buffalo' not in x.lower()),
        ('Which school has a good veterinary program?', lambda x: True),
        ('Does alfred state have financial aid?', lambda x: True)
        # (
        #     'Which school will give me the best economics degree?',
        #     lambda x: True
        # ),
        # (
        #     'I am interested in an economics degreee. Which school should I choose?',
        #     lambda x: True
        # ),
        # (
        #     'I am interested in an accounting degree. Which school should I choose?',
        #     lambda x: True
        # )
    ]

    rows = []

    for question, eval_func in questions_and_evals:

        for idx in range(n_iter):

            key = (question, idx)
            new_messages = cache.get(key)

            if new_messages is None:
                new_messages = counselor(question)

            if new_messages is None:
                # OpenAI error, try it again next round
                present, correct, answer, failreason = False, False, '', 'likely openai error'
            else:
                cache[key] = new_messages
                present, correct, answer, failreason = evaluate(new_messages, eval_func)

            row = dict(
                question=question,
                idx=idx,
                answer=answer,
                present=present,
                correct=correct,
                failreason=failreason
            )
            rows.append(row)

    for row in rows:
        print(row)

    ev.save_xlsx('general.xlsx', rows)
    print('Saved results to general.xlsx')

    ev.save_pickle(cache, counselor_cache_file_name)
    print('Saved cache to counselor_cache.pkl')


def evaluate(
        new_messages: List[Message],
        eval_func) -> Tuple[bool, bool, str, str]:
    """
    Given new messages and determine whether an answer is present
    and correct. Returns flags, the answer, and a reason.
    """

    msg = new_messages[-1]

    try:
        msg_dict = json.loads(msg.message)
        assert isinstance(msg_dict, dict)
        assert 'phase' in msg_dict
        assert 'recipient' in msg_dict
        assert 'message' in msg_dict
    except:
        return False, False, msg.message, 'json problem'

    # TODO: check phase?

    answer = msg_dict['message']

    # incorrect behavior
    recipient = msg_dict['recipient']
    if recipient != 'student':
        return True, False, answer, f'bad recipient `{recipient}`'

    correct = eval_func(answer)
    fail_reason = 'eval func fail' if not correct else ''

    return True, correct, answer, fail_reason


def _prep_counselor_conversation(user_prompts: List[str], client: OpenAI, student_md_profile: str):
    """
    Run a sequence of user messages to prepare a starting
    message history state for the counselor agent."""

    counselor_agent = run.initialize_counselor_agent(client, student_md_profile)
    suny_agent = run.initialize_suny_agent(client)

    from src import prompts
    first_message_content = json.dumps({
        'phase': 'introductory',
        'recipient': 'student',
        #'message': prompts.FIRST_MESSAGE.format(name='JohnJacobJingleheimerSchmidt')
        'message': prompts.FIRST_MESSAGE.format(name='Cameron')
    })
    first_message = Message(
        role='assistant',
        sender='counselor',
        recipient='student',
        message=first_message_content,
        chat_id=0
    )
    counselor_agent.add_message(first_message)

    for user_prompt in user_prompts:
        print('USER PROMPT:', user_prompt)
        run_tools.process_user_input(counselor_agent, suny_agent, None, None, user_prompt)
        print('Counselor agent:', counselor_agent.messages[-1].message, '\n')
        #input()

    return counselor_agent.messages


if __name__ == '__main__':
    main()
