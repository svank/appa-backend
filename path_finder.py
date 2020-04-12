from typing import List, Set

from ads_buddy import is_bibcode
from ads_name import ADSName
from author_record import AuthorRecord
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
    expanding_from_src: bool
    connecting_nodes: Set[PathNode]
    n_iterations: int
    
    authors_to_expand_src = List[AuthorRecord]
    authors_to_expand_src_next = List[AuthorRecord]
    authors_to_expand_dest = List[AuthorRecord]
    authors_to_expand_dest_next = List[AuthorRecord]
    
    def __init__(self, src, dest, excluded_names=None):
        self.repository = Repository()
        src = ADSName.parse(src)
        dest = ADSName.parse(dest)
        self.excluded_names = NameAwareSet()
        self.excluded_bibcodes = set()
        if excluded_names is not None:
            for name in excluded_names:
                name = name.strip()
                if is_bibcode(name):
                    self.excluded_bibcodes.add(name)
                else:
                    self.excluded_names.add(ADSName.parse(name))
        
        self.repository.notify_of_upcoming_author_request(src, dest)
        self.expanding_from_src = True
        self.authors_to_expand_src = [src]
        self.authors_to_expand_src_next = []
        self.authors_to_expand_dest = []
        self.authors_to_expand_dest_next = [dest]
        
        self.nodes = NameAwareDict()
        self.src = PathNode(name=src, dist_from_src=0)
        self.nodes[src] = self.src
        self.dest = PathNode(name=dest, dist_from_dest=0)
        self.nodes[dest] = self.dest
        
        self.connecting_nodes = set()
    
    def find_path(self):
        lb.on_start_path_finding()
        self.n_iterations = 0
        
        src_rec = self.repository.get_author_record(self.src.name)
        dest_rec = self.repository.get_author_record(self.dest.name)
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
        
        self.expanding_from_src = True
        
        while True:
            authors = (self.authors_to_expand_src
                       if self.expanding_from_src
                       else self.authors_to_expand_dest)
            authors_next = (self.authors_to_expand_src_next
                            if self.expanding_from_src
                            else self.authors_to_expand_dest_next)
            for expand_author in authors:
                lb.d(f"Expanding author {expand_author}")
                expand_node = self.nodes[expand_author]
                expand_node_dist = expand_node.dist(self.expanding_from_src)
                record = self.repository.get_author_record(expand_author)

                # Here's a tricky one. If "<Last, F" is in the exclude
                # list, and if we previously came across "Last, First" and
                # we're now expanding that node, we're ok using papers
                # written under "Last, First" but we're _not_ ok using
                # papers written under "Last, F.". So we need to ensure
                # we're allowed to use each paper by ensuring Last, First's
                # name appears on it in a way that's not excluded.
                ok_aliases = [
                    name for name in record.appears_as
                    if name not in self.excluded_names]
                ok_bibcodes = [
                    bibcode
                    for alias in ok_aliases
                    for bibcode in record.appears_as[alias]
                    if bibcode not in self.excluded_bibcodes
                ]
                
                for coauthor in record.coauthors:
                    # lb.d(f"  Checking coauthor {coauthor}")
                    bibcodes = record.coauthors[coauthor]
                    bibcodes = [bibcode for bibcode in bibcodes
                                if bibcode in ok_bibcodes]
                    if len(bibcodes) == 0:
                        continue
                    
                    coauthor = ADSName.parse(coauthor)
                    if coauthor in self.excluded_names:
                        # lb.d("   Author is excluded")
                        continue
                    
                    if coauthor not in self.nodes:
                        # lb.d(f"   New author added to graph")
                        lb.on_coauthor_considered()
                        node = PathNode(name=coauthor)
                        self.nodes[coauthor] = node
                        node.set_dist(expand_node_dist + 1, self.expanding_from_src)
                        node.neighbors(self.expanding_from_src).add(expand_node)
                        authors_next.append(coauthor)
                        self.repository.notify_of_upcoming_author_request(coauthor)
                    
                    else:
                        # lb.d(f"   Author exists in graph")
                        node = self.nodes[coauthor]
                        if (node.dist(self.expanding_from_src)
                                <= expand_node_dist):
                            # This node must have been encountered in a
                            # previous expansion cycle. Ignore it.
                            pass
                        elif (node.dist(self.expanding_from_src)
                                > expand_node_dist + 1):
                            # This node is a viable next step along this chain.
                            # That it already exists suggests it has multiple
                            # chains of equal length connecting it to the
                            # src or dest
                            node.set_dist(expand_node_dist + 1, self.expanding_from_src)
                            node.neighbors(self.expanding_from_src).add(expand_node)
                            # lb.d(f"   Added viable step")
                        if self.node_connects(node):
                            self.connecting_nodes.add(node)
                            lb.d(f"   Connecting author found!")
                    links = node.links(self.expanding_from_src)[expand_node]
                    links.update(bibcodes)
            lb.d("All expansions complete")
            self.n_iterations += 1
            if len(self.connecting_nodes) > 0:
                lb.i(f"{len(self.connecting_nodes)} connections found!")
                break
            else:
                lb.d("Beginning new iteration")
                lb.d(f"{len(self.authors_to_expand_src_next)} authors on src side")
                lb.d(f"{len(self.authors_to_expand_dest_next)} authors on dest side")
                if (len(self.authors_to_expand_src_next) == 0
                        or len(self.authors_to_expand_dest_next) == 0):
                    raise PathFinderError(
                        "no_authors_to_expand",
                        f"No connections possible after {self.n_iterations} iterations")
                # Of the two lists of authors we could expand, let's always
                # choose the shortest. This tends to get us to a solution
                # faster.
                if (len(self.authors_to_expand_src_next)
                        < len(self.authors_to_expand_dest_next)):
                    self.authors_to_expand_src = self.authors_to_expand_src_next
                    self.authors_to_expand_src_next = []
                    self.expanding_from_src = True
                else:
                    self.authors_to_expand_dest = self.authors_to_expand_dest_next
                    self.authors_to_expand_dest_next = []
                    self.expanding_from_src = False
                lb.d(f"Expanding from {'src' if self.expanding_from_src else 'dest'} side")
        self.produce_final_graph()
        lb.on_stop_path_finding()
    
    def node_connects(self, node: PathNode):
        if (len(node.neighbors_toward_src) > 0
                and len(node.neighbors_toward_dest) > 0):
            return True
        if self.expanding_from_src and node is self.dest:
            return True
        if not self.expanding_from_src and node is self.src:
            return True
    
    def produce_final_graph(self):
        # Step one: Make all linkages bidirectional
        nodes_to_walk = list(self.connecting_nodes)
        visited = set()
        while len(nodes_to_walk):
            node = nodes_to_walk.pop()
            if node.name in visited:
                continue
            visited.add(node.name)
            for neighbor in node.neighbors_toward_src:
                if neighbor.name not in visited:
                    nodes_to_walk.append(neighbor)
                neighbor.neighbors_toward_dest.add(node)
                neighbor.dist_from_dest = min(node.dist_from_dest + 1,
                                              neighbor.dist_from_dest)
                neighbor.links_toward_dest[node] = \
                    node.links_toward_src[neighbor]
            for neighbor in node.neighbors_toward_dest:
                if neighbor.name not in visited:
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
            for neighbor in list(node.neighbors_toward_dest):
                if neighbor.dist_from_src != node.dist_from_src + 1:
                    node.neighbors_toward_dest.remove(neighbor)
                    node.links_toward_dest.pop(neighbor)
                    
                    neighbor.neighbors_toward_src.remove(node)
                    neighbor.links_toward_src.pop(node)
                else:
                    nodes_to_walk.append(neighbor)
            
            for neighbor in list(node.neighbors_toward_src):
                if neighbor.dist_from_dest != node.dist_from_dest + 1:
                    node.neighbors_toward_src.remove(neighbor)
                    node.links_toward_src.pop(neighbor)
                    
                    neighbor.neighbors_toward_dest.remove(node)
                    neighbor.links_toward_dest.pop(node)

    @property
    def authors_to_expand(self):
        return self.authors_to_expand_src if self.expanding_from_src else \
            self.authors_to_expand_dest


class PathFinderError(RuntimeError):
    def __init__(self, key, message):
        super().__init__(message)
        self.key = key
