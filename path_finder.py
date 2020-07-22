from typing import List, Set

from ads_buddy import is_bibcode, is_orcid_id, normalize_orcid_id
from ads_name import ADSName, InvalidName
from author_record import AuthorRecord
from cache_buddy import key_is_valid
from log_buddy import lb
from name_aware import NameAwareDict, NameAwareSet
from path_node import PathNode
from repository import Repository


class PathFinder:
    repository: Repository()
    nodes: NameAwareDict
    src: PathNode
    dest: PathNode
    excluded_names: NameAwareSet
    excluded_bibcodes: set
    connecting_nodes: Set[PathNode]
    n_iterations: int
    
    authors_to_expand_src = List[AuthorRecord]
    authors_to_expand_src_next = List[AuthorRecord]
    authors_to_expand_dest = List[AuthorRecord]
    authors_to_expand_dest_next = List[AuthorRecord]
    
    def __init__(self, src, dest, excluded_names=None):
        self.repository = Repository()
        if not key_is_valid(src) and not is_orcid_id(src):
            raise PathFinderError(
                "invalid_char_in_name",
                'The "source" name is invalid.')
        if not key_is_valid(dest) and not is_orcid_id(dest):
            raise PathFinderError(
                "invalid_char_in_name",
                'The "destination" name is invalid.')
        
        names_to_be_queried = []
        if is_orcid_id(src):
            src = normalize_orcid_id(src)
        else:
            try:
                src = ADSName.parse(src)
            except InvalidName:
                raise PathFinderError(
                    "invalid_char_in_name",
                    'The "source" name is invalid.')
            if src.excludes_self:
                raise PathFinderError(
                    "src_invalid_lt_gt",
                    "'<' and '>' are invalid modifiers for the source and "
                    "destination authors and can only be used in the "
                    "exclusions "
                    "list. Try '<=' or '>=' instead."
                )
            names_to_be_queried.append(src)

        if is_orcid_id(dest):
            dest = normalize_orcid_id(dest)
        else:
            try:
                dest = ADSName.parse(dest)
            except InvalidName:
                raise PathFinderError(
                    "invalid_char_in_name",
                    'The "destination" name is invalid.')
            if dest.excludes_self:
                raise PathFinderError(
                    "dest_invalid_lt_gt",
                    "'<' and '>' are invalid modifiers for the source and "
                    "destination authors and can only be used in the "
                    "exclusions "
                    "list. Try '<=' or '>=' instead."
                )
            names_to_be_queried.append(dest)
        
        if type(src) == type(dest) and src == dest:
            raise PathFinderError(
                "src_is_dest",
                'The "source" and "destination" names are equal (or at least'
                ' consistent). The distance is zero. APPA would like something'
                ' more challenging, please.'
            )
        
        self.excluded_names = NameAwareSet()
        self.excluded_bibcodes = set()
        if excluded_names is not None:
            if type(excluded_names) is str:
                excluded_names = [excluded_names]
            for name in excluded_names:
                name = name.strip()
                if name == '':
                    continue
                elif is_bibcode(name):
                    self.excluded_bibcodes.add(name)
                else:
                    self.excluded_names.add(ADSName.parse(name))
        
        self.repository.notify_of_upcoming_author_request(*names_to_be_queried)
        self.authors_to_expand_src = []
        self.authors_to_expand_src_next = []
        self.authors_to_expand_dest = []
        self.authors_to_expand_dest_next = []
        
        self.nodes = NameAwareDict()
        self.connecting_nodes = set()
        
        self.orig_src = src
        self.orig_dest = dest
    
    def find_path(self):
        lb.on_start_path_finding()
        self.n_iterations = 0
        
        if is_orcid_id(self.orig_src):
            src_rec = self.repository.get_author_record_by_orcid_id(
                self.orig_src)
            self.src = PathNode(name=src_rec.name,
                                dist_from_src=0,
                                legal_bibcodes=set(src_rec.documents))
        else:
            src_rec = self.repository.get_author_record(self.orig_src)
            self.src = PathNode(name=self.orig_src,
                                dist_from_src=0)
        
        if is_orcid_id(self.orig_dest):
            dest_rec = self.repository.get_author_record_by_orcid_id(
                self.orig_dest)
            self.dest = PathNode(name=dest_rec.name,
                                 dist_from_dest=0,
                                 legal_bibcodes=set(dest_rec.documents))
        else:
            dest_rec = self.repository.get_author_record(self.orig_dest)
            self.dest = PathNode(name=self.orig_dest,
                                 dist_from_dest=0)
        
        # If we were given a name and an ORCID ID and they turn out to refer
        # to the same person, error out.
        mixed_name_formats = (
            (type(self.orig_src) == ADSName and type(self.orig_dest) == str)
            or (type(self.orig_src) == str and type(self.orig_dest) == ADSName)
        )
        if mixed_name_formats and src_rec.name == dest_rec.name:
            raise PathFinderError(
                "src_is_dest_after_orcid",
                'After looking up the ORCID ID, the "source" and "destination"'
                ' identities are equal (or at least overlap).'
            )
        
        self.nodes[src_rec.name] = self.src
        self.nodes[dest_rec.name] = self.dest
        self.authors_to_expand_src_next.append(self.src.name)
        self.authors_to_expand_dest_next.append(self.dest.name)
        
        if (len(src_rec.documents) == 0
                or all([d in self.excluded_bibcodes
                        for d in src_rec.documents])):
            raise PathFinderError(
                "src_empty",
                "No documents found for " + self.src.name.original_name)
        if (len(dest_rec.documents) == 0
                or all([d in self.excluded_bibcodes
                        for d in dest_rec.documents])):
            raise PathFinderError(
                "dest_empty",
                "No documents found for " + self.dest.name.original_name)
        
        while True:
            lb.d("Beginning new iteration")
            lb.d(f"{len(self.authors_to_expand_src_next)} "
                 "authors on src side")
            lb.d(f"{len(self.authors_to_expand_dest_next)} "
                 "authors on dest side")
            if (len(self.authors_to_expand_src_next) == 0
                    or len(self.authors_to_expand_dest_next) == 0):
                raise PathFinderError(
                    "no_authors_to_expand",
                    "No connections possible after "
                    f"{self.n_iterations} iterations")
            # Of the two lists of authors we could expand, let's always
            # choose the shortest. This tends to get us to a solution
            # faster.
            expanding_from_src = (len(self.authors_to_expand_src_next)
                                  < len(self.authors_to_expand_dest_next))
            lb.d("Expanding from "
                 f"{'src' if expanding_from_src else 'dest'} side")
            
            authors = (self.authors_to_expand_src
                       if expanding_from_src
                       else self.authors_to_expand_dest)
            authors_next = (self.authors_to_expand_src_next
                            if expanding_from_src
                            else self.authors_to_expand_dest_next)
            authors.clear()
            authors.extend(authors_next)
            authors_next.clear()
            
            # There's no point pre-fetching for only one author, and this
            # ensures we don't re-fetch the src and dest authors if they
            # were provided by ORCID ID
            if len(authors) > 1:
                self.repository.notify_of_upcoming_author_request(*authors)
            for expand_author in authors:
                lb.d(f"Expanding author {expand_author}")
                expand_node = self.nodes[expand_author]
                expand_node_dist = expand_node.dist(expanding_from_src)
                
                # We already have src and dest records handy, and this special
                # handling is required if either was provided by ORCID ID
                if expand_node is self.src:
                    record = src_rec
                elif expand_node is self.dest:
                    record = dest_rec
                else:
                    record = self.repository.get_author_record(expand_author)

                # Here's a tricky one. If "<=Last, F" is in the exclude
                # list, and if we previously came across "Last, First" and
                # we're now expanding that node, we're ok using papers
                # written under "Last, First" but we're _not_ ok using
                # papers written under "Last, F.". So we need to ensure
                # we're allowed to use each paper by ensuring Last, First's
                # name appears on it in a way that's not excluded.
                ok_aliases = [
                    name for name in record.appears_as
                    if name not in self.excluded_names]
                if (len(self.excluded_bibcodes)
                        or len(ok_aliases) != len(record.appears_as)):
                    ok_bibcodes = {
                        bibcode
                        for alias in ok_aliases
                        for bibcode in record.appears_as[alias]
                        if bibcode not in self.excluded_bibcodes
                    }
                else:
                    ok_bibcodes = None
                
                for coauthor, bibcodes in record.coauthors.items():
                    # lb.d(f"  Checking coauthor {coauthor}")
                    if ok_bibcodes is not None:
                        bibcodes = [bibcode for bibcode in bibcodes
                                    if bibcode in ok_bibcodes]
                    if len(bibcodes) == 0:
                        continue
                    
                    coauthor = ADSName.parse(coauthor)
                    if coauthor in self.excluded_names:
                        # lb.d("   Author is excluded")
                        continue
                    
                    try:
                        node = self.nodes[coauthor]
                        # lb.d(f"   Author exists in graph")
                    except KeyError:
                        # lb.d(f"   New author added to graph")
                        lb.on_coauthor_seen()
                        node = PathNode(name=coauthor)
                        self.nodes[coauthor] = node
                        node.set_dist(expand_node_dist + 1, expanding_from_src)
                        node.neighbors(expanding_from_src).add(expand_node)
                        links = node.links(expanding_from_src)[expand_node]
                        links.update(bibcodes)
                        authors_next.append(coauthor)
                        continue
                    
                    # if (node.dist(expanding_from_src)
                    #         <= expand_node_dist):
                        # This node is closer to the src/dest than we are
                        # and must have been encountered in a
                        # previous expansion cycle. Ignore it.
                        # pass
                    if (node.dist(expanding_from_src)
                            > expand_node_dist):
                        # We provide an equal-or-better route from the
                        # src/dest than the route (if any) that this node
                        # is aware of, meaning this node is a viable next
                        # step along the chain from the src/dest through
                        # us. That it already exists suggests it has
                        # multiple chains of equal length connecting it to
                        # the src or dest.
                        # If the src or dest was given via ORCID ID, we need
                        # to make sure we have a valid connection. (E.g. if
                        # the given ID is for one J Doe and our expand_author
                        # is connected to a different J Doe, we need to
                        # exclude that.
                        if len(node.legal_bibcodes):
                            legal_bibcodes = set(bibcodes) & node.legal_bibcodes
                        else:
                            legal_bibcodes = bibcodes
                        if len(legal_bibcodes):
                            links = node.links(expanding_from_src)[expand_node]
                            links.update(legal_bibcodes)
                            node.set_dist(expand_node_dist + 1,
                                          expanding_from_src)
                            node.neighbors(expanding_from_src).add(expand_node)
                            # lb.d(f"   Added viable step")
                            if self.node_connects(node, expanding_from_src):
                                self.connecting_nodes.add(node)
                                lb.d(f"   Connecting author found!")
            lb.d("All expansions complete")
            self.n_iterations += 1
            if len(self.connecting_nodes) > 0:
                break
            elif self.n_iterations > 8:
                raise PathFinderError(
                    "too_far",
                    "The distance is >8, which is quite far. Giving up.")
            else:
                continue
        self.produce_final_graph()
        lb.set_n_connections(len(self.connecting_nodes))
        lb.set_distance(self.src.dist_from_dest)
        lb.on_stop_path_finding()
    
    def node_connects(self, node: PathNode, expanding_from_src: bool):
        if (len(node.neighbors_toward_src) > 0
                and len(node.neighbors_toward_dest) > 0):
            return True
        if expanding_from_src and node is self.dest:
            return True
        if not expanding_from_src and node is self.src:
            return True
    
    def produce_final_graph(self):
        # Step one: Make all linkages bidirectional
        nodes_to_walk = list(self.connecting_nodes)
        visited = set()
        while len(nodes_to_walk):
            node = nodes_to_walk.pop()
            if node in visited:
                continue
            visited.add(node)
            for neighbor in node.neighbors_toward_src:
                if neighbor not in visited:
                    nodes_to_walk.append(neighbor)
                neighbor.neighbors_toward_dest.add(node)
                neighbor.dist_from_dest = min(node.dist_from_dest + 1,
                                              neighbor.dist_from_dest)
                neighbor.links_toward_dest[node] = \
                    node.links_toward_src[neighbor]
            for neighbor in node.neighbors_toward_dest:
                if neighbor not in visited:
                    nodes_to_walk.append(neighbor)
                neighbor.neighbors_toward_src.add(node)
                neighbor.dist_from_src = min(node.dist_from_src + 1,
                                             neighbor.dist_from_src)
                neighbor.links_toward_src[node] = \
                    node.links_toward_dest[neighbor]
        
        # Step two: Remove any links that aren't along the most direct route
        nodes_to_walk = [self.src]
        while len(nodes_to_walk):
            node = nodes_to_walk.pop()
            if len(node.neighbors_toward_dest):
                dist_of_best_neighbor = min(
                    (neighbor.dist_from_dest
                     for neighbor in node.neighbors_toward_dest))
                # Copy the set we're iterating over, since we mutate it
                # in the loop
                for neighbor in list(node.neighbors_toward_dest):
                    if neighbor.dist_from_dest != dist_of_best_neighbor:
                        node.neighbors_toward_dest.remove(neighbor)
                        node.links_toward_dest.pop(neighbor)
                        
                        neighbor.neighbors_toward_src.remove(node)
                        neighbor.links_toward_src.pop(node)
                    else:
                        nodes_to_walk.append(neighbor)
            
            if len(node.neighbors_toward_src):
                dist_of_best_neighbor = min(
                    (neighbor.dist_from_src
                     for neighbor in node.neighbors_toward_src))
                for neighbor in list(node.neighbors_toward_src):
                    if neighbor.dist_from_src != dist_of_best_neighbor:
                        node.neighbors_toward_src.remove(neighbor)
                        node.links_toward_src.pop(neighbor)
                        
                        neighbor.neighbors_toward_dest.remove(node)
                        neighbor.links_toward_dest.pop(node)
        
        # Step three: Remove nodes that aren't on a path between src and dest
        for name, node in self.nodes.items():
            if node is self.src or node is self.dest:
                continue
            if (len(node.neighbors_toward_src) == 0
                    or len(node.neighbors_toward_dest) == 0):
                del self.nodes[name]


class PathFinderError(RuntimeError):
    def __init__(self, key, message):
        super().__init__(message)
        self.key = key
