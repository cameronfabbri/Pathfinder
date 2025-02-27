"""
Run the system without the UI
"""
import os
import readline

from openai import OpenAI

from scripts.run import initialize_counselor_agent, initialize_suny_agent

from src import agent, assessment, prompts, run_tools as rt, utils
from src.user import User, UserProfile
from src.database import db_access as dba, db_setup as dbs

MODEL = 'gpt-4o-mini'

ASSESSMENT_ANALYSIS = """
The student demonstrates strong strengths in responsibility, problem-solving,
and interpersonal skills, as evidenced by high scores in areas such as taking
ownership of commitments (5), being sensitive to others' emotions (5), and
enjoying helping others grow (4). They also show a passion for learning and
personal growth, with top scores in pursuing knowledge (5) and enjoying the
learning process (5). However, the student may struggle with competition and
recognition, as indicated by lower scores in areas related to striving to win
(3) and seeking recognition (3).  Overall, their strengths lie in collaboration,
empathy, and a commitment to excellence, while their weaknesses may include a
hesitance towards competitive environments and a need for external validation.
"""

def load_assessment_responses(assessment_responses):
    """ """
    theme_scores = {}

    # Calculate theme scores
    theme_scores = {}
    for theme, questions in assessment.theme_questions.items():
        theme_score = sum(assessment_responses[q] for q in questions)
        theme_name = assessment.themes[theme - 1][1]
        theme_scores[theme_name] = theme_score

    return theme_scores

    # Generate strengths summary
    user_prompt = '[question] | Score: [score]\n'
    for question, score in assessment_responses.items():
        user_prompt += f'{question} | Score: {score}\n'

    response = agent.quick_call(
        model='gpt-4o-mini',
        system_prompt=prompts.SUMMARIZE_ASSESSMENT_PROMPT,
        user_prompt=user_prompt)

    print('\n---------\n')
    print(response)


def main():
    """ Main function """

    os.makedirs(os.path.join('data', 'sql_dbs'), exist_ok=True)
    dbs.create_auth_tables()
    user_id = dbs.initialize_test_user('test')

    user = User(user_id, username='test', session_id=1)

    theme_scores = load_assessment_responses(assessment.answers)

    dba.insert_user_responses(user_id, assessment.answers)
    dba.insert_strengths(user_id, theme_scores)
    dba.insert_assessment_analysis(user_id, ASSESSMENT_ANALYSIS)

    user_profile = UserProfile(user_id)

    client = OpenAI(api_key=os.getenv('PATHFINDER_OPENAI_API_KEY'))
    counselor_agent = initialize_counselor_agent(client, user_profile.student_md_profile)
    suny_agent = initialize_suny_agent(client)
    print('\n\n')

    user_prompts = [
        'hi',
        '3.4',
        'I like math and finance',
        'band and lacrosse',
        'not right now',
        'that makes sense',
        'my dad is an accountant, so maybe that',
        'yes',
        'which school has the best economics program?'
    ]
    user_prompts = []
    idx = 0
    while True:

        if idx < len(user_prompts) and user_prompts:
            user_prompt = user_prompts[idx]
            print('>', user_prompt)
            idx += 1
        else:
            user_prompt = input('> ')

        rt.process_user_input(
            counselor_agent,
            suny_agent,
            user,
            None,
            user_prompt
        )
        m = utils.extract_content_from_message(
            counselor_agent.messages[-1].message
        )
        print(m, '\n')



if __name__ == "__main__":
    main()
