"""
"""

import os

from src.rag import RAG
from src.database import ChromaDB
from src.constants import CHROMA_DB_PATH

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


def retrieve_content_from_question(question: str, school_name: str = None) -> str:
    """
    Retrieve relevant content from the database based on the user's question.

    Args:
        question (str): The user's question about SUNY schools or programs.
        school_name (str, optional): The name of the SUNY school. Only include this if the user's question is about a specific school.

    Returns:
        str: The generated response.
    """
    # Initialize the ChromaDB instance
    db = ChromaDB(path=CHROMA_DB_PATH, name='universities')

    # Initialize the RAG instance
    rag = RAG(db=db, top_k=3)
    documents = rag.retrieve(question, school_name)

    # Format the retrieved documents to include in the prompt
    context = rag.format_documents(documents)

    return context


function_map = {
    "retrieve_content_from_question": retrieve_content_from_question
}
