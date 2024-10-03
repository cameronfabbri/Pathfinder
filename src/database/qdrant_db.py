"""
Vector database that uses Faiss for storing and querying vectors.
"""
# Cameron Fabbri

import os
import re
import json
import faiss
import numpy as np

from bs4 import BeautifulSoup
from openai import OpenAI

import pickle
from tqdm import tqdm
from qdrant_client.models import VectorParams, Distance
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client import QdrantClient

from fastembed import TextEmbedding
from typing import List

from src import utils
from src.constants import METADATA_PATH, UNIVERSITY_MAPPING, UNIVERSITY_DATA_DIR, QDRANT_DB_PATH
from src.utils import chunk_pages, chunk_text


opj = os.path.join


def get_openai_embedding(client, text, model="text-embedding-3-small"):
    return client.embeddings.create(input=[text], model=model).data[0].embedding


def get_fastembed_embedding(text: List[str], embedding_model: TextEmbedding) -> List[np.ndarray]:
    return list(embedding_model.embed(text))


class QdrantDB:
    """
    Vector database that uses Qdrant for storing and querying vectors.
    """
    def __init__(self, client, collection_name: str, emb_dim: int):
        self.client = client
        self.collection_name = collection_name
        self.emb_dim = emb_dim

        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=emb_dim, distance=Distance.COSINE),
            )

    def add_document(
            self,
            content: str,
            embedding: np.ndarray,
            collection_name: str,
            point_id: str,
            payload: dict = None
        ):
        """
        Add a document to the collection.

        Args:
            content (str): The content of the document.
            embedding (np.ndarray): The embedding of the document.
            collection_name (str): The name of the collection.
            doc_id (str): The ID of the document.
            metadata (dict): The metadata of the document.
        """

        payload['content'] = content
        payload['id'] = point_id

        self.client.upsert(
            collection_name=collection_name,
            wait=True,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            ],
        )

    def point_exists(self, point_id: str) -> bool:
        """
        Check if a point with the given ID exists in the collection.
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )
            return len(result) > 0
        except Exception as e:
            print(f"Error checking if point exists: {e}")
            return False

    def query(self, collection_name: str, query_vector: np.ndarray, university: str | None = None, limit: int = 1):
        """
        Query the database for the given query vector and optional university filter.

        Args:
            collection_name (str): The name of the collection.
            query_vector (np.ndarray): The query vector.
            university (str | None): The name of the university. Defaults to None.
            limit (int): The number of results to return. Defaults to 1.
        Returns:
            List[Dict[str, Any]]: A list of relevant documents with metadata.
        """
        filter = None
        if university is not None:
            filter = Filter(
                must=[
                    FieldCondition(
                        key="university",
                        match=MatchValue(value=university)
                    )
                ]
            )

        search_result1 = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=filter,
            limit=limit
        )
        return search_result1
    

class EmbeddingModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        if model_name == 'bge-small':
            self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            self.emb_dim = 384
            self.max_tokens = 512
        elif model_name == 'jina':
            self.embedding_model = TextEmbedding(model_name="jinaai/jina-embeddings-v2-base-en")
            self.emb_dim = 768
            self.max_tokens = 8192

    def embed(self, text: str) -> np.ndarray:

        num_tokens = utils.count_tokens(text)

        if num_tokens > self.max_tokens:

            # Chunk the text with an overlap of 20 words
            words = text.split()
            chunks = []
            for i in range(0, len(words), self.max_tokens - 20):
                chunk = ' '.join(words[max(0, i-20):i+self.max_tokens])
                chunks.append(chunk)

            # Get embeddings for each chunk
            chunk_embeddings = [list(self.embedding_model.embed(chunk))[0] for chunk in chunks]
            
            # Average the embeddings
            avg_embedding = np.mean(chunk_embeddings, axis=0)
            
            return list(avg_embedding)

        return list(self.embedding_model.embed(text))[0]

def main():

    #client_qdrant = QdrantClient(
    #    url="https://b3a175dd-76e6-47e4-a90e-0b76f8f3c526.europe-west3-0.gcp.cloud.qdrant.io:6333", 
    #    api_key="bEnJ-0g3rj4waAA3Ep9M7bcxSQXhH7VtJvkWuAjvxZmB3H4gi6DqhQ",
    #)
    #client_qdrant = QdrantClient(path=QDRANT_DB_PATH)
    client = QdrantClient(host="localhost", port=6333)

    qdrant_db = QdrantDB(client, 'suny', 786)

    import random
    import string
    import uuid

    for i in range(10):

        text = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=random.randint(50, 99)))

        emb = np.random.rand(786)
        qdrant_db.add_document(
            content=text,
            embedding=emb,
            collection_name='suny',
            doc_id=i,
            payload={'university': 'SUNY Adirondack'}
        )
    print(client.get_collection('suny'), '\n')

    print(qdrant_db.point_exists(1))

    exit()

    qdrant_db = QdrantDB(client_qdrant, 'suny')

    university = 'SUNY Adirondack'
    html_file = '/Volumes/External/system_data/suny/sunyacc.smartcatalogiq.com/en/24-25/college-catalog/academic-programs/culinary-arts-aas-cart.html'

    ids, texts, embeddings = process_html_files([html_file], None)
    print(len(ids))
    print(len(texts))
    print(len(embeddings))
    with open('data.pkl', 'wb') as f:
        pickle.dump((ids, texts, embeddings), f)
    exit()
    for uid, text, embedding in zip(ids, texts, embeddings):
        print(uid)
        print(text)
        print('\n', '-'*100, '\n')
        input('Press Enter to continue...')

    exit()

    client = utils.get_openai_client()

    text = 'Hello world my name is Cameron Fabbri'
    embedding = get_openai_embedding(client, text)

    print('operation_info:', operation_info, '\n')

    universities = ['Alfred University', 'Clinton Community College']

    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)

    all_files = []
    for university_name, data in metadata.items():
        if university_name not in universities:
            continue

        files = {
            'html_files': data.get('html_files', []),
            'pdf_files': data.get('pdf_files', [])
        }

        # Process files based on processing instructions
        if 'processing_instructions' in data and data['processing_instructions']:
            # Add root directory from src.constants
            root_directory = opj(UNIVERSITY_DATA_DIR, data.get('root_directory'))
            if root_directory:
                selected_files = select_files(
                    root_directory=root_directory,
                    instructions=data['processing_instructions']
                )
                files['html_files'].extend(selected_files.get('html_files', []))
                files['pdf_files'].extend(selected_files.get('pdf_files', []))
            else:
                print(f"Warning: Root directory not specified for {university_name}")

        #print('University:', university_name)
        #print('HTML files:', len(files['html_files']))
        #print('PDF files:', len(files['pdf_files']))

        embeddings = process_html_files(files['html_files'], client)

    #print(embeddings[0] @ embeddings[1].T)
    exit()


if __name__ == '__main__':
    main()