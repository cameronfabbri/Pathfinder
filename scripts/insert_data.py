"""
Script to insert files found by scripts/find_relevant_files.py into the database for RAG
"""
import os
import re
import json
import uuid
import click
import requests
import pymupdf4llm

from tqdm import tqdm
from openai import OpenAI
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from qdrant_client import QdrantClient

from src import agent
from src import utils
from src.database import qdrant_db
from src.constants import UNIVERSITY_DATA_DIR, METADATA_PATH

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


def get_doc_id_from_path(path: str) -> str:
    """
    Get the document id from the path

    Args:
        path (str): The path to the document.
    Returns:
        str: The document id.
    """
    doc_id = path.split(UNIVERSITY_DATA_DIR)[-1]
    if doc_id.startswith(os.sep):
        doc_id = doc_id[1:]
    return doc_id


def get_html_url(university_name: str, file_path: str) -> str | None:
    """
    Try and get the URL of the HTML file
     
    Args:
        file_path (str): The local path to the HTML file.
    Returns:
        str: The valid URL (with or without .html) or None.
    """
    
    # Extract base URL from the file path by removing the root directory and file extension
    base_url = file_path.split(university_name)[1].replace('.html', '')
    if base_url.startswith('/'):
        base_url = base_url[1:]

    base_url = 'https://' + base_url

    # TODO - look if .cfm is in the URL, I had wget --adjust-extension so they all
    # turned from index.cfm to index.cfm.html

    variants = [
        base_url.rstrip('/index') + '/',
        base_url,
        base_url + '.html',
        base_url + '/index.html',
        base_url + '/index.php',
        base_url + '/index.php.html',
        base_url.rstrip('/index'),
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Referer': base_url,
        'Accept-Language': 'en-US,en;q=0.9',
    }

    for variant in variants:
        try:
            response = requests.get(variant, headers=headers)
            if response.status_code == 200:
                return variant
        except requests.exceptions.RequestException:
            pass

    return None


def select_files(root_directory: str, instructions: dict) -> dict:
    """
    Select the files to insert into the database

    Args:
        root_directory (str): The root directory to search for files.
        instructions (dict): The instructions for selecting files.
    Returns:
        dict: The selected files.
    """
    include_in_path = instructions.get('include_in_path', [])
    exclude_from_path = instructions.get('exclude_from_path', [])
    file_extensions = instructions.get('file_extensions', [])
    selected_files = {'html_files': [], 'pdf_files': []}

    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            if any(filename.endswith(ext) for ext in file_extensions):
                file_path = os.path.join(dirpath, filename)
                # Normalize the file path for consistent string matching
                normalized_path = os.path.normpath(file_path)
                include = not include_in_path or all(pattern in normalized_path for pattern in include_in_path)
                exclude = any(pattern in normalized_path for pattern in exclude_from_path)
                if include and not exclude:
                    if filename.endswith('.html'):
                        selected_files['html_files'].append(file_path)
                    elif filename.endswith('.pdf'):
                        selected_files['pdf_files'].append(file_path)
    return selected_files


def generate_questions(agent: agent.Agent, chunk: dict) -> list[str]:
    prompt = 'Generate a list of 5 questions that can be answered by the given document.'
    prompt += '**Document:**\n'
    prompt += chunk['text'] + '\n\n'
    agent.add_message('user', prompt)
    response = agent.invoke()
    questions = response.choices[0].message.content
    agent.delete_last_message()
    return json.loads(questions)['questions']


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
    agent = agent.Agent(client, 'Agent', None, SYSTEM_PROMPT, model='gpt-4o', json_mode=False)

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


