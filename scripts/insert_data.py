"""
Script to insert files found by scripts/find_relevant_files.py into the database for RAG
"""
import os
import click

from tqdm import tqdm

from src.database import ChromaDB
from src.pdf_tools import load_pdf_text, chunk_pages, get_pdf_metadata

from openai import OpenAI
from src.agent import Agent

opj = os.path.join

from typing import Dict, Any

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
In your answer, reference every Document ID  you use as a reference. Your answer
should be in the following JSON format without ```JSON

{
    "answer": "...",
    "document_ids": [
        "...",
        "..."
    ]
}

"""
def ask_question(db, question):

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


def sanitize_metadata(metadata):
    def sanitize_value(value):
        if isinstance(value, (str, int, float, bool)):
            return value
        elif value is None:
            return ''
        else:
            return str(value)

    return {key: sanitize_value(value) for key, value in metadata.items()}


def document_exists(db, doc_id: str) -> bool:
    results = db.collection.get(ids=[doc_id], include=['metadatas'])
    return len(results['ids']) > 0

def insert_if_not_exists(db, content: str, doc_id: str, metadata: Dict[Any, Any]):
    if not document_exists(db, doc_id):
        sanitized_metadata = sanitize_metadata(metadata)
        db.add_document(content=content, doc_id=doc_id, metadata=sanitized_metadata)
        return True
    return False


def main():

    data_dir = opj('system_data', 'suny')
    db_path = opj('system_data', 'chromadb')

    db = ChromaDB(db_path, 'universities')
    
    #question = 'Does SUNY Poly offer a degree in Computer Science?'
    #ask_question(db, question)
    #exit()

    for school in os.listdir(data_dir):

        school_name = school.replace('www.', '').replace('.edu', '')
        school_dir = opj(data_dir, school)
        if not os.path.isdir(school_dir):
            continue

        catalogues_path = opj(school_dir, 'catalogues.txt')

        if not os.path.exists(catalogues_path):
            print(f'No catalogues found for {school}')
            continue

        with open(catalogues_path, 'r') as f:
            filepaths = f.readlines()
        filepaths = [fp.strip() for fp in filepaths]

        print(f'Inserting {len(filepaths)} catalogues for {school}')

        for path in tqdm(filepaths):

            if not os.path.exists(path):
                continue

            filename = os.path.basename(path)
            pages = load_pdf_text(path)
            metadata = {}
            metadata['university'] = school_name
            metadata['filename'] = os.path.basename(path)
            metadata['filepath'] = path

            page_chunks = chunk_pages(pages, chunk_size=500)

            for chunk in page_chunks:
                doc_id = f"{school_name}-{filename}-chunk-{chunk['metadata']['chunk_id']}"
                combined_metadata = {**metadata, **chunk['metadata']}
                try:
                    inserted = insert_if_not_exists(db, chunk['text'], doc_id, combined_metadata)
                    if inserted:
                        print(f"Inserted new document: {doc_id}")
                    else:
                        print(f"Document already exists: {doc_id}")
                except Exception as e:
                    print(f'Error processing document {doc_id}: {e}')
                    print('Metadata:', combined_metadata)
                    continue

    question = 'What does the third semester of a Agribusiness Management major look like?'
    question = 'What are the admission requirements for Engineering Science majors?'
    question = 'Can you tell me about the nursing program?'
    question = 'Which SUNY schools offer a degreen in Applied Behavior Analysis Studies?'
    ask_question(db, question)



if __name__ == '__main__':
    main()