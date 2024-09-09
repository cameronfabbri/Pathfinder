import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings


class ChromaDB:
    def __init__(self, path, distance_metric: str = "cosine"):
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

        self.collection = self.client.get_or_create_collection(name="documents", metadata={"hnsw:space": distance_metric})

    def add_document(self, content, doc_id: str, user_id=None):
        
        if user_id:
            metadata = {"access": "private", "user_id": user_id}
        else:
            metadata = {"access": "public"}
         
        # Add document to ChromaDB
        self.collection.add(
            ids=[doc_id],  # Unique identifier for the document
            documents=[content],  # Document content
            metadatas=[metadata],  # Access control metadata
        )
        print(f"Document added successfully with ID: {doc_id}")



from qdrant_client import QdrantClient
client = QdrantClient(path="path/to/db")