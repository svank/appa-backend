from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Set, DefaultDict

from ads_name import ADSName


@dataclass()
class PathNode:
    """Once instantiated, the name property should not be changed or mutated"""
    prunable = True
    name: ADSName
    dist_from_src: int = sys.maxsize
    dist_from_dest: int = sys.maxsize
    neighbors_toward_src: Set[PathNode] = field(default_factory=set)
    neighbors_toward_dest: Set[PathNode] = field(default_factory=set)
    links_toward_src: DefaultDict[PathNode, Set[str]] = field(
        default_factory=lambda: defaultdict(set))
    links_toward_dest: DefaultDict[PathNode, Set[str]] = field(
        default_factory=lambda: defaultdict(set))
    legal_bibcodes: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        self._hash = hash(self.name)
    
    def dist(self, from_src: bool):
        return self.dist_from_src if from_src else self.dist_from_dest
    
    def set_dist(self, dist: int, from_src: bool):
        if from_src:
            self.dist_from_src = dist
        else:
            self.dist_from_dest = dist
    
    def neighbors(self, from_src: bool):
        return self.neighbors_toward_src if from_src else self.neighbors_toward_dest
    
    def links(self, from_src: bool):
        return self.links_toward_src if from_src else self.links_toward_dest
    
    def __hash__(self):
        # This function is called in some very tight loops, so it's memoized
        return self._hash
    
    def __str__(self):
        return f"Node({self.name})"
    
    def __repr__(self):
        src_neighbors = ', '.join([str(n) for n in self.neighbors_toward_src])
        dest_neighbors = ', '.join([str(n) for n in self.neighbors_toward_dest])
        return (f"Node(name={self.name}, "
                f"dist_from_src={self.dist_from_src}, "
                f"dist_from_dest={self.dist_from_dest}, "
                f"neighbors_toward_src=[{src_neighbors}], "
                f"neighbors_toward_dest=[{dest_neighbors}], "
                f"legal_bibcodes=[{len(self.legal_bibcodes)} bibcodes]")
