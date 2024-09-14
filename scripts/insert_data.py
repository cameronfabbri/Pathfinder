"""
Script to insert files found by scripts/find_relevant_files.py into the database for RAG
"""
import os
import json
import click

from tqdm import tqdm

from src.database import ChromaDB
from src.pdf_tools import load_pdf_text, chunk_pages, get_pdf_metadata

from openai import OpenAI
from src.agent import Agent
from src.constants import SUNY_DATA_DIR, UNIVERSITY_DATA_DIR, CHROMA_DB_PATH, UNIVERSITY_MAPPING

opj = os.path.join

def get_distinct_university_results(query_results, n_results=3):
    unique_universities = {}
    
    for idx, metadata in enumerate(query_results['metadatas'][0]):
        university = metadata['university']
        if university not in unique_universities:
            unique_universities[university] = {
                'id': query_results['ids'][0][idx],
                'distance': query_results['distances'][0][idx],
                'metadata': metadata,
                'document': query_results['documents'][0][idx]  # Include the document text here
            }
        
        if len(unique_universities) == n_results:
            break
    
    return list(unique_universities.values())

SYSTEM_PROMPT = """
You are a helpful assistant that can answer questions about the given document.
"""

def _ask_question(db, question):

    all_results = db.collection.query(
        query_texts=[question],
        n_results=100
    )
    results = get_distinct_university_results(all_results, n_results=3)

    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    agent = Agent(client, 'Agent', None, SYSTEM_PROMPT, model='gpt-4o', json_mode=True)

    prompt = 'Answer the following question given the available information.'
    prompt += '**Question:**\n'
    prompt += question + '\n\n'
    prompt += '**Information:**\n'
    for result in results:
        prompt += f'**University:** {result["metadata"]["university"]}\n'
        prompt += f'**Document:** {result["document"]}\n\n'
        prompt += f'**Document ID:** {result["id"]}\n\n'
        prompt += '---'

    agent.add_message('user', prompt)

    print('Question:', question, '\n')
    response = agent.invoke()
    print('Answer:', response.choices[0].message.content)


_QUESTION_SYSTEM_PROMPT = """
You are a helpful assistant that generates a list of 5 questions based directly
on specific details from the given document. Ensure that each of the 5 questions
can be answered by explicit information found within the document, without using
reference words. Your question must explicitly reference content from the
document. Your response must be in the following JSON format without ```JSON or
```json at the beginning or end.

**Rules:**
- Your question must explicitly reference content from the document.
- Your question must be answerable by explicit information found within the document.
- Your question must not be a simple recall of information, but rather an attempt to extract specific details.
- Your question must be concise and directly related to the document.
- Do not use reference phrases such as "the document", "this document", or "the information".
- Do not use phrases like "the information in the document" or "the content of the document".
- Do not use phrases like "in the document", "from the text", or "according to the information".

**Response Format:**
{
    "questions": [
        "Question 1",
        "Question 2",
        "Question 3",
        "Question 4",
        "Question 5"
    ]
}
"""

QUESTION_SYSTEM_PROMPT = """
You are a helpful assistant that generates a list of 5 questions based directly on specific details from the given document. Ensure that each of the 5 questions can be answered by explicit information found within the document, without using reference words. Your questions must directly reference the content described in the document. Your response must be in the following JSON format without JSON or json at the beginning or end.

**Rules:**
    - Each question must directly reference specific topics, items, or sections mentioned in the document.
    - Each question must be answerable by explicit details found in the document.
    - Avoid broad or vague phrasing. Use clear, specific references based on the document's content.
    - Your questions should aim to extract meaningful information beyond simple recall.
    - Do not use reference phrases such as "this", "the document", or "the information".
    - Do not use phrases like "in the text", "in the document", or "according to the document". Instead, refer directly to specific names, places, subjects, or data points within the document.
    - Keep questions concise and directly tied to the document's content.

**Response Format:**
{
    "questions": [
        "Question 1",
        "Question 2",
        "Question 3",
        "Question 4",
        "Question 5"
    ]
}
"""

