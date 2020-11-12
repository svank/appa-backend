import time

import route_ranker
from log_buddy import lb
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
        t_start = time.time()
        fmt = "{{:{}.{}}}".format(col_width, col_width)
        
        chains = route_ranker.get_ordered_chains(self.path_finder)
        fmt = separator.join([fmt] * len(chains[0]))
        
        strings = [fmt.format(*chain) for chain in chains]
        output = '\n'.join(strings)
        lb.on_result_prepared(time.time() - t_start)
        return output
