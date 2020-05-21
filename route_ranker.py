import functools
import itertools
import string
from collections import defaultdict

from ads_name import ADSName
from log_buddy import lb
from path_finder import PathFinder
from path_node import PathNode
from repository import Repository


def process_pathfinder(path_finder: PathFinder):
    repo = Repository(can_skip_refresh=True)
    
    pairings, all_bibcodes = _store_bibcodes_for_node(path_finder.src, repo)
    
    doc_data = {}
    lb.set_n_docs_relevant(len(all_bibcodes))
    repo.notify_of_upcoming_document_request(*all_bibcodes)
    _insert_document_data(pairings, doc_data, repo, path_finder.excluded_names)
    lb.update_progress_cache(force=True)
    
    chains = _build_author_chains(path_finder.src)
    scored_chains = _rank_author_chains(chains, repo, pairings)
    
    if scored_chains is None:
        # TODO: do better
        raise AllPathsInvalid(f"src: {path_finder.src.name}"
                              f" dest: {path_finder.dest.name}"
                              f" excln: {path_finder.excluded_names}"
                              f" exclb: {path_finder.excluded_bibcodes}")
    
    return scored_chains, doc_data


def get_ordered_chains(path_finder: PathFinder, scores=False):
    scored_chains, doc_data = process_pathfinder(path_finder)
    if scores:
        return ([chain for _, chain, _ in scored_chains],
                [score for score, _, _ in scored_chains])
    return [chain for _, chain, _ in scored_chains]


def _store_bibcodes_for_node(node: PathNode, repo: Repository,
                             pairings=None, all_bibcodes=None):
    """Recursively builds the object linking author pairs to documents.

    For now, only stores bibcodes---author indices will be back filled
    in _insert_document_data, which loads the document data.
    
    This all enables quicker lookups later while ranking.
    """
    if pairings is None:
        pairings = defaultdict(dict)
    if all_bibcodes is None:
        all_bibcodes = set()
    
    for neighbor in node.neighbors_toward_dest:
        bibcodes = sorted(node.links_toward_dest[neighbor])
        all_bibcodes.update(bibcodes)
        
        pairings[node.name.bare_original_name][
            neighbor.name.bare_original_name] = \
            bibcodes
        _store_bibcodes_for_node(neighbor, repo, pairings, all_bibcodes)
    
    return pairings, all_bibcodes


def _insert_document_data(pairings, doc_data, repo, excluded_names):
    """Stores all required document data, and back fills indices"""
    for k1 in pairings.keys():
        author1 = ADSName.parse(k1)
        for k2 in pairings[k1].keys():
            author2 = ADSName.parse(k2)
            replacement = []
            
            for bibcode in pairings[k1][k2]:
                if bibcode in doc_data:
                    doc_record = doc_data[bibcode]
                else:
                    doc_record = repo.get_document(bibcode).asdict()
                    lb.on_doc_loaded()
                    del doc_record['bibcode']
                    del doc_record['timestamp']
                    doc_data[bibcode] = doc_record
                
                auth_1_idx = None
                auth_2_idx = None
                for i, author in enumerate(doc_record['authors']):
                    author = ADSName.parse(author)
                    if author in excluded_names:
                        continue
                    if auth_1_idx is None and author1 == author:
                        auth_1_idx = i
                    if auth_2_idx is None and author2 == author:
                        auth_2_idx = i
                    if auth_1_idx is not None and auth_2_idx is not None:
                        break
                replacement.append((bibcode, auth_1_idx, auth_2_idx))
            pairings[k1][k2] = replacement


def _build_author_chains(src: PathNode):
    starter = []
    list_of_chains = []
    _build_author_chains_next_level(starter, src, list_of_chains)
    return list_of_chains


def _build_author_chains_next_level(starter: [], src: PathNode,
                                    list_of_chains: []):
    starter = starter + [src.name.bare_original_name]
    if len(src.neighbors_toward_dest) == 0:
        list_of_chains.append(starter)
    else:
        for neighbor in src.neighbors_toward_dest:
            _build_author_chains_next_level(starter, neighbor, list_of_chains)


