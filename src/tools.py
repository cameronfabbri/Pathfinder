"""
"""
import os

from functools import lru_cache

from src.rag import RAG
from src.database import qdrant_db

opj = os.path.join

suny_tools = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_content_from_question",
            "description": "Retrieve relevant content from the database based on the user's question. Call this if a user asks a question about a specific school or program.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The user's question about SUNY schools or programs.",
                    },
                    "school_name": {
                        "type": "string",
                        "description": "The name of the SUNY school. Only include this if the user's question is about a specific school. If it is not, do not include it.",
                    },
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        }
    }
]


@lru_cache(maxsize=1)
def get_db_and_reranker():
    model = 'jina'
    embedding_model = qdrant_db.get_embedding_model(model)
    client_qdrant = qdrant_db.get_remote_qdrant_client()
    db = qdrant_db.get_qdrant_db(client_qdrant, 'suny', embedding_model.emb_dim)
    reranker = qdrant_db.get_reranker()
    return db, embedding_model, reranker


def retrieve_content_from_question(
        question: str,
        school_name: str = None) -> str:
    """
    Retrieve relevant content from the database based on the user's question.

    Args:
        question (str): The user's question about SUNY schools or programs.
        school_name (str, optional): The name of the SUNY school. Only include
        this if the user's question is about a specific school.
    Returns:
        str: The formatted documents.
    """

    db, embedding_model, reranker = get_db_and_reranker()

    # Initialize the RAG instance
    rag = RAG(db=db, top_n=30, top_k=5, embedding_model=embedding_model, reranker=reranker)

    return rag.run(question, school_name)


function_map = {
    "retrieve_content_from_question": retrieve_content_from_question
}
