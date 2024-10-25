"""
Script to process files and either compute embeddings or insert them into the database for RAG
"""
import os
import re
import json
import uuid
import pickle

from difflib import SequenceMatcher

import click
import requests

from bs4 import BeautifulSoup
from tqdm import tqdm

import pymupdf4llm

from icecream import ic
from openai import OpenAI
from qdrant_client import QdrantClient

from unidecode import unidecode

from src import agent, utils
from src.database import qdrant_db
from src.constants import METADATA_PATH, UNIVERSITY_DATA_DIR

opj = os.path.join


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
    doc_id = doc_id.replace('\\', '/')
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

    if base_url.startswith('/') or base_url.startswith('\\'):
        base_url = base_url[1:]

    base_url = 'https://' + base_url

    base_url = base_url.replace('\\', '/')

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
        base_url + '.cfm'
    ]

    #print('university_name:', university_name)
    #print('file_path:', file_path)
    #print('base_url:', base_url, '\n')
    #[print(x) for x in variants]

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
        except Exception as e:#requests.exceptions.RequestException:
            print('WARNING: Failed to get variant', variant)
            print('Exception:', e)
            continue

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


def get_files(directory: str, extension: str) -> list[str]:
    """
    Recursively search for files with the given extension in the given directory and return their full paths.

    Args:
        directory (str): The root directory to start the search from.
        extension (str): File extension to search for.

    Returns:
        list[str]: A list of full paths to files with the given extension found in the directory and its subdirectories.
    """
    if not extension.startswith('.'):
        extension = '.' + extension

    result_files = []
    for root, _, filenames in os.walk(directory):
        for file in filenames:
            if file.lower().endswith(extension):
                if '?' in file:
                    file2 = file.split('?')[0] + '.html'
                    if os.path.exists(os.path.join(root, file2)):
                        result_files.append(os.path.join(root, file2))
                    else:
                        result_files.append(os.path.join(root, file))
                else:
                    result_files.append(os.path.join(root, file))

    return sorted(list(set(result_files)))


def compute_html_embeddings(
        university_name: str,
        html_files: list[str],
        embedding_model: qdrant_db.EmbeddingModel,
        data_dir: str
    ) -> None:
    """
    Compute embeddings for html files and save to pickle file.

    Args:
        university_name (str): Name of the university.
        html_files (list[str]): List of html files.
        embedding_model (qdrant_db.EmbeddingModel): Embedding model to use.
        data_dir (str): Directory to save pickle files.
    """
    batch_size = 100  # Save embeddings every 10 files
    embeddings_file = os.path.join(data_dir, 'html_embeddings.pkl')

    # Load existing embeddings if file exists
    if os.path.exists(embeddings_file):
        with open(embeddings_file, 'rb') as f:
            embeddings_dict = pickle.load(f)
    else:
        embeddings_dict = {}

    files_processed = 0

    for path in tqdm(html_files):

        doc_id = get_doc_id_from_path(path)
        parent_point_id = str(uuid.uuid4())

        if doc_id in embeddings_dict:
            continue

        print('PATH:', path)
        text = utils.get_text_from_html(path)

        url = get_html_url(university_name, path)

        if url is None:
            print(f"Warning: No corresponding web page found for {path}")
            with open('missing_html_urls.txt', 'a', encoding='utf-8', errors='ignore') as f:
                f.write(path + '\n')

        # Compute embedding for the full text
        parent_vector = embedding_model.embed(text)
        parent_payload = {
            'filepath': path,
            'doc_id': doc_id,
            'university': university_name,
            'type': 'html',
            'url': url,
            'content': text,
            'point_id': parent_point_id,
            'parent_point_id': parent_point_id
        }

        # Process chunks
        text_chunks = utils.chunk_text(text, chunk_size=256, overlap_size=32)

        chunk_embeddings = []
        for chunk_id, chunk_text in enumerate(text_chunks):
            chunk_point_id = str(uuid.uuid4())
            chunk_vector = embedding_model.embed(chunk_text)
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
            chunk_embeddings.append({'vector': chunk_vector, 'payload': chunk_payload})

        # Store embeddings in embeddings_dict
        embeddings_dict[doc_id] = {
            'parent': {'vector': parent_vector, 'payload': parent_payload},
            'chunks': chunk_embeddings
        }

        files_processed += 1

        # Save embeddings_dict every batch_size files
        if files_processed % batch_size == 0:
            with open(embeddings_file, 'wb') as f:
                pickle.dump(embeddings_dict, f)
            print(f"Saved embeddings for {files_processed} files.")

    # Save any remaining embeddings
    with open(embeddings_file, 'wb') as f:
        pickle.dump(embeddings_dict, f)
    print(f"Saved embeddings for total of {len(embeddings_dict)} files.")


