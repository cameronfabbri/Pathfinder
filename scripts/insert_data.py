"""
Script to insert files found by scripts/find_relevant_files.py into the database for RAG
"""
import os
import click

from src.database import ChromaDB
from src.pdf_tools import load_pdf_text, chunk_pages

from openai import OpenAI
from src.agent import Agent

opj = os.path.join


def ask_question(db, question):

    results = db.collection.query(
        query_texts=[question],
        n_results=1
    )
    content = results['documents'][0][0]

    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    system_prompt = 'You are a helpful assistant that can answer questions about the given document.'
    agent = Agent(client, 'Agent', None, system_prompt, model='gpt-4o', json_mode=False)

    prompt = '**Question:**\n'
    prompt += question + '\n\n'
    prompt += '**Document:**\n' + content

    agent.add_message('user', prompt)

    print('Question:', question)
    response = agent.invoke()
    print('Answer:', response.choices[0].message.content)


@click.command()
@click.option('--directory', '-d')
def main(directory):

    #with open(opj(directory, 'relevant_files.json'), 'r') as f:
    #    files = json.load(f)
    #filepaths = [k for k, v in files.items() if v=='YES']

    filepaths = ['system_data/suny_schools/State-University-Of-New-York-College-Of-Technology-At-Canton/www.canton.edu/media/pubs/2023-24-currbook.pdf']

    pages = []
    for path in filepaths:
        document = load_pdf_text(path)
        for page in document:
            pages.append(page)

    page_chunks = chunk_pages(pages)

    name = os.path.basename(directory)
    path = opj('system_data', 'chromadb')

    db = ChromaDB(path, name)

    for chunk_num, chunk in enumerate(page_chunks):
        doc_id = name + f'-chunk-{chunk_num}'
        db.add_document(content=chunk, doc_id=doc_id)

    exit()
    question = 'What does the third semester of a Agribusiness Management major look like?'
    question = 'What are the admission requirements for Engineering Science majors?'
    question = 'Can you tell me about the nursing program?'
    ask_question(db, question)



if __name__ == '__main__':
    main()