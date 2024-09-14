"""
Script to insert files found by scripts/find_relevant_files.py into the database for RAG
"""
import os
import json
import click

from tqdm import tqdm
from openai import OpenAI
from difflib import SequenceMatcher

from src.agent import Agent
from src.database import ChromaDB
from src.pdf_tools import load_pdf_text, chunk_pages, get_pdf_metadata
from src.constants import SUNY_DATA_DIR, UNIVERSITY_DATA_DIR, CHROMA_DB_PATH, UNIVERSITY_MAPPING

opj = os.path.join

SYSTEM_PROMPT = """
You are a helpful assistant that can answer questions about the given document.
Do not use reference words such as "this", "the document", or "the information".
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

def generate_questions(agent: Agent, chunk: dict) -> list[str]:
    prompt = 'Generate a list of 5 questions that can be answered by the given document.'
    prompt += '**Document:**\n'
    prompt += chunk['text'] + '\n\n'
    agent.add_message('user', prompt)
    response = agent.invoke()
    questions = response.choices[0].message.content
    agent.delete_last_message()
    return json.loads(questions)['questions']


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

            doc_id = f"{university_name}-{filename}-chunk-{chunk['metadata']['chunk_id']}"
            combined_metadata = {**metadata, **chunk['metadata']}

            questions = None

            try:

                # Insert the document into the database
                inserted = db.insert_if_not_exists(chunk['text'], doc_id, combined_metadata)
                if inserted:
                    print(f"Inserted new document: {doc_id}")
                    questions = generate_questions(agent, chunk)
                else:
                    print(f"Document already exists: {doc_id}")

                if questions is None:
                    continue

                # Insert the generated questions into the database
                for idx, question in enumerate(questions[:2]):
                    question_id = f"{doc_id}-question-{idx}"
                    combined_metadata['reference_doc_id'] = doc_id
                    inserted = db.insert_if_not_exists(question, question_id, combined_metadata)
                    if inserted:
                        print(f"Inserted new question: {question_id}")
                    else:
                        print(f"Question already exists: {question_id}")

            except Exception as e:
                print(f'Error processing document {doc_id}: {e}')
                print('Metadata:', combined_metadata)
                continue


def remove_overlap(docs):
    """
    Remove overlapping content from a list of document chunks.
    """
    if not docs or len(docs) == 1:
        return docs

    merged_text = docs[0]['document']
    merged_metadata = docs[0]['metadata'].copy()

    for doc in docs[1:]:
        text = doc['document']
        matcher = SequenceMatcher(None, merged_text, text)
        match = matcher.find_longest_match(0, len(merged_text), 0, len(text))
        
        # If there's a significant overlap (e.g., more than 50 characters)
        if match.size > 50:
            # Append only the non-overlapping part
            merged_text += text[match.b + match.size:]
        else:
            # If no significant overlap, just append the whole text
            merged_text += " " + text

        # Update metadata
        merged_metadata.update(doc['metadata'])

    # Create a new merged document
    merged_doc = {
        'document': merged_text,
        'metadata': merged_metadata
    }

    return merged_doc


def ask_question(db, question):

    results = db.collection.query(
        query_texts=[question],
        n_results=2
    )
    print(results, '\n')

    res_ids = results['ids'][0]
    res_ids = [id.split('-question')[0] for id in res_ids]

    docs = []
    for rid1 in res_ids:
        chunk_id = int(rid1.split('-chunk-')[-1])

        # Get the chunks before and after the current chunk
        if chunk_id != 0:
            rid2 = rid1.split('-chunk-')[0] + f'-chunk-{chunk_id - 1}'
            rid3 = rid1.split('-chunk-')[0] + f'-chunk-{chunk_id + 1}'
            doc1 = db.get_document_by_id(rid2)
            doc2 = db.get_document_by_id(rid1)
            doc3 = db.get_document_by_id(rid3)
            doc = remove_overlap([doc1, doc2, doc3])
        else:
            # No chunk before, only the current chunk and the chunk after
            doc1 = db.get_document_by_id(rid1)
            rid2 = rid1.split('-chunk-')[0] + f'-chunk-{chunk_id + 1}'
            doc2 = db.get_document_by_id(rid2)
            doc = remove_overlap([doc1, doc2])

        docs.append(doc)

    docs_content = '\n\n'.join([doc['document'] for doc in docs])

    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    agent = Agent(client, 'Agent', None, SYSTEM_PROMPT, model='gpt-4o', json_mode=False)

    prompt = 'Answer the following question given the available information.\n\n'
    prompt += '**Question:**\n'
    prompt += question + '\n\n'
    prompt += '**Information:**\n'
    prompt += docs_content
    #for result in results:
    #    prompt += f'**University:** {result["metadata"]["university"]}\n'
    #    prompt += f'**Document:** {result["document"]}\n\n'
    #    prompt += f'**Document ID:** {result["id"]}\n\n'
    #    prompt += '---'

    agent.add_message('user', prompt)

    #print('Question:', question, '\n')
    print('Prompt:')
    print(prompt, '\n')
    response = agent.invoke()
    print('Answer:', response.choices[0].message.content)


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

    if single_university:
        process_university(db, university_dir)
    else:
        for university_dir in os.listdir(data_dir):
            university_dir = opj(data_dir, university_dir)
            if not os.path.isdir(university_dir):
                continue
            process_university(db, university_dir)

    question = 'Does SUNY Potsdam offer a degree in Music?'
    question = 'What coursework is involved in a music degree at the crane school of music?'
    ask_question(db, question)
    #print('\n===========================================\n')
    #question = 'Can you give me more information on the Crane School of Music?'
    #ask_question(db, question)
    exit()


    #question = 'What does the third semester of a Agribusiness Management major look like?'
    #question = 'What are the admission requirements for Engineering Science majors?'
    #question = 'Can you tell me about the nursing program?'
    #question = 'Which SUNY schools offer a degreen in Applied Behavior Analysis Studies?'
    #ask_question(db, question)



if __name__ == '__main__':
    main()