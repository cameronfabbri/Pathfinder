import os
from functools import lru_cache

opj = os.path.join

SYSTEM_DATA_DIR = opj('/Volumes', 'External', 'system_data')

SUNY_DATA_DIR = opj(SYSTEM_DATA_DIR, 'general')
CHROMA_DB_PATH = opj(SYSTEM_DATA_DIR, 'chromadb')
UNIVERSITY_DATA_DIR = opj(SYSTEM_DATA_DIR, 'suny')

@lru_cache(maxsize=None)
def get_university_mapping():
    return {
        'www.sunyacc.edu': 'SUNY Adirondack',
        'sunyacc.smartcatalogiq.com': 'SUNY Adirondack',
        'www.alfred.edu': 'Alfred University',
        'catalog.alfredstate.edu': 'Alfred State College',
        'www.alfredstate.edu': 'Alfred State College',
        'www.albany.edu': 'University at Albany',
        'www.binghamton.edu': 'Binghamton University',
        'www.clinton.edu': 'Clinton Community College',
        'suny.oneonta.edu': 'SUNY Oneonta',
        'www.nccc.edu': 'Niagara County Community College',
        'www.potsdam.edu': 'SUNY Potsdam',
        'www.sunydutchess.edu': 'Dutchess Community College',
        'www.sunypoly.edu': 'SUNY Polytechnic Institute',
        'www.tompkinscortland.edu': 'Tompkins Cortland Community College',
        'www.oldwestbury.edu': 'SUNY Old Westbury',
        'www.stonybrook.edu': 'Stony Brook University',
        'www.sunyocc.edu': 'Onondaga Community College',
        'www.sunyulster.edu': 'SUNY Ulster',
        'www.upstate.edu': 'SUNY Upstate Medical University',
        'www.canton.edu': 'SUNY Canton',
        'www.plattsburgh.edu': 'SUNY Plattsburgh',
        'www.sunyopt.edu': 'SUNY College of Optometry',
        'www.sunywcc.edu': 'Westchester Community College',
        'www1.sunybroome.edu': 'SUNY Broome'
    }

UNIVERSITY_MAPPING = get_university_mapping()

METADATA_PATH = opj('data', 'metadata.json')
