"""
Script to insert files found by scripts/find_relevant_files.py into the database for RAG
"""
import os
import re
import fitz
import json
import click
import requests

from tqdm import tqdm
from openai import OpenAI
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

from src.agent import Agent
from src.database import ChromaDB
from src.pdf_tools import load_pdf_text
from src.utils import chunk_pages, chunk_text
from src.constants import UNIVERSITY_DATA_DIR, CHROMA_DB_PATH, UNIVERSITY_MAPPING, METADATA_PATH

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

    metadata['source_url'] = soup.find('link', rel='canonical')['href'] if soup.find('link', rel='canonical') else ''

    return metadata


def extract_pdf_pages(pdf_file: str, text_type: str = 'text') -> list[str]:
    """
    Extract the text from each page of a pdf file as a list of strings.

    Args:
        pdf_file (str): The path to the pdf file.
        text_type (str): The type of text to extract. Defaults to 'text'.
        text, html, dict, json, xml, blocks, words, xhtml
    Returns:
        list[str]: A list of strings, one for each page of the pdf file.
    """
    pages_text = []
    
    with fitz.open(pdf_file) as doc:
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text(text_type)
            pages_text.append(text)
    
    return pages_text


def insert_pdf_files(db: ChromaDB, university_name: str, pdf_files: list[str], debug: bool) -> None:
    """
    Insert the pdf files into the database

    Args:
        db (ChromaDB): The database to insert the documents into.
        university_name (str): The name of the university.
        pdf_files (list[str]): The list of pdf files to insert.
    Returns:
        None
    """
    for path in tqdm(pdf_files):

        if not os.path.exists(path):
            continue

        # TODO - remove table of contents pages

        doc_id = get_doc_id_from_path(path)
        pages = extract_pdf_pages(path, 'text')
        metadata = {
            'university': university_name,
            'filepath': path,
        }

        url = get_html_url(path)
        if url is None:
            print(f"Warning: No corresponding web page found for {path}")
            with open('missing_html_urls.txt', 'a') as f:
                f.write(path + '\n')
            continue

        # Insert each page as a separate document before chunking
        for page_num, page_text in enumerate(pages):
            page_num += 1
            page_id = doc_id + f'-page-{page_num}'
            metadata['page_number'] = page_num
            metadata['type'] = 'pdf'
            if not debug:
                db.insert_if_not_exists(page_text, page_id, metadata)
            else:
                print(f"[DEBUG] Inserted page: {page_id}")

        page_chunks = chunk_pages(pages, chunk_size=128, overlap_size=16)

        for chunk in page_chunks:
            chunk_id = doc_id + f"-chunk-{chunk['metadata']['chunk_id']}"
            chunk['metadata']['filepath'] = path
            chunk['metadata']['university'] = university_name
            chunk['metadata']['type'] = 'pdf'
            if not debug:
                db.insert_if_not_exists(chunk['text'], chunk_id, chunk['metadata'])
            else:
                print(f"[DEBUG] Inserted chunk: {chunk_id}")

                #inserted = db.insert_if_not_exists(chunk['text'], doc_id, combined_metadata)
                #if inserted:
                #    print(f"Inserted new document: {doc_id}")
                    #questions = generate_questions(agent, chunk)
                #else:
                #    print(f"Document already exists: {doc_id}")

#                if questions is None:
#                    continue

                # Insert the generated questions into the database
                #for idx, question in enumerate(questions[:2]):
                #    question_id = f"{doc_id}-question-{idx}"
                    #combined_metadata['reference_doc_id'] = doc_id
                    #inserted = db.insert_if_not_exists(question, question_id, combined_metadata)
                #    if inserted:
                #        print(f"Inserted new question: {question_id}")
                #    else:
                #        print(f"Question already exists: {question_id}")



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


