"""
ChromaDB vector database
"""
# Cameron Fabbri
from typing import Any, Dict, List

import chromadb

from chromadb.config import DEFAULT_DATABASE, DEFAULT_TENANT, Settings


class ChromaDB:
    def __init__(self, path: str, name: str, distance_metric: str = "cosine"):
        """
        Initialize the ChromaDB client and collection.

        Args:
            path (str): The path to the ChromaDB data directory.
            distance_metric (str): The distance metric to use for the collection.
        """
        self.client = chromadb.PersistentClient(
            path=path,
            settings=Settings(),
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE,
        )

        self.collection = self.client.get_or_create_collection(
            name=name, metadata={"hnsw:space": distance_metric}
        )

    @staticmethod
    def sanitize_metadata(metadata: dict) -> dict:
        def sanitize_value(value: Any) -> str:
            if isinstance(value, (str, int, float, bool)):
                return value
            elif value is None:
                return ''
            else:
                return str(value)

        return {key: sanitize_value(value) for key, value in metadata.items()}

    def insert_if_not_exists(self, content: str, doc_id: str, metadata: Dict[Any, Any]) -> bool:
        """
        Insert a document into the collection if it does not already exist.

        Args:
            content (str): The content of the document.
            doc_id (str): The ID of the document.
            metadata (dict): The metadata of the document.
        Returns:
            bool: True if the document was added, False otherwise.
        """
        if not self.document_exists(doc_id):
            sanitized_metadata = self.sanitize_metadata(metadata)
            self.add_document(content=content, doc_id=doc_id, metadata=sanitized_metadata)
            return True
        else:
            print(f"Document {doc_id} already exists.")
        return False

    def document_exists(self, doc_id: str) -> bool:
        """
        Check if a document exists in the collection.

        Args:
            doc_id (str): The ID of the document to check.
        Returns:
            bool: True if the document exists, False otherwise.
        """
        results = self.collection.get(ids=[doc_id], include=['metadatas'])
        return len(results['ids']) > 0

    def add_document(
            self, content, doc_id: str, metadata: dict = None, user_id=None, verbose=False) -> None:
        """
        Add a document to the collection.

        Args:
            content (str): The content of the document.
            doc_id (str): The ID of the document.
            metadata (dict): The metadata of the document.
            user_id (int): The ID of the user.
            verbose (bool): Whether to print verbose output.
        Returns:
            None
        """
        if metadata is None:
            metadata = {}

        if user_id:
            metadata["access"] = "private"
            metadata["user_id"] = user_id
        else:
            metadata["access"] = "public"

        # Add document to ChromaDB
        self.collection.add(
            ids=[doc_id],  # Unique identifier for the document
            documents=[content],  # Document content
            metadatas=[metadata],  # Access control metadata
        )
        if verbose:
            print(f"Document added successfully with ID: {doc_id}")

    def get_document_by_id(self, doc_id: str):
        """
        Retrieve a document from the collection by its doc_id.

        Args:
            doc_id (str): The ID of the document to retrieve.
        Returns:
            dict: A dictionary containing the document's content, metadata, and embeddings (if available).
                  Returns None if the document is not found.
        """
        try:
            result = self.collection.get(
                ids=[doc_id],
                include=['documents', 'metadatas', 'embeddings']
            )
            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'document': result['documents'][0] if result['documents'] else None,
                    'metadata': result['metadatas'][0] if result['metadatas'] else None,
                    #'embedding': result['embeddings'][0] if result['embeddings'] else None
                }
            else:
                return None
        except Exception as e:
            print(f"{doc_id} not found: {e}")
            return ''

    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the collection to retrieve the most similar documents to the query text.

        Args:
            query_text (str): The text to query.
            top_k (int): The number of top results to return.

        Returns:
            List[Dict[str, Any]]: A list of documents with their content, metadata, and distances.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )

        documents = []
        for i in range(len(results['documents'][0])):
            documents.append({
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
            })
        return documents
