import json
import time

import route_ranker
from log_buddy import lb
from path_finder import PathFinder


def to_json(path_finder: PathFinder):
    t_start = time.time()
    
    scored_chains, doc_data = route_ranker.process_pathfinder(path_finder)
    
    lb.on_doc_returned(len(doc_data))
    
    # scored_chains is a list. Each item is a tuple containing:
    # 1) The name-match confidence score for a unique authorship chain
    # 2) The chain itself (a list of names)
    # 3) paper_choices
    #
    # paper_choices is a list of all possible ways you can choose one paper
    # to make each link in the chain, sorted by the name-match confidence score
    # for that set of choices.
    #
    # For each chain we want to send back the best possible ordering of papers
    # along that chain. To simplify things, we'll put the best-possible
    # set of paper choices on top and then just sort the rest of the papers by
    # general "goodness", without worrying about which set of choices is
    # second-best, etc.
    
    chains = []
    paper_choices_for_chain = []
    for score, chain, paper_choices in scored_chains:
        unique_choices = []
        # paper_choices is (# possible choices) x (# links in chain)
        for choices_for_link in zip(*paper_choices):
            # Now we have a list of possible choices for one link in the chain.
            # Let's de-duplicate
            unique_choices.append([])
            already_seen = set()
            for choice in choices_for_link:
                if choice not in already_seen:
                    unique_choices[-1].append(choice)
                    already_seen.add(choice)
        chains.append(chain)
        paper_choices_for_chain.append(unique_choices)
    
    lb.on_result_prepared(time.time() - t_start)

    output = {
        'original_src': path_finder.src.name.bare_original_name,
        'original_dest': path_finder.dest.name.bare_original_name,
        'doc_data': doc_data,
        'chains': chains,
        'paper_choices_for_chain': paper_choices_for_chain,
        'stats': {
            'n_docs_queried': lb.n_docs_queried,
            'n_authors_queried': lb.n_authors_queried,
            'n_names_seen': lb.n_coauthors_seen,
            'n_network_queries': lb.n_network_queries,
            'time_waiting_network': sum(lb.time_waiting_network),
            'total_time': lb.get_search_time() + lb.get_result_prep_time()
        }
    }
    
    return json.dumps(output)