def _rank_author_chains(chains: [], repo, pairings):
    items = []
    for chain in chains:
        scores, paper_choices = _score_author_chain(chain, repo, pairings)
        if scores is None:
            continue
        # We'd like papers to be sorted by score descending, and then
        # alphabetically by title as the tie-breaker. So here we look up those
        # titles. `paper_choices` looks like:
        # ( [ (bibcode, 0, 1), (bibcode, 0, 1), (bibcode, 0, 1) ],
        #   [ (bibcode, 0, 1), (bibcode, 0, 1), (bibcode, 0, 1) ] )
        # Each column represents a chain link (A -> B)'
        # Each row gives you one paper for each chain link
        # We want to replace each inner tuple with a paper title
        titles = [[repo.get_document(bibcode).title
                   for bibcode, _, _ in paper_choice]
                  for paper_choice in paper_choices]
        
        # This should happen here, since later we use author names
        # as a secondary key for sorting.
        new_chain = normalize_author_names(paper_choices, repo)
        
        # Negate scores so we have a sort that's descending by actual score
        # and then ascending by title
        intermed = zip([-s for s in scores], titles, paper_choices)
        intermed = sorted(intermed)
        scores, _, paper_choices = zip(*intermed)
        items.append((scores[0], new_chain, paper_choices))
    
    if len(items) == 0:
        return None
    if len(items) != len(chains):
        lb.w(f"{len(chains) - len(items)} / {len(chains)} chains invalidated")
    
    # The scores are still negative, so now we get a sort that's descending by
    # actual score and then ascending by author names.
    intermed = sorted(items)
    return [(-score, chain, pc) for score, chain, pc in intermed]


def _score_author_chain(chain, repo, pairings):
    # `chain` is a list of authors: A -> B -> C -> D
    connection_lists = []
    for a1, a2 in zip(chain[:-1], chain[1:]):
        # For each link in the chain (each ->), `connection` is a list of
        # (bibcode, idx1, idx2), where each tuple contains the bibcode of a
        # document the two authors published together and the indices at which
        # each author appears in the document's author list
        connection = pairings[a1][a2]
        connection_lists.append(connection)
    
    # Now that we've identified the list of papers that can make each
    # connection in the chain, we need to compute a name-match-confidence
    # score for each possible realization of the chain:
    # Authors: A -> B -> C -> D
    # Papers:    p1   p3   p5
    #            p2   p4   p6
    # We need to consider the chains formed by (p1, p3, p5), (p2, p3, p5),
    # (p1, p3, p6), ...
    items = []
    for papers_choice in itertools.product(*connection_lists):
        # Now that we've chosen papers (e.g. (p1, p3, p5)), we need to score
        # how likely it is that the same B published p1 and p3, and that the
        # same C published p3 and p5.
        score = 0
        for con1, con2 in zip(papers_choice[:-1], papers_choice[1:]):
            addition = _score_author_chain_link(con1, con2, repo)
            if addition is None:
                score = None
                break
            score += addition
        
        if score is not None:
            items.append((score, papers_choice))
    
    if len(items) == 0:
        return None, None
    items.sort(reverse=True)
    scores, paper_choices = zip(*items)
    return scores, paper_choices


