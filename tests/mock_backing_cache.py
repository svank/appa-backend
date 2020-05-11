"""
Contains author & document records in dict() form for self-contained testing
"""

import contextlib
import copy
import time
from collections import defaultdict
from unittest.mock import MagicMock

import path_finder
from ads_name import ADSName
from cache_buddy import CacheMiss

# Monkey-patch path_finder to recognize our bibcodes
path_finder.is_bibcode = lambda x: x.startswith("paper")


r"""
The authorship graph:
           D -- J -- I
           |         |
 K -- A == B == C == F -- H
 |    |    \\  //
 L    E ---- G

"""

TIME = int(time.time())

empty_document = {
    'doctype': 'article', 'keywords': [],
    'publication': 'mock', 'pubdate': 'never',
    'citation_count': 0, 'read_count': 0,
    'timestamp': TIME}

documents = {
    'paperAB': {
        'title': 'Paper Linking A & B',
        'authors': ['Author, A.', 'Author, Bbb'],
        'affils': ['Univ of A', 'B Center'],
        'orcid_ids': [],
        'orcid_id_src': '',
        **empty_document
    },
    'paperAB2': {
        'title': 'Second Paper Linking A & B',
        'authors': ['Author, B.', 'Author, Aaa'],
        'affils': ['Univ of B', 'A Institute'],
        'orcid_ids': ['ORCID B'],
        'orcid_id_src': '3',
        **empty_document
    },
    'paperAE': {
        'title': 'Paper Linking A & E',
        'authors': ['Author, Aaa', 'Author, Eee E.'],
        'affils': ['A Institute', 'E Center for E'],
        'orcid_ids': [],
        'orcid_id_src': '',
        **empty_document
    },
    'paperAK': {
        'title': 'Paper Linking A & K',
        'authors': ['Author, Aaa', 'Author, K.'],
        'affils': ['A Institute', 'K Center for K'],
        'orcid_ids': [],
        'orcid_id_src': '',
        **empty_document
    },
    'paperBC': {
        'title': 'Paper Linking B & C',
        'authors': ['Author, C.', 'Author, B.'],
        'affils': ['University of C', 'Univ of B'],
        'orcid_ids': ['', 'ORCID B'],
        'orcid_id_src': '0,1',
        **empty_document
    },
    'paperBCG': {
        'title': 'Paper Linking B, C & G',
        'authors': ['Author, Bbb', 'Author, C. C.', 'Author, G.'],
        'affils': ['B Institute', 'Univ. C', 'G Center for G'],
        'orcid_ids': ['Not ORCID B'],
        'orcid_id_src': '1',
        **empty_document
    },
    'paperBD': {
        'title': 'Paper Linking B & D',
        'authors': ['Author, B.', 'Author, D.'],
        'affils': ['B Institute', 'D Center for D'],
        'orcid_ids': ['ORCID B'],
        'orcid_id_src': '1',
        **empty_document
    },
    'paperBG': {
        'title': 'Paper Linking B & G',
        'authors': ['Author, Bbb', 'Author, G.'],
        'affils': ['B Institute', 'G Center for G'],
        'orcid_ids': ['ORCID B'],
        'orcid_id_src': '1',
        **empty_document
    },
    'paperCF': {
        'title': 'Paper Linking C & F',
        'authors': ['Author, C.', 'Author, F.'],
        'affils': ['C Institute', 'F Center for F'],
        'orcid_ids': [],
        'orcid_id_src': '',
        **empty_document
    },
    'paperCF2': {
        'title': 'Second Paper Linking C & F',
        'authors': ['Author, C.', 'Author, F.'],
        'affils': ['C University', 'F Center for F'],
        'orcid_ids': [],
        'orcid_id_src': '',
        **empty_document
    },
    'paperCG': {
        'title': 'Paper Linking C & G',
        'authors': ['Author, C.', 'Author, G.'],
        'affils': ['C Institute', 'G Center for G at Gtown'],
        'orcid_ids': [],
        'orcid_id_src': '',
        **empty_document
    },
    'paperDJ': {
        'title': 'Paper Linking D & J',
        'authors': ['Author, D.', 'Author, J. J.'],
        'affils': ['D Institute', 'J Institute, U. J. @ Jtown'],
        'orcid_ids': ['', 'ORCID E'],
        'orcid_id_src': '0,2',
        **empty_document
    },
    'paperEG': {
        'title': 'Paper Linking E & G',
        'authors': ['Author, Eee E.', 'Author, G.'],
        'affils': ['E Institute', 'G Center for G, Gtown'],
        'orcid_ids': ['ORCID E'],
        'orcid_id_src': '3',
        **empty_document
    },
    'paperFH': {
        'title': 'Paper Linking F & H',
        'authors': ['Author, F.', 'Author, H.'],
        'affils': ['F Institute | Fville', 'H Center for H'],
        'orcid_ids': [],
        'orcid_id_src': '',
        **empty_document
    },
    'paperFI': {
        'title': 'Paper Linking F & I',
        'authors': ['Author, F.', 'Author, I.'],
        'affils': ['F Institute, Fville, Fstate, 12345', 'I Center for I'],
        'orcid_ids': ['', 'ORCID I'],
        'orcid_id_src': '0,3',
        **empty_document
    },
    'paperIJ': {
        'title': 'Paper Linking J & I',
        'authors': ['Author, J. J.', 'Author, I.'],
        'affils': ['J Center, University of J, Other town', 'I Center for I'],
        'orcid_ids': ['', 'ORCID I'],
        'orcid_id_src': '0,2',
        **empty_document
    },
    'paperKL': {
        'title': 'Paper Linking K & L',
        'authors': ['Author, L.', 'Author, K.'],
        'affils': ['L Institute', 'K Center for K'],
        'orcid_ids': [],
        'orcid_id_src': '',
        **empty_document
    },
    'paperUncon': {
        'title': 'Paper Linking Uncon1 & Uncon2',
        'authors': ['author, unconnected b.', 'author, unconnected a.'],
        'affils': ['B Institute', 'A Center for A'],
        'orcid_ids': [],
        'orcid_id_src': '',
        **empty_document
    },
}

