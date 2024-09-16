"""
"""

import os
from openai import OpenAI
from typing import List, Dict, Any

from src.agent import Agent
from src.database import ChromaDB
from src.constants import CHROMA_DB_PATH


class RAG:
    def __init__(self, agent: Agent, db: ChromaDB, top_k: int = 5):
        """
        Initialize the RAG (Retrieval Augmented Generation) class.

        Args:
            agent (Agent): An instance of the Agent class.
            db (ChromaDB): An instance of the ChromaDB class.
            top_k (int): The number of top documents to retrieve for context.
        """
        self.agent = agent
        self.db = db
        self.top_k = top_k

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from the database using the query.

        Args:
            query (str): The user's query.

        Returns:
            List[Dict[str, Any]]: A list of relevant documents with metadata.
        """
        #results = self.db.query(query_text=query, top_k=self.top_k)
        return self.db.collection.query(
            query_texts=[query],
            n_results=self.top_k,
            include=['documents', 'metadatas', 'distances'],
            where={"university": "Alfred University"}
        )

    def generate(self, query: str) -> str:
        """
        Generate a response using Retrieval Augmented Generation.

        Args:
            query (str): The user's query.

        Returns:
            str: The generated response.
        """
        # Retrieve relevant documents
        documents = self.retrieve(query)

        # Format the retrieved documents to include in the prompt
        context = self.format_documents(documents)

        # Add the context to the agent's messages
        self.agent.add_message("system", f"Use the following context to answer the user's question:\n{context}")

        # Add the user's query
        self.agent.add_message("user", query)

        print(context, '\n')

        # Invoke the agent to generate a response
        response = self.agent.invoke()

        # Extract the assistant's reply
        reply = response.choices[0].message.content

        # Optionally, remove the last messages to reset the context
        self.agent.delete_last_message()  # Remove user message
        self.agent.delete_last_message()  # Remove system message with context

        return reply

    def format_documents(self, documents: List[Dict[str, Any]]) -> str:
        """
        Format the retrieved documents into a string to be included in the prompt.

        Args:
            documents (List[Dict[str, Any]]): The retrieved documents.

        Returns:
            str: The formatted documents.
        """
        content_doc_ids = []
        for doc_id in documents['ids'][0]:

            # Document is a full HTML page
            if '.pdf' not in doc_id and 'chunk' not in doc_id:
                content_doc_ids.append(doc_id)

            # Chunk of an HTML file
            elif '.pdf' not in doc_id and 'chunk' in doc_id:
                content_doc_ids.append(doc_id.split('-chunk')[0])

            # Full PDF page
            elif '.pdf' in doc_id and 'chunk' not in doc_id:
                content_doc_ids.append(doc_id)

            # Chunk of a pdf page - we want to get the whole page(s)
            elif '.pdf' in doc_id and 'chunk' in doc_id:
                doc_id_base = doc_id.split('-chunk')[0]

                doc = self.db.get_document_by_id(doc_id)
                start_page = str(doc['metadata']['start_page'])
                end_page = str(doc['metadata']['end_page'])

                # chunk spans multiple pages
                if start_page != end_page:
                    doc_id1 = doc_id_base + '-page-' + start_page
                    doc_id2 = doc_id_base + '-page-' + end_page
                    content_doc_ids.append(doc_id1)
                    content_doc_ids.append(doc_id2)
                else:
                    doc_id1 = doc_id_base + '-page-' + start_page
                    content_doc_ids.append(doc_id1)

        content = ''
        for x in content_doc_ids:
            doc = self.db.get_document_by_id(x)
            if 'filepath' in doc['metadata'].keys():
                content += 'Filepath: ' + doc['metadata']['filepath'] + '\n'
            if 'page_number' in doc['metadata'].keys():
                content += 'Page Number: ' + str(doc['metadata']['page_number']) + '\n'
            content += doc['document'] + '\n\n'
        return content


def main():

    # Initialize the ChromaDB instance
    db = ChromaDB(path=CHROMA_DB_PATH, name='universities')

    # Initialize the Agent instance
    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    agent = Agent(
        client=client,
        name='assistant',
        tools=None,
        system_prompt="You are a helpful assistant.",
        model='gpt-4',
        json_mode=False,
        temperature=0.7
    )

    # Initialize the RAG instance
    rag = RAG(agent=agent, db=db, top_k=3)

    # Generate a response using RAG
    query = "What undergraduate programs are offered at the University of Albany?\n\n"
    query = 'For the school of art and design at Alfred University, what are the portfolio requirements for applying?'
    query = 'For the school of art and design, what are the portfolio requirements for applying?'
    response = rag.generate(query)

    print("Assistant's Response:")
    print(response)

if __name__ == "__main__": 
    main()