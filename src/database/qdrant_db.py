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
from src.constants import FASTEMBED_CACHE_DIR, QDRANT_URL, QDRANT_API_KEY

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
                model_name="BAAI/bge-small-en-v1.5",
                cache_dir=FASTEMBED_CACHE_DIR)
            self.emb_dim = 384
            self.max_tokens = 512
        elif model_name == 'jina':
            self.embedding_model = TextEmbedding(
                model_name="jinaai/jina-embeddings-v2-base-en",
                cache_dir=FASTEMBED_CACHE_DIR)
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


def get_local_qdrant_client(host: str = "localhost", port: int = 6333) -> QdrantClient:
    return QdrantClient(host=host, port=port)


def get_remote_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def get_qdrant_db(client: QdrantClient, collection_name: str, emb_dim: int) -> QdrantDB:
    return QdrantDB(client, collection_name, emb_dim)


def get_reranker(model: str='BAAI/bge-reranker-v2-m3') -> FlagReranker:
    return FlagReranker(model, use_fp16=True)
