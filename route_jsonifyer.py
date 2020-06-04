import json
import time

import route_ranker
from ads_buddy import is_orcid_id
from ads_name import ADSName
from log_buddy import lb
from path_finder import PathFinder
from repository import Repository


def to_json(path_finder: PathFinder):
    t_start = time.time()
    
    scored_chains, doc_data = route_ranker.process_pathfinder(path_finder)
    
    # scored_chains is a list. Each item is a tuple containing:
    # 1) The name-match confidence score for a unique authorship chain
    # 2) The chain itself (a list of names)
    # 3) paper_choices
    #
    # paper_choices is a list of all possible ways you can choose one paper
    # to make each link in the chain, sorted by the name-match confidence score
    # for that set of choices.
    #
    # For each chain we want to send back the best possible ordering of unique
    # papers along that chain. To simplify things, we'll put the best-possible
    # set of paper choices on top and then just sort the rest of the papers by
    # general "goodness", without worrying about which combined set of choices
    # is second-best, etc.
    
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
    
    src_name = path_finder.orig_src
    dest_name = path_finder.orig_dest
    
    used_src_names = list({chain[0] for chain in chains})
    used_dest_names = list({chain[-1] for chain in chains})
    
    src_display_name = get_name_as_in_ADS(src_name, used_src_names)
    dest_display_name = get_name_as_in_ADS(dest_name, used_dest_names)
    
    lb.on_result_prepared(time.time() - t_start)
    
    output = {
        'original_src': src_display_name,
        'original_dest': dest_display_name,
        'original_src_with_mods':
            path_finder.src.name.modifiers + src_display_name,
        'original_dest_with_mods':
            path_finder.dest.name.modifiers + dest_display_name,
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


def get_name_as_in_ADS(target_name, names_in_result: []):
    """For presentation in the UI, figures out how to capitalize a name
    
    The user may have typed in the query names in all lowercase. For the large
    banner at the top of the page, it would be nice to format the names more
    properly. Rather than just defaulting to first-letter-uppercase, we can
    use our ADS data to present the name in a form (or one of the forms) ADS
    has for the name. This means we may also pick up diacritics.
    
    Looks through all the publications belonging to the name and how the
    author's name appears in those publications. Grabs (one of) the
    most-detailed forms. If it contains more given names than the target
    names, truncates the list. Shortens given names to initials if the target
    name has an initial at that position."""
    repo = Repository(can_skip_refresh=True)
    names_in_result = [ADSName.parse(name) for name in names_in_result]
    orcid = is_orcid_id(target_name)
    if orcid:
        record = repo.get_author_record_by_orcid_id(target_name)
    else:
        target_name = ADSName.parse(target_name)
        record = repo.get_author_record(target_name)
    
    aliases = record.appears_as.keys()
    aliases = [ADSName.parse(alias) for alias in aliases]
    # Remove all aliases that aren't consistent with any of the name forms
    # used in the set of possible chains. E.g. if the user searched for
    # "Last" and all chains terminate at "Last, B.", then we shouldn't view
    # "Last, I." as a viable alias.
    aliases = [alias
               for alias in aliases
               if alias in names_in_result]
    
    # Grab the most-detailed alias. As tie-breaker, choose the form with the
    # most publications.
    alias = sorted([(a.level_of_detail,
                     len(record.appears_as[a.original_name]),
                     a.original_name)
                    for a in aliases])[-1][-1]
    alias = ADSName.parse(alias, preserve=True)
    
    if orcid:
        gns = alias.given_names
    else:
        # Trim it down to size
        gns = alias.given_names
        if len(gns) > len(target_name.given_names):
            gns = gns[:len(target_name.given_names)]
        
        # Ensure we have initials where we need them
        gns = [gn if len(tgn) > 1 else gn[0]
               for gn, tgn in zip(gns, target_name.given_names)]
    
    final_name = ADSName.parse(alias.last_name, *gns, preserve=True)
    return final_name.full_name
