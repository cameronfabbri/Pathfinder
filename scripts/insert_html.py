"""
"""

import os
import re

from openai import OpenAI
from bs4 import BeautifulSoup

from src.agent import Agent
from src.database import ChromaDB
from src.constants import CHROMA_DB_PATH

#path = '/Users/cameronfabbri/Projects/Pathfinder/system_data/suny/sunyacc.smartcatalogiq.com/en/24-25/college-catalog/academic-programs/computer-science-as-cmps.html'

def chunk_text(text, chunk_size=500, overlap_percentage=25):
    """
    Split text into chunks with a specified overlap percentage, preserving formatting.

    Args:
        text (str): The input text to be chunked.
        chunk_size (int): The target size of each chunk in words. Defaults to 500.
        overlap_percentage (int): The percentage of overlap between chunks. Defaults to 25.

    Returns:
        list[dict]: A list of dictionaries, each containing the chunk text and metadata.
    """
    overlap_size = int(chunk_size * (overlap_percentage / 100))
    stride = chunk_size - overlap_size

    # Split text into words while preserving formatting
    words = re.findall(r'\S+|\s+', text)
    total_words = len(words)

    chunks = []
    start_word = 0
    while start_word < total_words:
        end_word = min(start_word + chunk_size, total_words)
        
        chunk_text = ''.join(words[start_word:end_word])
        
        chunk_info = {
            "text": chunk_text,
            "metadata": {
                "chunk_id": len(chunks),
                "start_word": start_word,
                "end_word": end_word,
                "word_count": end_word - start_word
            }
        }
        chunks.append(chunk_info)

        start_word += stride

    # If the last chunk is too small, merge it with the previous one
    if len(chunks) > 1 and chunks[-1]["metadata"]["word_count"] < chunk_size // 2:
        chunks[-2]["text"] += chunks[-1]["text"]
        chunks[-2]["metadata"]["end_word"] = chunks[-1]["metadata"]["end_word"]
        chunks[-2]["metadata"]["word_count"] += chunks[-1]["metadata"]["word_count"]
        chunks.pop()

    return chunks


def ask_question(db, question):

    results = db.collection.query(
        query_texts=[question],
        n_results=2
    )

    full_text = ''
    for chunk_ids in results['ids']:
        for chunk_id in chunk_ids:
            # Extract the full page ID (without the chunk number)
            full_page_id = '-'.join(chunk_id.split('-chunk-')[:-1])

            # Retrieve the full page content
            full_page = db.get_document_by_id(full_page_id)
            if full_page and 'document' in full_page:
                full_text += 'Title: ' + full_page['metadata']['title'] + '\n\n'
                full_text += full_page['document'] + '\n\n'
    
    system_prompt = 'You are a helpful assistant that answers questions.'
    agent = Agent(
        OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY")),
        'Agent',
        None,
        system_prompt,
        model='gpt-4o',
        json_mode=False
    )

    prompt = 'Answer the following question given the available information.\n\n'
    prompt += '**Question:**\n'
    prompt += question + '\n\n'
    prompt += '**Information:**\n'
    prompt += full_text
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


def main():
    data_dir = '/Users/cameronfabbri/Projects/Pathfinder/system_data/suny/sunyacc.smartcatalogiq.com/en/24-25/college-catalog/academic-programs/'

    html_files = []
    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    print(f"Found {len(html_files)} HTML files:")

    db = ChromaDB(CHROMA_DB_PATH, 'sunyacc')

    university_name = 'SUNY Adirondack'

    for path in html_files:

        filename = os.path.basename(path)

        with open(path, 'r') as f:
            soup = BeautifulSoup(f, 'lxml')

        # Remove all <script> tags
        for script in soup(["script"]):
            script.extract()

        text = re.sub(r'\n{3,}', '\n\n', soup.get_text()).strip()
        title = soup.title.string.strip().replace('\xa0', ' ')

        # Insert the full document into the database
        doc_id = f"{university_name}-{filename}"
        metadata = {
            'filepath': path,
            'title': title,
            'university': university_name
        }
        inserted = db.insert_if_not_exists(text, doc_id, metadata)
        if inserted:
            print(f"Inserted new document: {doc_id}")

        # Insert chunks into the database
        text_chunks = chunk_text(text, chunk_size=500, overlap_percentage=25)
        for chunk in text_chunks:
            doc_id = f"{university_name}-{filename}-chunk-{chunk['metadata']['chunk_id']}"
            chunk['metadata']['filepath'] = path
            chunk['metadata']['title'] = title
            chunk['metadata']['university'] = university_name

            document = chunk['text']
            metadata = chunk['metadata']
            inserted = db.insert_if_not_exists(document, doc_id, metadata)
            if inserted:
                print(f"Inserted new document: {doc_id}")

    ask_question(db, 'Can you tell me about the Culinary Arts program?')


if __name__ == '__main__':
    main()