"""
RAG (Retrieval Augmented Generation) class for retrieving and formatting documents from a ChromaDB instance.
"""

from typing import List, Dict, Any, Tuple

from src.database.chroma_db import ChromaDB


class RAG:
    def __init__(self, db: ChromaDB, top_k: int = 5):
        """
        Initialize the RAG (Retrieval Augmented Generation) class.

        Args:
            db (ChromaDB): An instance of the ChromaDB class.
            top_k (int): The number of top documents to retrieve for context.
        """
        self.db = db
        self.top_k = top_k

    def retrieve(self, query: str, school_name: str = None, doc_type: str = None) -> List[Dict[str, Any]]:
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
        where = {}
        if school_name is not None:
            where['university'] = school_name
        if doc_type is not None:
            where['doc_type'] = doc_type

        return self.db.collection.query(
            query_texts=[query],
            n_results=self.top_k,
            include=['documents', 'metadatas', 'distances'],
            where=where
        )

    def format_documents(self, documents: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """
        Format the retrieved documents into a string to be included in the prompt.

        Args:
            documents (List[Dict[str, Any]]): The retrieved documents.

        Returns:
            Tuple[str, List[str]]: The formatted documents and the document IDs.
        """

        #print('Retrieved Documents:')
        #[print(x) for x in documents['ids'][0]]
        #print('-' * 100)
        content_doc_ids = []
        for doc_id in documents['ids'][0]:

            # Document is a full HTML page
            if '.pdf' not in doc_id and 'chunk' not in doc_id:
                if doc_id not in content_doc_ids:
                    content_doc_ids.append(doc_id)

            # Chunk of an HTML file
            elif '.pdf' not in doc_id and 'chunk' in doc_id:
                if doc_id.split('-chunk')[0] not in content_doc_ids:
                    content_doc_ids.append(doc_id.split('-chunk')[0])

            # Full PDF page
            elif '.pdf' in doc_id and 'chunk' not in doc_id:
                if doc_id not in content_doc_ids:
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
                    if doc_id1 not in content_doc_ids:
                        content_doc_ids.append(doc_id1)
                    if doc_id2 not in content_doc_ids:
                        content_doc_ids.append(doc_id2)
                else:
                    doc_id1 = doc_id_base + '-page-' + start_page
                    if doc_id1 not in content_doc_ids:
                        content_doc_ids.append(doc_id1)

        #print('CONTENT DOC IDS:')
        #[print(x) for x in content_doc_ids]
        #print('\n-\n')

        content = ''
        for x in content_doc_ids:
            doc = self.db.get_document_by_id(x)
            #if 'filepath' in doc['metadata'].keys():
            #    content += 'Filepath: ' + doc['metadata']['filepath'] + '\n'
            if 'url' in doc['metadata'].keys():
                content += 'URL: ' + doc['metadata']['url'] + '\n'
            if 'page_number' in doc['metadata'].keys():
                content += 'Page Number: ' + str(doc['metadata']['page_number']) + '\n'
            content += doc['document'] + '\n\n'

        #print('CONTENT:')
        #print(content)

        return content#, content_doc_ids