def process_university(db: ChromaDB, university_dir: str) -> None:
    """
    Process a university directory and insert its documents into the database
    """

    catalogues_path = opj(university_dir, 'catalogues.txt')

    with open(catalogues_path, 'r') as f:
        filepaths = f.readlines()
    filepaths = [fp.strip() for fp in filepaths]

    print(f'Inserting {len(filepaths)} catalogues for {university_dir}')

    university_name = UNIVERSITY_MAPPING[os.path.basename(university_dir)]

    agent = Agent(
        OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY")),
        'Agent',
        None,
        QUESTION_SYSTEM_PROMPT,
        model='gpt-4o',
        json_mode=True
    )

    filepaths = ['system_data/suny/www.potsdam.edu/sites/default/files/MinorBus_2425.pdf']

    for path in tqdm(filepaths):

        if not os.path.exists(path):
            continue

        filename = os.path.basename(path)
        pages = load_pdf_text(path)
        metadata = {}
        metadata['university'] = university_name
        metadata['filename'] = os.path.basename(path)
        metadata['filepath'] = path

        page_chunks = chunk_pages(pages, chunk_size=100)

        for chunk in page_chunks:

            prompt = 'Generate a list of 5 questions that can be answered by the given document.'
            prompt += '**Document:**\n'
            prompt += chunk['text'] + '\n\n'
            agent.add_message('user', prompt)
            response = agent.invoke()
            questions = response.choices[0].message.content
            questions = json.loads(questions)['questions']
            agent.delete_last_message()

            [print(f'Question {i+1}: {question}') for i, question in enumerate(questions)]
            print('\n----------------------------------------------\n')
            continue

            doc_id = f"{university_name}-{filename}-chunk-{chunk['metadata']['chunk_id']}"
            combined_metadata = {**metadata, **chunk['metadata']}
            #try:
            if 1:

                # Insert the document into the database
                inserted = db.insert_if_not_exists(chunk['text'], doc_id, combined_metadata)
                if inserted:
                    print(f"Inserted new document: {doc_id}")
                    print(f"Metadata: {combined_metadata}")
                else:
                    print(f"Document already exists: {doc_id}")

                # Insert the generated questions into the database
                for idx, question in enumerate(questions[:2]):
                    question_id = f"{doc_id}-question-{idx}"
                    combined_metadata['reference_doc_id'] = doc_id
                    inserted = db.insert_if_not_exists(question, question_id, combined_metadata)
                    if inserted:
                        print(f"Inserted new question: {question_id}")
                    else:
                        print(f"Question already exists: {question_id}")

                    print('\nquestion:', question)
                    print('question_id:', question_id)
                    print('combined_metadata:', combined_metadata)

                    #print('\nreference doc:')
                    #doc = db.get_document_by_id(combined_metadata['reference_doc_id'])
                    #print(doc['id'])
                    #print(doc['metadata'])
                    #print(doc['document'])

                    print('\n----------------------------------------------\n')
                    input()

            #except Exception as e:
            #    print(f'Error processing document {doc_id}: {e}')
            #    print('Metadata:', combined_metadata)
            #    continue


@click.command()
@click.option('--data_dir', type=str, default=None, help='Directory to load data from')
def main(data_dir: str | None):

    if data_dir is None:
        data_dir = UNIVERSITY_DATA_DIR
        single_university = False
    else:
        single_university = True
        university_dir = data_dir

    db = ChromaDB(CHROMA_DB_PATH, 'universities')

    #question = 'Does SUNY Poly offer a degree in Computer Science?'
    #ask_question(db, question)
    #exit()

    if single_university:
        process_university(db, university_dir)
    else:
        for university_dir in os.listdir(data_dir):
            university_dir = opj(data_dir, university_dir)
            if not os.path.isdir(university_dir):
                continue
            process_university(db, university_dir)

    #question = 'What does the third semester of a Agribusiness Management major look like?'
    #question = 'What are the admission requirements for Engineering Science majors?'
    #question = 'Can you tell me about the nursing program?'
    #question = 'Which SUNY schools offer a degreen in Applied Behavior Analysis Studies?'
    #ask_question(db, question)



if __name__ == '__main__':
    main()