def get_html_metadata(html_file: str) -> dict:
    """
    Get the metadata from an html file.

    Args:
        html_file (str): The path to the html file.
    Returns:
        dict: The metadata of the html file.
    """
    metadata = {}

    with open(html_file, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    metadata['title'] = soup.title.string.strip().replace('\xa0', ' ') if soup.title else ''

    description = soup.find('meta', attrs={'name': 'description'})
    metadata['description'] = description['content'].strip() if description else ''

    keywords = soup.find('meta', attrs={'name': 'keywords'})
    metadata['keywords'] = keywords['content'].strip() if keywords else ''

    # Check for h1 to h6
    metadata['headers'] = {}
    for i in range(1, 7):
        headers = [header.get_text().strip() for header in soup.find_all(f'h{i}')]
        if headers:
            metadata['headers'][f'h{i}'] = headers

    metadata['language'] = soup.html.get('lang', '')

    return metadata


def extract_pdf_pages(pdf_file: str) -> list[str]:
    """
    Extract the text from each page of a pdf file as a list of strings.

    Args:
        pdf_file (str): The path to the pdf file.
        text_type (str): The type of text to extract. Defaults to 'text'.
        text, html, dict, json, xml, blocks, words, xhtml
    Returns:
        list[str]: A list of strings, one for each page of the pdf file.
    """
    return pymupdf4llm.to_markdown(pdf_file, page_chunks=True)


def insert_pdf_files(
        db: qdrant_db.QdrantDB,
        university_name: str,
        pdf_files: list[str],
        embedding_model: qdrant_db.EmbeddingModel) -> None:
    """
    Insert the pdf files into the database.

    Args:
        db (qdrant_db.QdrantDB): The database to insert the documents into.
        university_name (str): The name of the university.
        pdf_files (list[str]): The list of pdf files to insert.
        embedding_model (qdrant_db.EmbeddingModel): The embedding model to use.
    Returns:
        None
    """

    batch_size = 16

    ids = []
    vectors = []
    payloads = []

    for path in tqdm(pdf_files):

        doc_id = get_doc_id_from_path(path)
        parent_point_id = str(uuid.uuid4())

        if db.point_exists(doc_id):
            print(f'Document {doc_id} already exists.')
            continue

        url = 'https:/' + path.split(UNIVERSITY_DATA_DIR)[1]

        text_pages = extract_pdf_pages(path)
        full_text = "\n".join([page['text'] for page in text_pages])

        payloads.append(
            {
                'filepath': path,
                'doc_id': doc_id,
                'university': university_name,
                'type': 'pdf',
                'url': url,
                'content': full_text,
                'point_id': parent_point_id,
                'parent_point_id': parent_point_id
            }
        )
        ids.append(parent_point_id)
        vectors.append(embedding_model.embed(full_text))

        if len(payloads) >= batch_size:
            db.add_batch(
                collection_name='suny',
                point_ids=ids,
                payloads=payloads,
                vectors=vectors
            )
            payloads = []
            vectors = []
            ids = []

        # Insert chunks into the database
        page_chunks = utils.chunk_pages([page['text'] for page in text_pages], chunk_size=256, overlap_size=32)

        chunk_payloads = []
        chunk_vectors = []
        chunk_ids = []
        for chunk_id, chunk in enumerate(page_chunks):
            chunk_point_id = str(uuid.uuid4())
            chunk_payload = {
                'filepath': path,
                'doc_id': doc_id,
                'university': university_name,
                'type': 'pdf',
                'url': url,
                'point_id': chunk_point_id,
                'parent_point_id': parent_point_id,
                'chunk_id': chunk_id,
                'content': chunk['text'],
                'start_page': chunk['metadata']['start_page'],
                'end_page': chunk['metadata']['end_page']
            }
            chunk_payloads.append(chunk_payload)
            chunk_vectors.append(embedding_model.embed(chunk['text']))
            chunk_ids.append(chunk_point_id)

        if chunk_payloads:
            db.add_batch(
                collection_name='suny',
                point_ids=chunk_ids,
                payloads=chunk_payloads,
                vectors=chunk_vectors
            )

    # Insert remaining payloads if len(payloads) < batch_size
    if payloads:
        db.add_batch(
            collection_name='suny',
            point_ids=ids,
            payloads=payloads,
            vectors=vectors
        )


def insert_html_files(
        db: qdrant_db.QdrantDB,
        university_name: str,
        html_files: list[str],
        embedding_model: qdrant_db.EmbeddingModel) -> None:
    """
    Insert the html files into the database

    Args:
        db (qdrant_db.QdrantDB): The database to insert the documents into.
        university_name (str): The name of the university.
        html_files (list[str]): The list of html files to insert.
        embedding_model (qdrant_db.EmbeddingModel): The embedding model to use.
        debug (bool): Run in debug mode.
    Returns:
        None
    """

    batch_size = 16

    ids = []
    vectors = []
    payloads = []

    for path in tqdm(html_files):

        doc_id = get_doc_id_from_path(path)
        parent_point_id = str(uuid.uuid4())

        if db.point_exists(doc_id):
            print(f'Document {doc_id} already exists.')
            continue

        url = get_html_url(university_name, path)
        if url is None:
            print(f"Warning: No corresponding web page found for {path}")
            with open('missing_html_urls.txt', 'a') as f:
                f.write(path + '\n')

        text = utils.get_text_from_html(path)

        payloads.append(
            {
                'filepath': path,
                'doc_id': doc_id,
                'university': university_name,
                'type': 'html',
                'url': url,
                'content': text,
                'point_id': parent_point_id,
                'parent_point_id': parent_point_id
            }
        )
        ids.append(parent_point_id)
        vectors.append(embedding_model.embed(text))

        if len(payloads) >= batch_size:
            db.add_batch(
                collection_name='suny',
                point_ids=ids,
                payloads=payloads,
                vectors=vectors
            )
            payloads = []
            vectors = []
            ids = []

        # Insert chunks into the database
        text_chunks = utils.chunk_text(text, chunk_size=256, overlap_size=32)

        chunk_payloads = []
        chunk_vectors = []
        chunk_ids = []
        for chunk_id, chunk_text in enumerate(text_chunks):
            chunk_point_id = str(uuid.uuid4())
            chunk_payload = {
                'filepath': path,
                'doc_id': doc_id,
                'university': university_name,
                'type': 'html',
                'url': url,
                'point_id': chunk_point_id,
                'parent_point_id': parent_point_id,
                'chunk_id': chunk_id,
                'content': chunk_text
            }
            chunk_payloads.append(chunk_payload)
            chunk_vectors.append(embedding_model.embed(chunk_text))
            chunk_ids.append(chunk_point_id)

        if chunk_payloads:
            db.add_batch(
                collection_name='suny',
                point_ids=chunk_ids,
                payloads=chunk_payloads,
                vectors=chunk_vectors
            )

    # Insert the remaining payloads if len(payloads) < batch_size
    if payloads:
        db.add_batch(
            collection_name='suny',
            point_ids=ids,
            payloads=payloads,
            vectors=vectors
        )


@click.command()
@click.option('--data_dir', '-d', type=str, default=None, help='Root university directory to process')
@click.option('--debug', is_flag=True, default=False, help='Run in debug mode')
@click.option('--model', type=click.Choice(['bge-small', 'jina']), default='jina', help='Embedding model')
def main(data_dir: str | None, debug: bool, model: str):

    embedding_model = qdrant_db.get_embedding_model(model)
    client_qdrant = qdrant_db.get_qdrant_client()
    db = qdrant_db.QdrantDB(client_qdrant, 'suny', embedding_model.emb_dim)

    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)

    university_name = os.path.basename(data_dir)

    if university_name not in metadata:
        print(f"Warning: University {university_name} not found in metadata")
        exit()

    html_files = []
    for directory in metadata[university_name]['html_directories']:
        directory = opj(UNIVERSITY_DATA_DIR, metadata[university_name]['root_directory'], directory)
        html_files.extend(utils.get_files(directory, '.html'))

    pdf_files = []
    for directory in metadata[university_name]['pdf_directories']:
        directory = opj(UNIVERSITY_DATA_DIR, metadata[university_name]['root_directory'], directory)
        pdf_files.extend(utils.get_files(directory, '.pdf'))
    for file in metadata[university_name]['pdf_files']:
        pdf_files.append(opj(UNIVERSITY_DATA_DIR, metadata[university_name]['root_directory'], file))
    pdf_files = sorted(list(set(pdf_files)))

    if len(pdf_files) > 0:
        print('Inserting', len(pdf_files), 'pdf files...')
        insert_pdf_files(db, university_name, pdf_files, embedding_model)
    if len(html_files) > 0:
        print('Inserting', len(html_files), 'html files...')
        insert_html_files(db, university_name, html_files, embedding_model)


if __name__ == '__main__':
    main()