def insert_html_files(
        db: ChromaDB,
        university_name: str,
        html_files: list[str],
        debug: bool) -> None:
    """
    Insert the html files into the database

    Args:
        db (ChromaDB): The database to insert the documents into.
        university_name (str): The name of the university.
        html_files (list[str]): The list of html files to insert.
        debug (bool): Run in debug mode.
    Returns:
        None
    """

    for path in tqdm(html_files):

        doc_id = get_doc_id_from_path(path)
        if db.document_exists(doc_id):
            print(f"Document {doc_id} already exists.")
            continue

        url = get_html_url(path)
        if url is None:
            print(f"Warning: No corresponding web page found for {path}")
            with open('missing_html_urls.txt', 'a') as f:
                f.write(path + '\n')
            continue

        with open(path, 'r') as f:
            soup = BeautifulSoup(f, 'lxml')

        # Remove all <script> tags
        for script in soup(["script"]):
            script.extract()

        text = re.sub(r'\n{3,}', '\n\n', soup.get_text()).strip()

        metadata = get_html_metadata(path)

        # Insert the full document into the database
        metadata['filepath'] = path
        metadata['university'] = university_name
        metadata['type'] = 'html'
        metadata['url'] = url
        if not debug:
            db.insert_if_not_exists(text, doc_id, metadata)
        else:
            print(f"[DEBUG] Inserted html: {doc_id}")

        # Insert chunks into the database
        text_chunks = chunk_text(text, chunk_size=512, overlap_size=20)
        
        for chunk in text_chunks:
            chunk_id = doc_id + f"-chunk-{chunk['metadata']['chunk_id']}"
            chunk['metadata']['filepath'] = path
            chunk['metadata']['university'] = university_name
            chunk['metadata']['type'] = 'html'
            chunk['metadata']['url'] = url
            if not debug:
                db.insert_if_not_exists(chunk['text'], chunk_id, chunk['metadata'])
            else:
                print(f"[DEBUG] Inserted chunk: {chunk_id}")


def get_html_url(file_path: str) -> str | None:
    """
    Try and get the URL of the HTML file
     
    Args:
        file_path (str): The local path to the HTML file.
    Returns:
        str: The valid URL (with or without .html) or None.
    """
    
    # Extract base URL from the file path by removing the root directory and file extension
    base_url = file_path.split(UNIVERSITY_DATA_DIR)[1].replace('.html', '')
    if base_url.startswith('/'):
        base_url = base_url[1:]

    base_url = 'https://' + base_url

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


@click.command()
@click.option('--data_dir', '-d', type=str, default=None, help='University directory to process')
@click.option('--general_data_dir', '-gd', type=str, default=None, help='General data directory to process')
@click.option('--debug', is_flag=True, default=False, help='Run in debug mode')
def main(data_dir: str | None, general_data_dir: str | None, debug: bool):

    if general_data_dir is not None and data_dir is not None:
        print("Error: Cannot specify both data_dir and general_data_dir")
        exit(1)

    db = ChromaDB(CHROMA_DB_PATH, 'universities')

    if general_data_dir is not None:
        selected_files = [opj(general_data_dir, x) for x in os.listdir(general_data_dir)]

        print(selected_files)
        exit()


    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)

    for university_name, data in metadata.items():

        if data_dir is not None:
            if university_name != UNIVERSITY_MAPPING[os.path.basename(data_dir)]:
                print('Skipping', university_name)
                continue

        files = {
            'html_files': data.get('html_files', []),
            'pdf_files': data.get('pdf_files', [])
        }

        # Process files based on processing instructions
        if 'processing_instructions' in data and data['processing_instructions']:
            root_directory = data.get('root_directory')
            if root_directory:
                selected_files = select_files(
                    root_directory=root_directory,
                    instructions=data['processing_instructions']
                )
                files['html_files'].extend(selected_files.get('html_files', []))
                files['pdf_files'].extend(selected_files.get('pdf_files', []))
            else:
                print(f"Warning: Root directory not specified for {university_name}")

        if files['html_files']:
            print('Inserting HTML files for', university_name, '...')
            insert_html_files(db, university_name, files['html_files'], debug)
        if files['pdf_files']:
            print('Inserting PDF files for', university_name, '...')
            insert_pdf_files(db, university_name, files['pdf_files'], debug)


if __name__ == '__main__':
    main()