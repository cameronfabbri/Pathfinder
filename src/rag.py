"""
RAG (Retrieval Augmented Generation) class for retrieving and formatting documents from a QdrantDB instance.
"""
from FlagEmbedding import FlagReranker
from typing import Any, Dict, List, Tuple

from src.database import qdrant_db


class RAG:
    def __init__(
            self,
            db: qdrant_db.QdrantDB,
            embedding_model: qdrant_db.EmbeddingModel,
            reranker: FlagReranker = None,
            top_n: int = 20,
            top_k: int = 5
        ):
        """
        Initialize the RAG (Retrieval Augmented Generation) class.

        Args:
            db (QdrantDB): An instance of the QdrantDB class.
            embedding_model (EmbeddingModel): An instance of the src.database.qdrant_db.EmbeddingModel class.
            top_n (int): The number of top documents to retrieve to pass to the reranker.
            top_k (int): The number of top documents to return after reranking for context.
            reranker (FlagReranker): An instance of the FlagReranker class.
        """
        self.db = db
        self.top_k = top_k
        self.top_n = top_n
        self.embedding_model = embedding_model
        self.reranker = reranker

    def retrieve(self, query_text: str, school_name: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from the database using the query.

        Args:
            query (str): The user's query.
            school_name (str | None): The name of the school to retrieve documents for.
            doc_type (str | None): The type of document to retrieve. Only include this if the user's question is about a specific type of document.
            Valid values are 'html' or 'pdf'
        Returns:
            List[Dict[str, Any]]: A list of relevant documents with metadata.
        """
        query_vector = self.embedding_model.embed(query_text)

        return self.db.query(
            collection_name='suny',
            query_vector=query_vector,
            university=school_name,
            limit=self.top_n,
        )

    def rerank(self, query_text, search_results):
        """
        Rerank the search results using the given query text and query vector.
        """

        # Compute scores for all results
        scored_results = []
        for result in search_results:
            score = self.reranker.compute_score([query_text, result.payload.get('content')], normalize=True)
            scored_results.append((result, score))
        
        # Sort results by score in descending order
        sorted_results = [y[0] for y in sorted(scored_results, key=lambda x: x[1], reverse=True)]

        return sorted_results[:self.top_k]

    def run(self, query_text: str, school_name: str = None) -> str:
        """
        Run the RAG pipeline.
        """
        search_results = self.retrieve(query_text, school_name)
        reranked_results = self.rerank(query_text, search_results)
        return self.format_documents(reranked_results)

    def format_documents(self, documents) -> str:
        """
        Format the retrieved documents into a string to be included in the prompt.
        """

        doc_ids = []
        filtered_docs = []
        for doc in documents:
            doc = doc.dict()

            # TODO - revisit this maybe
            if doc['payload']['type'] == 'pdf' and 'chunk_id' not in doc['payload']:
                continue

            if doc['payload']['parent_point_id'] not in doc_ids:
                doc_ids.append(doc['payload']['parent_point_id'])
                filtered_docs.append(doc)

        content = ''
        print('Doc IDs:', doc_ids)
        for doc in filtered_docs:

            # Match was a chunk, get the full parent document
            # In the case of HTML, the parent document is the whole webpage.
            # In the case of PDF, the parent document is the page the chunk was taken from.
            if 'chunk_id' in doc['payload'] and doc['payload']['type'] == 'html':
                doc = self.db.get_document_by_id(doc['payload']['parent_point_id']).dict()

            content += 'University: ' + doc['payload']['university'] + '\n'
            content += 'URL: ' + str(doc['payload']['url']) + '\n'
            content += 'Content: ' + doc['payload']['content'] + '\n\n'

        return content
