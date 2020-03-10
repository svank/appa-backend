from path_finder import PathFinder


class RoutePrinter:
    
    def __init__(self, path_finder: PathFinder):
        self.path_finder = path_finder
    
    def print(self, col_width=20, separator=" | "):
        print(self.__str__(col_width, separator))
    
    def __str__(self, col_width=20, separator=" | "):
        fmat = "{{:{}.{}}}".format(col_width, col_width)
        output = fmat.format(str(self.path_finder.src.name)) + separator
        
        output += self._construct_rows(self.path_finder.src,
                                       1, col_width,
                                       separator, fmat)
        
        return output
    
    def _construct_rows(self, parent_node, depth, width, separator, fmat):
        first = True
        output = ""
        for node in parent_node.neighbors_toward_dest:
            if not first:
                output += '\n' + (" " * width + separator) * depth
            first = False
            output += fmat.format(str(node.name))
            if len(node.neighbors_toward_dest):
                output += separator
                output += self._construct_rows(node, depth+1, width, separator, fmat)
        return output
