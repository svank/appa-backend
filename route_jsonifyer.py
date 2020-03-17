import json
from collections import defaultdict

import cache_buddy
from ads_name import ADSName
from log_buddy import LogBuddy
from path_finder import PathFinder
from path_node import PathNode
from repository import Repository


def to_json(path_finder: PathFinder, log_buddy: LogBuddy):
    """Prepares JSON data output.
    
    There are three main data products included:
    
    First, a tree representing paths from the source to the destination
    author.
    
    Second, a nested object containing bibcodes. The first key is any
    author. The second key is any author linked to the first author and
    one step closer to the destination. The output is a list of lists,
    where each inner list contains the bibcode of a document linking
    the two authors followed by two indices indicating where the two
    authors occur in the document's author and affiliation lists.
    
    Third is an object where the keys are bibcodes and the values are
    document records.
    
    Also included are the parsed, original src and dest names, with =<>
    qualifiers removed, and search statistics."""
    output = {}
    output['author_graph'] = _build_dict_for_node(
        path_finder.src)
    
    pairings = defaultdict(dict)
    _store_bibcodes_for_node(path_finder.src, pairings)
    output['bibcode_pairings'] = pairings
    
    # Special case for when the source and dest authors are the same
    if len(output['author_graph']['neighbors_toward_dest']) == 0:
        name = output['author_graph']['name']
        auth_record = Repository().get_author_record(path_finder.src.name.original_name)
        output['bibcode_pairings'][name][name] = [
            doc.bibcode for doc in auth_record.documents]
    
    doc_data = {}
    _insert_document_data(pairings, doc_data)
    output['doc_data'] = doc_data
    
    output['original_src'] = path_finder.src.name.bare_original_name
    output['original_dest'] = path_finder.dest.name.bare_original_name
    
    output['stats'] = {
        'n_docs_loaded': log_buddy.n_docs_loaded,
        'n_authors_loaded': log_buddy.n_authors_queried,
        'n_names_seen': log_buddy.n_coauthors_considered,
        'n_network_queries': log_buddy.n_network_queries,
        'time_waiting_network': sum(log_buddy.time_waiting_network),
        'total_time': log_buddy.get_search_time()
    }
    
    return json.dumps(output)


def _build_dict_for_node(node: PathNode):
    """Recursively builds up the tree of links between authors."""
    output = dict()
    output['name'] = node.name.bare_original_name
    neighbors = []
    output['neighbors_toward_dest'] = neighbors
    for neighbor in node.neighbors_toward_dest:
        neighbors.append(_build_dict_for_node(neighbor))
    return output


def _store_bibcodes_for_node(node: PathNode, store: {}):
    """Recursively builds the object linking author pairs to documents.
    
    For now, only stores bibcodes---author indices will be back filled
    in _insert_document_data, which loads the document data"""
    for neighbor in node.neighbors_toward_dest:
        store[node.name.bare_original_name][neighbor.name.bare_original_name] = \
            list(node.links_toward_dest[neighbor])
        _store_bibcodes_for_node(neighbor, store)


def _insert_document_data(pairings, doc_data):
    """Stores all required document data, and back fills indices"""
    for k1 in pairings.keys():
        for k2 in pairings[k1].keys():
            author1 = ADSName.parse(k1)
            author2 = ADSName.parse(k2)
            replacement = []
            
            for bibcode in pairings[k1][k2]:
                doc_record = cache_buddy.load_document_data(bibcode).asdict()
                del doc_record['bibcode']
                doc_data[bibcode] = doc_record
                
                auth_1_idx = None
                auth_2_idx = None
                for i, author in enumerate(doc_record['authors']):
                    if author1 == author and auth_1_idx is None:
                        auth_1_idx = i
                    if author2 == author and auth_2_idx is None:
                        auth_2_idx = i
                replacement.append([bibcode, auth_1_idx, auth_2_idx])
            pairings[k1][k2] = replacement
