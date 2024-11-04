"""
Tests for RAG module.
"""

from FlagEmbedding import FlagReranker
from typing import Any, Dict, List, Tuple

from src.database import qdrant_db
from src.rag import RAG


def test_rag():

    model = 'jina'
    embedding_model = qdrant_db.get_embedding_model(model)
    client_qdrant = qdrant_db.get_qdrant_client()
    reranker = qdrant_db.get_reranker()
    db = qdrant_db.get_qdrant_db(client_qdrant, 'suny', embedding_model.emb_dim)
    rag = RAG(db=db, embedding_model=embedding_model, reranker=reranker, top_n=20, top_k=5)

    query_text = 'Who is the chair of the Computer and Information Technology department at Alfred University?'
    query_text = 'Which colleges offer a degree in Arabic?'
    query_text = 'Culinary and Baking Arts'
    query_text = 'In addition to textbook expenses, students in the Culinary Arts program are expected to purchase uniforms ($100+) and a knife set ($300+).'
    school_name = None
    # school_name = 'Binghamton University'
    # school_name = 'Alfred State College'

    res = rag.run(query_text, school_name)
    print(res)
    exit()
    for point in res:
        point_dict = point.dict()
        print(point_dict)
        # print(point_dict['payload'].keys(), '\n')
        # print('ID:', point_dict['payload']['id'])
        # print('Chunk ID:', point_dict['payload']['chunk_id'])
        # print('Point ID:', point_dict['payload']['point_id'])
        # print('Parent Point ID:', point_dict['payload']['parent_point_id'])
        # print('ID1:', point_dict['id'])
        # print('Title:', point_dict['payload']['title'])
        # print(r.payload.get('filepath'))
        # print(r.payload.get('start_page'), '-', r.payload.get('end_page'))
        # print(r.payload.get('university'))
        # print(r.payload.get('type'))
        # print(r.payload.get('url'))
        print('\n----------------------------------------------------------\n')
        input()