def compute_pdf_embeddings(university_name: str, pdf_files: list[str], embedding_model: qdrant_db.EmbeddingModel, data_dir: str) -> None:
    """
    Compute embeddings for pdf files and save to pickle file.

    Args:
        university_name (str): Name of the university.
        pdf_files (list[str]): List of pdf files.
        embedding_model (qdrant_db.EmbeddingModel): Embedding model to use.
        data_dir (str): Directory to save pickle files.
    """
    batch_size = 50  # Save embeddings every 10 files
    embeddings_file = os.path.join(data_dir, 'pdf_embeddings.pkl')

    # Load existing embeddings if file exists
    if os.path.exists(embeddings_file):
        with open(embeddings_file, 'rb') as f:
            embeddings_dict = pickle.load(f)
    else:
        embeddings_dict = {}

    files_processed = 0

    for path in tqdm(pdf_files):

        doc_id = get_doc_id_from_path(path)

        if doc_id in embeddings_dict:
            continue

        parent_point_id = str(uuid.uuid4())

        try:
            text_pages = extract_pdf_pages(path)
        except Exception as e:
            print('WARNING: Could not extract text from', path)
            print(e)
            continue

        full_text = "\n".join([page['text'] for page in text_pages])

        url = 'https:/' + path.split(UNIVERSITY_DATA_DIR)[1]

        # Compute embedding for the full text
        parent_vector = embedding_model.embed(full_text)
        parent_payload = {
            'filepath': path,
            'doc_id': doc_id,
            'university': university_name,
            'type': 'pdf',
            'url': url,
            'content': full_text,
            'point_id': parent_point_id,
            'parent_point_id': parent_point_id
        }

        # Process chunks
        page_chunks = utils.chunk_pages(
            [page['text'] for page in text_pages], chunk_size=256, overlap_size=32
        )

        chunk_embeddings = []
        for chunk_id, chunk in enumerate(page_chunks):
            chunk_point_id = str(uuid.uuid4())
            chunk_vector = embedding_model.embed(chunk['text'])
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
            chunk_embeddings.append({'vector': chunk_vector, 'payload': chunk_payload})

        # Store embeddings in embeddings_dict
        embeddings_dict[doc_id] = {
            'parent': {'vector': parent_vector, 'payload': parent_payload},
            'chunks': chunk_embeddings
        }

        files_processed += 1

        # Save embeddings_dict every batch_size files
        if files_processed % batch_size == 0:
            with open(embeddings_file, 'wb') as f:
                pickle.dump(embeddings_dict, f)
            print(f"Saved embeddings for {files_processed} files.")

    # Save any remaining embeddings
    with open(embeddings_file, 'wb') as f:
        pickle.dump(embeddings_dict, f)
    print(f"Saved embeddings for total of {len(embeddings_dict)} files.")


def insert_html_embeddings(db: qdrant_db.QdrantDB, embeddings_file: str) -> None:
    """
    Load embeddings from pickle file and insert into database.

    Args:
        db (qdrant_db.QdrantDB): Database to insert into.
        embeddings_file (str): Path to embeddings pickle file.
    """
    with open(embeddings_file, 'rb') as f:
        embeddings_dict = pickle.load(f)

    batch_size = 4
    ids = []
    vectors = []
    payloads = []

    for path, data in tqdm(embeddings_dict.items()):

        parent_data = data['parent']
        parent_point_id = parent_data['payload']['point_id']
        doc_id = parent_data['payload']['doc_id']

        # Check if document already exists in database
        if db.point_exists(doc_id):
            print(f'Document {doc_id} already exists.')
            continue

        ids.append(parent_point_id)
        vectors.append(parent_data['vector'])
        payloads.append(parent_data['payload'])

        # Insert parent document embeddings in batches
        if len(ids) >= batch_size:
            db.add_batch(
                collection_name='suny',
                point_ids=ids,
                payloads=payloads,
                vectors=vectors
            )
            ids = []
            vectors = []
            payloads = []

        # Insert chunks
        chunk_ids = []
        chunk_vectors = []
        chunk_payloads = []

        for chunk_data in data['chunks']:
            chunk_ids.append(chunk_data['payload']['point_id'])
            chunk_vectors.append(chunk_data['vector'])
            chunk_payloads.append(chunk_data['payload'])

            if len(chunk_ids) >= batch_size:
                db.add_batch(
                    collection_name='suny',
                    point_ids=chunk_ids,
                    payloads=chunk_payloads,
                    vectors=chunk_vectors
                )
                chunk_ids = []
                chunk_vectors = []
                chunk_payloads = []

        # Insert any remaining chunks
        if chunk_ids:
            db.add_batch(
                collection_name='suny',
                point_ids=chunk_ids,
                payloads=chunk_payloads,
                vectors=chunk_vectors
            )

    # Insert any remaining parent documents
    if ids:
        db.add_batch(
            collection_name='suny',
            point_ids=ids,
            payloads=payloads,
            vectors=vectors
        )


