"""
Tests for qdrant functionality.
"""

import uuid
import random
import string

from qdrant_client import QdrantClient

import src

from src.database.qdrant_db import QdrantDB


def test_collections():
    """Test that expected collections exist in the db."""

    client = QdrantClient(host="localhost", port=6333)

    qdrant_db = QdrantDB(client, 'suny', 786)

    print(client.get_collection('suny'), '\n')

    print(qdrant_db.point_exists(1))


