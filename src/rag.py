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
            top_n: int = 20,
            top_k: int = 5,
            reranker: FlagReranker = None,
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

    def retrieve(self, query_text: str, school_name: str = None, doc_type: str = None) -> List[Dict[str, Any]]:
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


if __name__ == '__main__':
    import time
    import qdrant_client
    client = qdrant_client.QdrantClient(host="localhost", port=6333)
    db = qdrant_db.QdrantDB(client, 'suny', 786)
    embedding_model = qdrant_db.EmbeddingModel('jina')

    query_text = 'Who is the chair of the Computer and Information Technology department at Alfred University?'
    query_text = 'Which colleges offer a degree in Arabic?'
    school_name = None
    #school_name = 'Binghamton University'
    #school_name = 'Alfred State College'

    reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)
    rag = RAG(db, embedding_model, top_n=20, top_k=5, reranker=reranker)
    res = rag.retrieve(query_text, school_name=school_name)

    res = rag.rerank(query_text, search_results=res)

    for r in res:
        print(r.payload.get('filepath'))
        print(r.payload.get('start_page'), '-', r.payload.get('end_page'))
        print(r.payload.get('university'))
        print(r.payload.get('type'))
        print(r.payload.get('url'))
        print('\n----------------------------------------------------------\n')
        input()
