from log_buddy import lb
from path_finder import PathFinder, PathFinderError
from route_printer import RoutePrinter

if __name__ == "__main__":
    lb.set_log_level(lb.INFO)
    source = "Van Kooten, S"
    dest = "Rast, Mark"
    exclude = []
    pf = PathFinder(source, dest, exclude)
    try:
        pf.find_path()
    except PathFinderError as e:
        lb.e(e)
    else:
        print(RoutePrinter(pf))
        lb.log_stats()