def insert_pdf_embeddings(db: qdrant_db.QdrantDB, embeddings_file: str) -> None:
    """
    Load embeddings from pickle file and insert into database.

    Args:
        db (qdrant_db.QdrantDB): Database to insert into.
        embeddings_file (str): Path to embeddings pickle file.
    """
    with open(embeddings_file, 'rb') as f:
        embeddings_dict = pickle.load(f)

    batch_size = 8
    ids = []
    vectors = []
    payloads = []

    for path, data in tqdm(embeddings_dict.items()):
        parent_data = data['parent']
        parent_point_id = parent_data['payload']['point_id']
        doc_id = parent_data['payload']['doc_id']

        # Check if document already exists in database
        if db.point_exists(doc_id):
            print(f'Document {doc_id} already exists.')
            continue

        ids.append(parent_point_id)
        vectors.append(parent_data['vector'])
        payloads.append(parent_data['payload'])

        # Insert parent document embeddings in batches
        if len(ids) >= batch_size:
            db.add_batch(
                collection_name='suny',
                point_ids=ids,
                payloads=payloads,
                vectors=vectors
            )
            ids = []
            vectors = []
            payloads = []

        # Insert chunks
        chunk_ids = []
        chunk_vectors = []
        chunk_payloads = []

        for chunk_data in data['chunks']:
            chunk_ids.append(chunk_data['payload']['point_id'])
            chunk_vectors.append(chunk_data['vector'])
            chunk_payloads.append(chunk_data['payload'])

            if len(chunk_ids) >= batch_size:
                db.add_batch(
                    collection_name='suny',
                    point_ids=chunk_ids,
                    payloads=chunk_payloads,
                    vectors=chunk_vectors
                )
                chunk_ids = []
                chunk_vectors = []
                chunk_payloads = []

        # Insert any remaining chunks
        if chunk_ids:
            db.add_batch(
                collection_name='suny',
                point_ids=chunk_ids,
                payloads=chunk_payloads,
                vectors=chunk_vectors
            )

    # Insert any remaining parent documents
    if ids:
        db.add_batch(
            collection_name='suny',
            point_ids=ids,
            payloads=payloads,
            vectors=vectors
        )


@click.command()
@click.option('--data_dir', '-d', type=str, default=None, help='Root university directory to process')
@click.option('--university_dir', '-u', type=str, default=None, help='University directory to process. If `None`, processes all universities in data_dir.')
@click.option('--debug', is_flag=True, default=False, help='Run in debug mode')
@click.option('--model', type=click.Choice(['bge-small', 'jina']), default='jina', help='Embedding model')
@click.option('--mode', type=click.Choice(['compute', 'insert']), required=True, help='Mode to run: compute embeddings or insert into database')
def main(data_dir: str | None, university_dir: str | None, debug: bool, model: str, mode: str):

    if data_dir is None and university_dir is None:
        print('Error: data_dir or university_dir must be provided.')
        exit()

    if university_dir is None:
        data_dirs = [opj(data_dir, x) for x in os.listdir(data_dir) if os.path.isdir(opj(data_dir, x))]
    else:
        data_dirs = [university_dir]

    embedding_model = qdrant_db.get_embedding_model(model)

    if mode == 'insert':
        client_qdrant = qdrant_db.get_qdrant_client(host='192.168.0.8')
        db = qdrant_db.QdrantDB(client_qdrant, 'suny', embedding_model.emb_dim)

    for data_dir in data_dirs:

        if data_dir[-1] != os.sep:
            data_dir += os.sep

        if mode == 'compute':
            university_name = os.path.basename(os.path.dirname(data_dir))

            html_files = get_files(data_dir, '.html')
            pdf_files = get_files(data_dir, '.pdf')

            html_files = [x for x in html_files if 'faculty' not in x]
            pdf_files = [x for x in pdf_files if 'faculty' not in x]

            html_files = [x for x in html_files if 'news' not in x]
            pdf_files = [x for x in pdf_files if 'news' not in x]

            html_files = [x for x in html_files if 'events' not in x]
            pdf_files = [x for x in pdf_files if 'events' not in x]

            if len(html_files) > 0:
                print('Computing embeddings for', len(html_files), 'html files...')
                print('University:', university_name, '\n')
                compute_html_embeddings(
                    university_name,
                    html_files,
                    embedding_model,
                    data_dir
                )
            if len(pdf_files) > 0:
                print('Computing embeddings for', len(pdf_files), 'pdf files...')
                compute_pdf_embeddings(university_name, pdf_files, embedding_model, data_dir)

        elif mode == 'insert':

            html_embeddings_file = os.path.join(data_dir, 'html_embeddings.pkl')
            pdf_embeddings_file = os.path.join(data_dir, 'pdf_embeddings.pkl')

            if os.path.exists(html_embeddings_file):
                print('Inserting html embeddings from', html_embeddings_file)
                insert_html_embeddings(db, html_embeddings_file)

            if os.path.exists(pdf_embeddings_file):
                print('Inserting pdf embeddings from', pdf_embeddings_file)
                insert_pdf_embeddings(db, pdf_embeddings_file)


if __name__ == '__main__':
    main()

