"""
Script to quickly test out prompts and responses from an LLM
"""

from src.pdf_tools import parse_pdf_with_llama, load_pdf_text
from src.agent import Agent
import os
from openai import OpenAI

def main():

    filepath = 'system_data/suny_schools/State-University-Of-New-York-College-Of-Technology-At-Canton/www.canton.edu/media/pubs/2023-24-currbook.pdf'

    document = load_pdf_text(filepath)
    content = document[2]

    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    system_prompt = 'You are a helpful assistant that can answer questions about the given document.'
    agent = Agent(client, 'Agent', None, system_prompt, model='gpt-4o', json_mode=False)

    prompt = '**Question:**\n'
    prompt += 'What does the third semester of a Agribusiness Management major look like?\n\n'
    prompt += '**Document:**\n' + content

    print(prompt)
    print('-'*100)

    agent.add_message('user', prompt)
    response = agent.invoke()
    print(response.choices[0].message.content)


if __name__ == '__main__':
    main()