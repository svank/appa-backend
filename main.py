from LogBuddy import lb
from path_finder import PathFinder
from route_printer import RoutePrinter

if __name__ == "__main__":
    lb.set_log_level(lb.DEBUG)
    source = "Van Kooten, S"
    dest = "Rast, Mark"
    exclude = []
    pf = PathFinder(source, dest, exclude)
    pf.find_path()
    
    lb.log_stats()
    print(RoutePrinter(pf))