@functools.lru_cache(5000)
def _score_author_chain_link(con1, con2, repo):
    """Scores the reliability of name matching between two papers

    Accepts two "connections", tupes containing a bibcode followed by two
    indices locating an author in the author list of the associated bibccode.
    The author in question will be indicated by the latter index in the first
    connection and the earlier index in the second connection.

    When ORCID ids are available, they solely determine the score, which will
    fall between 0.7 and 1 depending on the source of the ORCID ids. Otherwise
    the score will be derived from the faction of overlap between the author's
    affiliations in the two papers, and the level of detail of the
    author's name as printed in the two papers. These scores will fall in the
    range (0, 0.4), with contributions of up to 0.3 from affiliation matching
    and up to 0.1 from name detail"""
    doc1 = repo.get_document(con1[0])
    doc2 = repo.get_document(con2[0])
    idx1 = con1[2]
    idx2 = con2[1]
    orcid_id_1 = doc1.orcid_ids[idx1]
    orcid_id_2 = doc2.orcid_ids[idx2]
    if orcid_id_1 != '' and orcid_id_2 != '':
        if orcid_id_1 == orcid_id_2:
            orcid_src_1 = doc1.orcid_id_src[idx1]
            orcid_src_2 = doc2.orcid_id_src[idx2]
            # Looking at the source of ADS's ORCID id data, each score element
            # is 1 for orcid_pub, .92 for orcid_user, and .84 for orcid_other.
            # The values for the two ORCID ids are multiplied together
            score1 = 1 - .08 * (orcid_src_1 - 1)
            score2 = 1 - .08 * (orcid_src_2 - 1)
            return score1 * score2
        else:
            # The ORCID ids _don't_ match!
            return None
    
    # Attempt some affiliation fuzzy-matching
    # _process_affil will do some processing and return a list of the
    # comma-delimited chunks in the affiliation.
    affil1 = _process_affil(doc1.affils[idx1])
    affil2 = _process_affil(doc2.affils[idx2])
    
    # Compute the fraction of the chunks of each affil that are present
    # in the other
    try:
        one_in_two = sum(chunk in affil2 for chunk in affil1) / len(affil1)
        two_in_one = sum(chunk in affil1 for chunk in affil2) / len(affil2)
    except ZeroDivisionError:
        one_in_two = 0
        two_in_one = 0
    # Average these two fractions
    affil_frac_in_common = (one_in_two + two_in_one) / 2
    
    # Put the score in the range (0, 0.3)
    affil_score = affil_frac_in_common * .3
    
    name1 = ADSName.parse(doc1.authors[idx1])
    name2 = ADSName.parse(doc2.authors[idx2])
    if name1 != name2:
        # This can occur, e.g. if J. Doe was encountered first, creating a
        # J. Doe node in PathFinder, then Jane and John Doe were encountered
        # and added to that node, and now a proposed chain runs from Jane
        # to John.
        return None
    detail1 = name1.level_of_detail
    detail2 = name2.level_of_detail
    # level_of_detail examples:
    # Last, First Middle: 20
    # Last, First, M: 13
    # Last, First: 10
    # Last, F: 3
    # Last: 0
    #
    # We'll score based on the less-detailed name, take 20 as the ideal value,
    # and put the name score in the range (0, 0.1)
    detail_score = min(detail1, detail2) / 20 * .1
    
    return detail_score + affil_score


# Includes hyphen '-'
chars_to_remove = {'.', ':', '-'}
chars_to_remove.update(string.digits)
# Includes en dash '–', em dash '—', & horizontal bar '―'
chars_to_replace = {'|', ';', '@', '/', '–', '—', '―'}
words_to_remove = {'the', 'of', 'a', 'an', 'and', '&'}
words_to_replace = {
    'inst': 'institute',
    'u': 'university',
    'uni': 'university',
    'univ': 'university'
}


@functools.lru_cache(5000)
def _process_affil(affil):
    affil = affil.lower()
    affil = affil.replace(" at ", ',')
    
    affil = ''.join(',' if c in chars_to_replace else c
                    for c in affil
                    if (c not in chars_to_remove
                        and c.isprintable()))
    
    chunks = affil.split(',')
    chunks = (chunk.strip() for chunk in chunks)
    
    processed_chunks = []
    for chunk in chunks:
        words = []
        for word in chunk.split():
            if word in words_to_remove:
                continue
            if word in words_to_replace:
                word = words_to_replace[word]
            if len(word):
                words.append(word)
        if len(words):
            processed_chunks.append(" ".join(words))
    return processed_chunks


def normalize_author_names(paper_choices, repo):
    """Re-builds a chain with names representative of the linking papers.
    
    Builds a new chain where each name is as seen in the top paper choice
    for that chain link. Names that aren't the first or last in the chain
    appear on two chosen papers, and of those two versions of the name, the
    least specific is chosen."""
    new_chain = []
    for i, pc in enumerate(zip(*paper_choices)):
        bibcode, a1idx, a2idx = pc[0]
        doc = repo.get_document(bibcode)
        a1name = doc.authors[a1idx]
        a2name = doc.authors[a2idx]
        if (i != 0
                and ADSName.parse(a1name).level_of_detail
                < ADSName.parse(new_chain[-1]).level_of_detail):
            new_chain[-1] = a1name
        elif i == 0:
            new_chain.append(a1name)
        new_chain.append(a2name)
    return new_chain


class AllPathsInvalid(RuntimeError):
    pass