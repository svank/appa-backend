import route_ranker
from path_finder import PathFinder


class RoutePrinter:
    """
    Prints a PathFinder's discovered routes in an ASCII table
    
    Rows are ordered by name-match confidence
    """
    def __init__(self, path_finder: PathFinder):
        self.path_finder = path_finder
    
    def print(self, col_width=20, separator=" | "):
        print(self.__str__(col_width, separator))
    
    def __str__(self, col_width=20, separator=" | "):
        fmt = "{{:{}.{}}}".format(col_width, col_width)
        
        chains = route_ranker.get_ordered_chains(self.path_finder)
        fmt = separator.join([fmt] * len(chains[0]))
        
        prev_chain = chains[0]
        out_chains = [prev_chain]
        for chain in chains[1:]:
            res = [e2 if e2 != e1 else ''
                   for e1, e2 in zip(prev_chain, chain)]
            out_chains.append(res)
        
        strings = [fmt.format(*chain) for chain in out_chains]
        return '\n'.join(strings)
