"""
Constants for the application.
"""
# Cameron Fabbri
import os
from functools import lru_cache
from src import personas

opj = os.path.join

SQL_DB_DIR = opj('data', 'sql_dbs')
    
PERSONA_PROMPT = personas.DAVID + '\n\n' + personas.DAVID_TRAITS

FASTEMBED_CACHE_DIR = opj('data', 'fastembed')

SYSTEM_DATA_DIR = opj('/Volumes', 'External', 'system_data')

QDRANT_DB_PATH = opj('data', 'qdrantdb')
SUNY_DATA_DIR = opj(SYSTEM_DATA_DIR, 'general')
UNIVERSITY_DATA_DIR = opj(SYSTEM_DATA_DIR, 'suny')

METADATA_PATH = opj('data', 'metadata.json')

EXCLUDE = ['meeting', 'blog', 'news', 'events', 'calendar', 'faculty', '\\uf03f', '?', '_archive', 'alumni']

# Number of threads to use for downloading files using wget2
MAX_DOWNLOAD_THREADS = 9

@lru_cache(maxsize=None)
def get_university_names():
    with open(opj('data', 'university_names.txt'), 'r') as f:
        return [line.strip() for line in f.readlines()]

UNIVERSITY_NAMES = get_university_names()
