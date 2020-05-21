from unittest import TestCase
from unittest.mock import patch, MagicMock

import ads_buddy
import cache_buddy
import path_finder
import tests.mock_backing_cache as mock_backing_cache
from log_buddy import lb


@patch.object(ads_buddy, "requests", MagicMock)
class TestPathFinder(TestCase):
    def setUp(self):
        self.real_backing_cache = cache_buddy.backing_cache
        cache_buddy.backing_cache = mock_backing_cache
    
    def tearDown(self):
        cache_buddy.backing_cache = self.real_backing_cache
        cache_buddy._loaded_authors = {}
        cache_buddy._loaded_documents = {}
        lb.reset_stats()
    
    def test_path_finding_simple(self):
        source = "Author, K"
        dest = "Author, H"
        exclude = []
        pf = path_finder.PathFinder(source, dest, exclude)
        
        pf.find_path()
        
        self.assertEqual(lb.distance, 5)
        self.assertEqual(pf.src.name, source)
        self.assertEqual(pf.dest.name, dest)
        self.assertEqual(len(pf.nodes), 6)
        
        for initial in 'il':
            self.assertIn(f"author, {initial}.", cache_buddy._loaded_authors)
            self.assertNotIn(f"author, {initial}.", pf.nodes)
        for initial in 'bdegj':
            self.assertNotIn(f"author, {initial}.",
                             cache_buddy._loaded_authors)
        
        # Checking the src node, Author, K.
        node = pf.src
        
        self.assertEqual(node.name, 'author, k.')
        self.assertEqual(node.dist_from_src, 0)
        self.assertEqual(node.dist_from_dest, 5)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         [])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, aaa'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, aaa': ['paperAK']})
        
        # Checking the next node, Author, Aaa
        node = sorted(node.neighbors_toward_dest)[0]
        
        self.assertEqual(node.name, 'author, aaa')
        self.assertEqual(node.dist_from_src, 1)
        self.assertEqual(node.dist_from_dest, 4)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, k.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, b.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, k.': ['paperAK']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, b.': ['paperAB', 'paperAB2']})
        
        # Checking the next node, Author, B.
        node = sorted(node.neighbors_toward_dest)[0]
        
        self.assertEqual(node.name, 'author, b.')
        self.assertEqual(node.dist_from_src, 2)
        self.assertEqual(node.dist_from_dest, 3)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, aaa'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, c.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, aaa': ['paperAB', 'paperAB2']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, c.': ['paperBC', 'paperBCG']})
        
        # Checking the next node, Author, C.
        node = sorted(node.neighbors_toward_dest)[0]
        
        self.assertEqual(node.name, 'author, c.')
        self.assertEqual(node.dist_from_src, 3)
        self.assertEqual(node.dist_from_dest, 2)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, b.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, f.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, b.': ['paperBC', 'paperBCG']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, f.': ['paperCF', 'paperCF2']})
        
        # Checking the next node, Author, F.
        node = sorted(node.neighbors_toward_dest)[0]
        
        self.assertEqual(node.name, 'author, f.')
        self.assertEqual(node.dist_from_src, 4)
        self.assertEqual(node.dist_from_dest, 1)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, c.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, h.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, c.': ['paperCF', 'paperCF2']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, h.': ['paperFH']})
        
        # Checking the final node, Author, H.
        node = sorted(node.neighbors_toward_dest)[0]
        self.assertIs(node, pf.dest)
        
        self.assertEqual(node.name, 'author, h.')
        self.assertEqual(node.dist_from_src, 5)
        self.assertEqual(node.dist_from_dest, 0)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, f.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         [])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, f.': ['paperFH']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {})
        
    def test_path_finding_exclusions(self):
        source = "Author, A"
        dest = "Author, F"
        exclude = ['author, B', 'paperCG']
        pf = path_finder.PathFinder(source, dest, exclude)
        
        pf.find_path()
        
        self.assertEqual(lb.distance, 4)
        self.assertEqual(pf.src.name, source)
        self.assertEqual(pf.dest.name, dest)
        self.assertEqual(len(pf.nodes), 5)
        
        for initial in "kl":
            self.assertIn(f"author, {initial}.", cache_buddy._loaded_authors)
            self.assertNotIn(f"author, {initial}.", pf.nodes)
        for initial in "bcdhij":
            self.assertNotIn(f"author, {initial}.",
                             cache_buddy._loaded_authors)
        
        # Checking the src node, Author, A.
        node = pf.src
        
        self.assertEqual(node.name, 'author, a.')
        self.assertEqual(node.dist_from_src, 0)
        self.assertEqual(node.dist_from_dest, 4)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         [])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, eee e.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, eee e.': ['paperAE']})
        
        # Checking the next node, Author, E.
        node = sorted(node.neighbors_toward_dest)[0]
        
        self.assertEqual(node.name, 'author, eee e.')
        self.assertEqual(node.dist_from_src, 1)
        self.assertEqual(node.dist_from_dest, 3)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, a.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, g.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, a.': ['paperAE']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, g.': ['paperEG']})
        
        # Checking the next node, Author, G.
        node = sorted(node.neighbors_toward_dest)[0]
        
        self.assertEqual(node.name, 'author, g.')
        self.assertEqual(node.dist_from_src, 2)
        self.assertEqual(node.dist_from_dest, 2)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, eee e.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, c.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, eee e.': ['paperEG']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, c.': ['paperBCG']})
        
        # Checking the next node, Author, C.
        node = sorted(node.neighbors_toward_dest)[0]
        
        self.assertEqual(node.name, 'author, c.')
        self.assertEqual(node.dist_from_src, 3)
        self.assertEqual(node.dist_from_dest, 1)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, g.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, f.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, g.': ['paperBCG']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, f.': ['paperCF', 'paperCF2']})
        
        # Checking the last node, Author, F.
        node = sorted(node.neighbors_toward_dest)[0]
        self.assertIs(node, pf.dest)
        
        self.assertEqual(node.name, 'author, f.')
        self.assertEqual(node.dist_from_src, 4)
        self.assertEqual(node.dist_from_dest, 0)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, c.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         [])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, c.': ['paperCF', 'paperCF2']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {})
    
    def test_path_finding_specificity_exclusions_error(self):
        source = "Author, L"
        dest = "Author, G"
        exclude = ['<author, aaa a', '>author, b']
        pf = path_finder.PathFinder(source, dest, exclude)
        
        with self.assertRaises(path_finder.PathFinderError):
            pf.find_path()
        
        source = "Author, L"
        dest = "Author, G"
        exclude = ['author, e', 'author, c', '>author, b']
        pf = path_finder.PathFinder(source, dest, exclude)
        
        with self.assertRaises(path_finder.PathFinderError):
            pf.find_path()
    
    def test_path_finding_specificity_exclusions(self):
        source = "Author, L"
        dest = "Author, G"
        exclude = ['<author, aaa']
        pf = path_finder.PathFinder(source, dest, exclude)
        pf.find_path()
        
        self.assertEqual(lb.distance, 4)
        self.assertEqual(pf.src.name, source)
        self.assertEqual(pf.dest.name, dest)
        self.assertEqual(len(pf.nodes), 6)
        
        for initial in "cdfhij":
            self.assertNotIn(f"author, {initial}.",
                             cache_buddy._loaded_authors)
        
        # Checking the src node, Author, L.
        node = pf.src
        
        self.assertEqual(node.name, 'author, l.')
        self.assertEqual(node.dist_from_src, 0)
        self.assertEqual(node.dist_from_dest, 4)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         [])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, k.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, k.': ['paperKL', 'paperKL2']})
        
        # Checking the next node, Author, K.
        node = sorted(node.neighbors_toward_dest)[0]
        
        self.assertEqual(node.name, 'author, k.')
        self.assertEqual(node.dist_from_src, 1)
        self.assertEqual(node.dist_from_dest, 3)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, l.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, aaa'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, l.': ['paperKL', 'paperKL2']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, aaa': ['paperAK']})
        
        # Checking the next node, Author, Aaa
        node = sorted(node.neighbors_toward_dest)[0]
        
        self.assertEqual(node.name, 'author, aaa')
        self.assertEqual(node.dist_from_src, 2)
        self.assertEqual(node.dist_from_dest, 2)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, k.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, bbb', 'author, eee e.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, k.': ['paperAK']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, bbb': ['paperAB2'],
                          'author, eee e.': ['paperAE']})
        
        nodeB, nodeE = sorted(node.neighbors_toward_dest,
                           key=lambda x: x.name.full_name)
        self.assertEqual(nodeB.name, 'Author, Bbb')
        self.assertEqual(nodeE.name, 'Author, Eee E.')
        self.assertEqual(nodeB.neighbors_toward_src,
                         nodeE.neighbors_toward_src)
        self.assertEqual(nodeB.neighbors_toward_dest,
                         nodeE.neighbors_toward_dest)
        
        # Checking the next node, Author, B.
        node = nodeB
        
        self.assertEqual(node.name, 'author, bbb')
        self.assertEqual(node.dist_from_src, 3)
        self.assertEqual(node.dist_from_dest, 1)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, aaa'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, g.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, aaa': ['paperAB2']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, g.': ['paperBCG', 'paperBG']})
        
        # Checking the next node, Author, E.
        node = nodeE
        
        self.assertEqual(node.name, 'author, eee e.')
        self.assertEqual(node.dist_from_src, 3)
        self.assertEqual(node.dist_from_dest, 1)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, aaa'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, g.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, aaa': ['paperAE']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, g.': ['paperEG']})
        
        # Checking the last node, Author, G.
        node = sorted(nodeB.neighbors_toward_dest)[0]
        self.assertIs(node, pf.dest)
        
        self.assertEqual(node.name, 'author, g.')
        self.assertEqual(node.dist_from_src, 4)
        self.assertEqual(node.dist_from_dest, 0)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, bbb', 'author, eee e.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         [])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, bbb': ['paperBCG', 'paperBG'],
                          'author, eee e.': ['paperEG']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {})
    
    def test_path_finding_loop(self):
        source = "Author, Eee e."
        dest = "Author, B"
        exclude = []
        pf = path_finder.PathFinder(source, dest, exclude)
        pf.find_path()
        
        self.assertEqual(lb.distance, 2)
        self.assertEqual(pf.src.name, source)
        self.assertEqual(pf.dest.name, dest)
        self.assertEqual(len(pf.nodes), 4)
        
        for initial in "cdfhijkl":
            self.assertNotIn(f"author, {initial}.",
                             cache_buddy._loaded_authors)
        
        # Checking the src node, Author, E.
        node = pf.src
        
        self.assertEqual(node.name, 'author, eee e.')
        self.assertEqual(node.dist_from_src, 0)
        self.assertEqual(node.dist_from_dest, 2)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         [])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, a.', 'author, g.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, a.': ['paperAE'],
                          'author, g.': ['paperEG']})
        
        nodeA, nodeG = sorted(node.neighbors_toward_dest,
                           key=lambda x: x.name.full_name)
        self.assertEqual(nodeA.name, 'Author, Aaa')
        self.assertEqual(nodeG.name, 'Author, G.')
        self.assertEqual(nodeA.neighbors_toward_src,
                         nodeG.neighbors_toward_src)
        self.assertEqual(nodeA.neighbors_toward_dest,
                         nodeG.neighbors_toward_dest)
        
        # Checking the next node, Author, Aaa
        node = nodeA
        
        self.assertEqual(node.dist_from_src, 1)
        self.assertEqual(node.dist_from_dest, 1)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, eee e.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, b.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, eee e.': ['paperAE']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, b.': ['paperAB', 'paperAB2']})
        
        # Checking the next node, Author, G.
        node = nodeG
        
        self.assertEqual(node.dist_from_src, 1)
        self.assertEqual(node.dist_from_dest, 1)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, eee e.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         ['author, b.'])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, eee e.': ['paperEG']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {'author, b.': ['paperBCG', 'paperBG']})
        
        # Checking the last node, Author, B.
        node = sorted(node.neighbors_toward_dest)[0]
        self.assertIs(node, pf.dest)
        
        self.assertEqual(node.name, 'author, b.')
        self.assertEqual(node.dist_from_src, 2)
        self.assertEqual(node.dist_from_dest, 0)
        self.assertIn(node.name, pf.nodes)
        
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_src),
                         ['author, a.', 'author, g.'])
        self.assertEqual(set_of_nodes_to_names(node.neighbors_toward_dest),
                         [])
        
        self.assertEqual(links_to_name_doc_map(node.links_toward_src),
                         {'author, a.': ['paperAB', 'paperAB2'],
                          'author, g.': ['paperBCG', 'paperBG']})
        self.assertEqual(links_to_name_doc_map(node.links_toward_dest),
                         {})
    
    def test_errors(self):
        with self.assertRaises(path_finder.PathFinderError) as cm:
            path_finder.PathFinder("/&", "author")
        self.assertEqual(cm.exception.key, "invalid_char_in_name")
        with self.assertRaises(path_finder.PathFinderError) as cm:
            path_finder.PathFinder("author", "/&")
        self.assertEqual(cm.exception.key, "invalid_char_in_name")
        
        with self.assertRaises(path_finder.PathFinderError) as cm:
            path_finder.PathFinder("", "author")
        self.assertEqual(cm.exception.key, "invalid_char_in_name")
        with self.assertRaises(path_finder.PathFinderError) as cm:
            path_finder.PathFinder("author", "")
        self.assertEqual(cm.exception.key, "invalid_char_in_name")
        
        with self.assertRaises(path_finder.PathFinderError) as cm:
            path_finder.PathFinder("<author, c.", "author, b.")
        self.assertEqual(cm.exception.key, "src_dest_invalid_lt_gt")
        with self.assertRaises(path_finder.PathFinderError) as cm:
            path_finder.PathFinder("author, c.", "<author, b.")
        self.assertEqual(cm.exception.key, "src_dest_invalid_lt_gt")
        
        with self.assertRaises(path_finder.PathFinderError) as cm:
            path_finder.PathFinder(">author, c.", "author, b.")
        self.assertEqual(cm.exception.key, "src_dest_invalid_lt_gt")
        with self.assertRaises(path_finder.PathFinderError) as cm:
            path_finder.PathFinder("author, c.", ">author, b.")
        self.assertEqual(cm.exception.key, "src_dest_invalid_lt_gt")
        
        pf = path_finder.PathFinder("author, nodocs", "author, a.")
        with self.assertRaises(path_finder.PathFinderError) as cm:
            pf.find_path()
        self.assertEqual(cm.exception.key, "src_empty")
        
        pf = path_finder.PathFinder("author, b.", "author, nodocs")
        with self.assertRaises(path_finder.PathFinderError) as cm:
            pf.find_path()
        self.assertEqual(cm.exception.key, "dest_empty")
        
        pf = path_finder.PathFinder("author, b.", "author, unconnected a.")
        with self.assertRaises(path_finder.PathFinderError) as cm:
            pf.find_path()
        self.assertEqual(cm.exception.key, "no_authors_to_expand")

        with self.assertRaises(path_finder.PathFinderError) as cm:
            path_finder.PathFinder("author, b.", "author, bbb")
        self.assertEqual(cm.exception.key, "src_is_dest")


def set_of_nodes_to_names(set):
    return sorted(node.name.qualified_full_name for node in set)


def links_to_name_doc_map(links):
    output = {}
    for node in links:
        output[node.name] = sorted(links[node])
    return output
