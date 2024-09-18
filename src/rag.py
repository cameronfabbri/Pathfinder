"""
"""

import os
from openai import OpenAI
from typing import List, Dict, Any

from src.database import ChromaDB
from src.constants import CHROMA_DB_PATH


class RAG:
    def __init__(self, db: ChromaDB, top_k: int = 5):
        """
        Initialize the RAG (Retrieval Augmented Generation) class.

        Args:
            agent (Agent): An instance of the Agent class.
            db (ChromaDB): An instance of the ChromaDB class.
            top_k (int): The number of top documents to retrieve for context.
        """
        self.db = db
        self.top_k = top_k

    def retrieve(self, query: str, school_name: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from the database using the query.

        Args:
            query (str): The user's query.
            school_name (str | None): The name of the school to retrieve documents for.
        Returns:
            List[Dict[str, Any]]: A list of relevant documents with metadata.
        """
        where = None
        if school_name is not None:
            where = {"university": school_name}

        return self.db.collection.query(
            query_texts=[query],
            n_results=self.top_k,
            include=['documents', 'metadatas', 'distances'],
            where=where
        )

    def format_documents(self, documents: List[Dict[str, Any]]) -> str:
        """
        Format the retrieved documents into a string to be included in the prompt.

        Args:
            documents (List[Dict[str, Any]]): The retrieved documents.

        Returns:
            str: The formatted documents.
        """

        print('Retrieved Documents:')
        [print(x) for x in documents['ids'][0]]
        print('-' * 100)
        content_doc_ids = []
        #content_doc_ids = documents['ids'][0]
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
    #rag = RAG(agent=agent, db=db, top_k=3)

    # Generate a response using RAG
    #query = "What undergraduate programs are offered at the University of Albany?\n\n"
    #query = 'For the school of art and design at Alfred University, what are the portfolio requirements for applying?'
    #query = 'For the school of art and design, what are the portfolio requirements for applying?'
    #query = 'What coursework is required for a Chinese Studies major at Binghamton University?'
    #response = rag.generate(query)

    #print("Assistant's Response:")
    #print(response)

if __name__ == "__main__": 
    main()