authors = {author for doc in documents.values() for author in doc['authors']}

for bibcode, document in documents.items():
    document['bibcode'] = bibcode


def refresh():
    pass


store_document = MagicMock()


store_documents = store_document


def delete_document(*args, **kwargs):
    raise RuntimeError("Should not delete from mock cache")


def load_document(key):
    try:
        return copy.deepcopy(documents[key])
    except KeyError:
        raise CacheMiss(key)


def load_documents(keys):
    return [load_document(key) for key in keys]


store_author = MagicMock()


delete_author = delete_document


def author_is_in_cache(key):
    try:
        load_author(key)
        return True
    except CacheMiss:
        return False


def authors_are_in_cache(keys):
    return [author_is_in_cache(key) for key in keys]


def load_author(key):
    if key[0] in '<>=':
        raise CacheMiss(key)
    
    name = ADSName.parse(key)
    docs = []
    coauthors = defaultdict(list)
    appears_as = defaultdict(list)
    for bibcode, document in documents.items():
        # Go through the document's authors until/if we find our search author
        for author in document['authors']:
            if author == name:
                docs.append(bibcode)
                idx = len(docs) - 1
                appears_as[author].append(idx)
                
                # Now add the doc's other authors as coauthors
                for coauthor in document['authors']:
                    coauthors[coauthor].append(idx)
                break
    if len(docs) or key.endswith("nodocs"):
        for coauthor, coauthor_dat in coauthors.items():
            coauthors[coauthor] = ','.join(str(i) for i in coauthor_dat)
        for alias, alias_dat in appears_as.items():
            appears_as[alias] = ','.join(str(i) for i in alias_dat)
        return {
            # defaultdict doesn't play nicely with AuthorRecord's asdict()
            'name': key,
            'documents': docs,
            'coauthors': dict(**coauthors),
            'appears_as': dict(**appears_as),
            'timestamp': TIME
        }
    else:
        raise CacheMiss(key)


def load_authors(keys):
    return [load_author(key) for key in keys]


def store_progress_data(*args, **kwargs):
    pass


delete_progress_data = delete_document


def load_progress_data(*args, **kwargs):
    raise RuntimeError("Should not load progress from mock cache")


def clear_stale_data(*args, **kwargs):
    pass


# A dummy batch manager
@contextlib.contextmanager
def batch():
    yield True
