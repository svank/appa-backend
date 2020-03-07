from __future__ import annotations
import sys
from dataclasses import dataclass, field
from typing import Set

from ads_name import ADSName


@dataclass()
class PathNode:
    prunable = True
    name: ADSName
    dist_from_src: int = sys.maxsize
    dist_from_dest: int = sys.maxsize
    links_toward_src: Set[PathNode] = field(default_factory=set)
    links_toward_dest: Set[PathNode] = field(default_factory=set)
    
    def dist(self, from_src: bool):
        return self.dist_from_src if from_src else self.dist_from_dest
    
    def set_dist(self, dist: int, from_src: bool):
        if from_src:
            self.dist_from_src = dist
        else:
            self.dist_from_dest = dist
    
    def links(self, from_src: bool):
        return self.links_toward_src if from_src else self.links_toward_dest
    
    def __hash__(self):
        return hash(self.name)
    
    def __str__(self):
        return f"Node({self.name})"
    
    def __repr__(self):
        src_links = ', '.join([str(n) for n in self.links_toward_src])
        dest_links = ', '.join([str(n) for n in self.links_toward_dest])
        return (f"Node(name={self.name}, "
                f"dist_from_src={self.dist_from_src}, "
                f"dist_from_dest={self.dist_from_dest}, "
                f"links_toward_src=[{src_links}], "
                f"links_toward_dest=[{dest_links}], ")
