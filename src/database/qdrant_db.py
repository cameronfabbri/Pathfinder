"""
"""
# Cameron Fabbri
import os
import json
import pickle

from typing import List
from functools import lru_cache

import numpy as np

from fastembed import TextEmbedding
from FlagEmbedding import FlagReranker

from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams
from qdrant_client.http.models import (FieldCondition, Filter, MatchValue,
                                       PointStruct)

from src import utils
from src.constants import METADATA_PATH, UNIVERSITY_DATA_DIR

opj = os.path.join


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

    def add_batch(
            self,
            collection_name: str,
            point_ids: List[str],
            payloads: List[dict],
            vectors: List[np.ndarray]) -> None:
        """ """

        self.client.upsert(
            collection_name=collection_name,
            points=models.Batch(
                ids=point_ids,
                payloads=payloads,
                vectors=vectors,
            ),
        )

    def add_document(
            self,
            embedding: np.ndarray,
            collection_name: str,
            point_id: str,
            payload: dict = None
        ) -> None:
        """
        Add a document to the collection.

        Args:
            embedding (np.ndarray): The embedding of the document.
            collection_name (str): The name of the collection.
            doc_id (str): The ID of the document.
            metadata (dict): The metadata of the document.
        """

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

    def point_exists(self, doc_id: str) -> bool:
        """
        Check if a point with the given doc_id exists in the collection.
        """
        existing_points = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="doc_id", match=MatchValue(value=doc_id))
                ]
            ),
            limit=1
        )[0]
        if existing_points:
            return True
        return False

    def get_document_by_id(self, point_id: str):
        """
        Get a document by its ID.
        """
        result = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id]
        )
        return result[0]

    def query(
            self,
            collection_name: str,
            query_vector: np.ndarray,
            university: str | None = None,
            limit: int = 1):
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

        return self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=filter,
            limit=limit
        )


class EmbeddingModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        if model_name == 'bge-small':
            self.embedding_model = TextEmbedding(
                model_name="BAAI/bge-small-en-v1.5")
            self.emb_dim = 384
            self.max_tokens = 512
        elif model_name == 'jina':
            self.embedding_model = TextEmbedding(
                model_name="jinaai/jina-embeddings-v2-base-en")
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

def get_openai_embedding(
        client, text, model="text-embedding-3-small"):
    return client.embeddings.create(input=[text], model=model).data[0].embedding


def get_fastembed_embedding(
        text: List[str], embedding_model: TextEmbedding) -> List[np.ndarray]:
    return list(embedding_model.embed(text))


def get_embedding_model(model: str) -> EmbeddingModel:
    return EmbeddingModel(model)


def get_qdrant_client(host: str = "localhost", port: int = 6333) -> QdrantClient:
    return QdrantClient(host=host, port=port)


def get_qdrant_db(client: QdrantClient, collection_name: str, emb_dim: int) -> QdrantDB:
    return QdrantDB(client, collection_name, emb_dim)


def get_reranker(model: str='BAAI/bge-reranker-v2-m3') -> FlagReranker:
    return FlagReranker(model, use_fp16=True)


def main():

    #client_qdrant = QdrantClient(
    #    url="https://b3a175dd-76e6-47e4-a90e-0b76f8f3c526.europe-west3-0.gcp.cloud.qdrant.io:6333",
    #    api_key="bEnJ-0g3rj4waAA3Ep9M7bcxSQXhH7VtJvkWuAjvxZmB3H4gi6DqhQ",
    #)
    #client_qdrant = QdrantClient(path=QDRANT_DB_PATH)
    client = QdrantClient(host="localhost", port=6333)

    qdrant_db = QdrantDB(client, 'suny', 786)

    import uuid
    import random
    import string

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
