from typing import Set
import time

from name_aware import NameAwareDict, NameAwareSet
from repository import Repository
from ads_name import ADSName
from LogBuddy import lb
from path_node import PathNode


class PathFinder:
    repository = Repository()
    nodes: NameAwareDict
    src: PathNode
    dest: PathNode
    excluded_names = NameAwareSet
    expanding_from_src: bool
    connecting_nodes: Set[PathNode]
    
    def __init__(self, src, dest, excluded_names=None):
        if type(src) == str:
            src = ADSName(src)
        if type(dest) == str:
            dest = ADSName(dest)
        self.excluded_names = NameAwareSet()
        if excluded_names is not None:
            for name in excluded_names:
                self.excluded_names.add(ADSName(name))
        
        self.repository.notify_of_upcoming_author_request(src, dest)
        self.expanding_from_src = True
        self.authors_to_expand_src = [src]
        self.authors_to_expand_src_next = []
        self.authors_to_expand_dest = [dest]
        self.authors_to_expand_dest_next = []
        
        self.nodes = NameAwareDict()
        self.src = PathNode(name=src, dist_from_src=0)
        self.nodes[src] = self.src
        self.dest = PathNode(name=dest, dist_from_dest=0)
        self.nodes[dest] = self.dest
        
        self.connecting_nodes = set()
    
    def find_path(self):
        start_time = time.time()
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
                for document in record.documents:
                    lb.d(f" Found document {document.title:35.35}...")
                    for coauthor in document.authors:
                        # lb.d(f"  Checking coauthor {coauthor}")
                        coauthor = ADSName(coauthor)
                        
                        if coauthor in self.excluded_names:
                            # lb.d("   Author is excluded")
                            continue
                        
                        if coauthor not in self.nodes:
                            # lb.d(f"   New author added to graph")
                            node = PathNode(name=coauthor)
                            self.nodes[coauthor] = node
                            node.set_dist(expand_node_dist + 1, self.expanding_from_src)
                            node.links(self.expanding_from_src).add(expand_node)
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
                                node.links(self.expanding_from_src).add(expand_node)
                                # lb.d(f"   Added viable step")
                            if self.node_connects(node):
                                self.connecting_nodes.add(node)
                                lb.d(f"   Connecting author found!")
            lb.d("All expansions complete")
            if len(self.connecting_nodes) > 0:
                lb.i(f"{len(self.connecting_nodes)} connections found!")
                lb.on_coauthor_considered(len(self.nodes))
                break
            else:
                lb.d("Beginning new iteration")
                if self.expanding_from_src:
                    if len(self.authors_to_expand_src_next) == 0:
                        raise RuntimeError("No authors found to expand!")
                    self.authors_to_expand_src = self.authors_to_expand_src_next
                    self.authors_to_expand_src_next = []
                else:
                    if len(self.authors_to_expand_dest_next) == 0:
                        raise RuntimeError("No authors found to expand!")
                    self.authors_to_expand_dest = self.authors_to_expand_dest_next
                    self.authors_to_expand_dest_next = []
                self.expanding_from_src = not self.expanding_from_src
                lb.d(f"Expanding from {'src' if self.expanding_from_src else 'dest'} side")
        # self.prune_graph()
        self.produce_final_graph()
        lb.i(f"Finished path finding in {time.time() - start_time:.2f} s")
    
    def node_connects(self, node):
        if (len(node.links_toward_src) > 0
                and len(node.links_toward_dest) > 0):
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
            for neighbor in node.links_toward_src:
                if neighbor.name not in visited:
                    nodes_to_walk.append(neighbor)
                neighbor.links_toward_dest.add(node)
                neighbor.dist_from_dest = min(node.dist_from_dest + 1,
                                              neighbor.dist_from_dest)
            for neighbor in node.links_toward_dest:
                if neighbor.name not in visited:
                    nodes_to_walk.append(neighbor)
                neighbor.links_toward_src.add(node)
                neighbor.dist_from_src = min(node.dist_from_src + 1,
                                             neighbor.dist_from_src)
        
        # Step two: Remove any links that aren't along the most direct route
        nodes_to_walk = [self.src]
        while len(nodes_to_walk):
            node = nodes_to_walk.pop()
            for neighbor in list(node.links_toward_dest):
                if neighbor.dist_from_src != node.dist_from_src + 1:
                    node.links_toward_dest.remove(neighbor)
                    neighbor.links_toward_src.remove(node)
                else:
                    nodes_to_walk.append(neighbor)
            
            for neighbor in list(node.links_toward_src):
                if neighbor.dist_from_dest != node.dist_from_dest + 1:
                    node.links_toward_src.remove(neighbor)
                    neighbor.links_toward_dest.remove(node)

    @property
    def authors_to_expand(self):
        return self.authors_to_expand_src if self.expanding_from_src else \
            self.authors_to_expand_dest
