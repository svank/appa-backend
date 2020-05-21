from unittest import TestCase
from unittest.mock import patch, MagicMock

import ads_buddy
import cache_buddy
import path_finder
import route_ranker
from repository import Repository
from tests import mock_backing_cache


@patch.object(ads_buddy, "requests", MagicMock)
class TestRouteRanker(TestCase):
    def setUp(self):
        self.real_backing_cache = cache_buddy.backing_cache
        cache_buddy.backing_cache = mock_backing_cache
        self.repository = Repository()
    
    def tearDown(self):
        cache_buddy.backing_cache = self.real_backing_cache
    
    def test_score_chain_link(self):
        #
        # ORCID ID-based scores
        #
        
        # IDs match, varying values of orcid_id_src
        con1 = ('paperBG', None, 0)
        con2 = ('paperBC', 1, None)
        self.assertEqual(1, route_ranker._score_author_chain_link(
            con1, con2, self.repository))
        
        con1 = ('paperBG', None, 0)
        con2 = ('paperAB2', 0, None)
        self.assertEqual(0.84, route_ranker._score_author_chain_link(
            con1, con2, self.repository))
        
        con1 = ('paperFI', None, 1)
        con2 = ('paperIJ', 1, None)
        self.assertEqual(0.7728, route_ranker._score_author_chain_link(
            con1, con2, self.repository))
        
        # IDs _don't_ match
        con1 = ('paperAB2', None, 0)
        con2 = ('paperBCG', 0, None)
        self.assertIsNone(route_ranker._score_author_chain_link(
            con1, con2, self.repository))
        
        #
        # Affiliation-matching and name-specificity scores
        #
        # Data is tested before use to ensure they haven't changed
        # in the mock data set and we're still testing the same thing.
        # Expected scores are written as (affil score) + (name score)
        
        # Exact match, two spelled-out names
        self.assertEqual(cache_buddy.load_document('paperAB2').affils[1],
                         'A Institute')
        self.assertEqual(cache_buddy.load_document('paperAE').affils[0],
                         'A Institute')
        self.assertEqual(cache_buddy.load_document('paperAB2').authors[1],
                         'Author, Aaa')
        self.assertEqual(cache_buddy.load_document('paperAE').authors[0],
                         'Author, Aaa')
        con1 = ('paperAB2', None, 1)
        con2 = ('paperAE', 0, None)
        self.assertEqual(0.3 + 0.05, route_ranker._score_author_chain_link(
            con1, con2, self.repository))
        
        # Exact affil match after word and letter substitution removal
        self.assertEqual(cache_buddy.load_document('paperBCG').affils[1],
                         'Univ. C')
        self.assertEqual(cache_buddy.load_document('paperBC').affils[0],
                         'University of C')
        self.assertEqual(cache_buddy.load_document('paperBCG').authors[1],
                         'Author, C. C.')
        self.assertEqual(cache_buddy.load_document('paperBC').authors[0],
                         'Author, C.')
        con1 = ('paperBCG', None, 1)
        con2 = ('paperBC', 0, None)
        self.assertEqual(0.3 + 0.015, route_ranker._score_author_chain_link(
            con1, con2, self.repository))
        
        # Multi-part, exact affil match after word->split substitution
        self.assertEqual(cache_buddy.load_document('paperCG').affils[1],
                         'G Center for G at Gtown')
        self.assertEqual(cache_buddy.load_document('paperEG').affils[1],
                         'G Center for G, Gtown')
        self.assertEqual(cache_buddy.load_document('paperCG').authors[1],
                         'Author, G.')
        self.assertEqual(cache_buddy.load_document('paperEG').authors[1],
                         'Author, G.')
        con1 = ('paperCG', None, 1)
        con2 = ('paperEG', 1, None)
        self.assertEqual(0.3 + 0.015, route_ranker._score_author_chain_link(
            con1, con2, self.repository))
        
        # Multi-part, partial affil match after word->split substitution;
        # zip code removed
        self.assertEqual(cache_buddy.load_document('paperFH').affils[0],
                         'F Institute | Fville')
        self.assertEqual(cache_buddy.load_document('paperFI').affils[0],
                         'F Institute, Fville, Fstate, 12345')
        self.assertEqual(cache_buddy.load_document('paperFH').authors[0],
                         'Author, F.')
        self.assertEqual(cache_buddy.load_document('paperFI').authors[0],
                         'Author, F.')
        con1 = ('paperFH', None, 0)
        con2 = ('paperFI', 0, None)
        self.assertEqual(0.3 * (1 + 2/3)/2 + 0.015, 
                         route_ranker._score_author_chain_link(
                             con1, con2, self.repository))
        
        # Multi-part, low affil match after word->split substitution
        self.assertEqual(cache_buddy.load_document('paperDJ').affils[1],
                         'J Institute, U. J. @ Jtown')
        self.assertEqual(cache_buddy.load_document('paperIJ').affils[0],
                         'J Center, University of J, Other town')
        self.assertEqual(cache_buddy.load_document('paperDJ').authors[1],
                         'Author, J. J.')
        self.assertEqual(cache_buddy.load_document('paperIJ').authors[0],
                         'Author, J. J.')
        con1 = ('paperDJ', None, 1)
        con2 = ('paperIJ', 0, None)
        self.assertEqual(0.3 * 1/3 + 0.03,
                         route_ranker._score_author_chain_link(
                             con1, con2, self.repository))
    
    def test_build_author_chains(self):
        for src, dest, expected_chain in [
            ("Author, A.", "Author, G.",
             [['Author, A.', 'Author, Bbb', 'Author, G.'],
              ['Author, A.', 'Author, Eee E.', 'Author, G.']]),
            
            ("Author, D.", "Author, I.",
             [['Author, D.', 'Author, J. J.', 'Author, I.']])]:
            
            with self.subTest(src=src, dest=dest):
                pf = path_finder.PathFinder(src, dest, [])
                pf.find_path()
                
                chains = route_ranker._build_author_chains(pf.src)
                self.assertEqual(sorted(chains), expected_chain)
    
    def test_score_author_chain(self):
        src = "Author, A."
        dest = "Author, G."
        pf = path_finder.PathFinder(src, dest)
        pf.find_path()
        
        pairings = {
            "Author, A.": {
                "Author, Bbb": [('paperAB', 0, 1), ('paperAB2', 1, 0)],
                "Author, Eee E.": [('paperAE', 0, 1)]
            },
            "Author, Bbb": {
                "Author, G.": [('paperBCG', 0, 2), ('paperBG', 0, 1)]
            },
            "Author, Eee E.": {
                "Author, G.": [('paperEG', 0, 1)]
            }
        }
        
        chain = ['Author, A.', 'Author, Bbb', 'Author, G.']
        scores, _ = route_ranker._score_author_chain(
            chain, self.repository, pairings)
        self.assertEqual(scores, (.84, .05, .05))
        
        chain = ['Author, A.', 'Author, Eee E.', 'Author, G.']
        scores, _ = route_ranker._score_author_chain(
            chain, self.repository, pairings)
        self.assertEqual(scores, (.065,))

        src = "Author, A."
        dest = "Author, F."
        pf = path_finder.PathFinder(src, dest)
        pf.find_path()
        
        pairings = {
            "Author, A.": {
                "Author, Bbb": [('paperAB', 0, 1), ('paperAB2', 1, 0)]
            },
            "Author, Bbb": {
                "Author, C.": [('paperBCG', 0, 1), ('paperBC', 1, 0)]
            },
            "Author, C.": {
                "Author, F.": [('paperCF', 0, 1), ('paperCF2', 0, 1)]
            }
        }
        
        chain = ['Author, A.', 'Author, Bbb', 'Author, C.', 'Author, F.']
        test_scores, _ = route_ranker._score_author_chain(
            chain, self.repository, pairings)
        self.assertEqual(test_scores,
                         (0.855, 0.855, 0.065, 0.065, 0.03, 0.03))
    
    def test_get_ordered_chains(self):
        # First rep: Author, B. has an ORCID id match and so that route should
        # come out on top

        # Second rep: With paperAB2 excluded, Author, B. no longer has an ORCID
        # ID match. There are no affiliation overlaps.
        # Now Author, Eee E.'s more full name should put that chain
        # on top.

        # Third rep: ensure no errors when there's only one chain

        for src, dest, exclude, expected_chain in [
            ("Author, A", "Author, G", [],
             [['Author, Aaa', 'Author, B.', 'Author, G.'],
              ['Author, Aaa', 'Author, Eee E.', 'Author, G.']]),
            
            ("Author, A", "Author, G",  ['paperAB2'],
             [['Author, Aaa', 'Author, Eee E.', 'Author, G.'],
              ['Author, A.', 'Author, Bbb', 'Author, G.']]),
            
            ("Author, D.", "Author, I.", [],
             [['Author, D.', 'Author, J. J.', 'Author, I.']]),
            
            ("Author, D.", "Author, J. J.", [],
             [['Author, D.', 'Author, J. J.']])]:
            with self.subTest(src=src, dest=dest, excl=exclude):
                pf = path_finder.PathFinder(src, dest, exclude)
                pf.find_path()
                
                chains = route_ranker.get_ordered_chains(pf)
                self.assertEqual(chains, expected_chain)
    
    def test_process_pathfinder(self):
        def run_pf(src, dest, exclude):
            pf = path_finder.PathFinder(src, dest, exclude)
            pf.find_path()
            
            return route_ranker.process_pathfinder(pf)
        
        # Author, B. has an ORCID id match and so that route should
        # come out on top
        source = "Author, A"
        dest = "Author, G"
        exclude = []
        scored_chains, doc_data = run_pf(source, dest, exclude)
        
        self.assertEqual([chain for _, chain, _ in scored_chains],
                         [['Author, Aaa', 'Author, B.', 'Author, G.'],
                          ['Author, Aaa', 'Author, Eee E.', 'Author, G.']])
        
        self.assertEqual([score for score, _, _ in scored_chains],
                         [.84, .1 * 13/20])
        
        paper_choices = [pc for _, _, pc in scored_chains]
        self.assertEqual(paper_choices[0],
                         ((('paperAB2', 1, 0), ('paperBG', 0, 1)),
                          (('paperAB', 0, 1), ('paperBG', 0, 1)),
                          (('paperAB', 0, 1), ('paperBCG', 0, 2))))
        self.assertEqual(paper_choices[1],
                         ((('paperAE', 0, 1), ('paperEG', 0, 1)),))
        
        for doc in ['AB', 'AB2', 'BCG', 'BG', 'AE', 'EG']:
            self.assertIn('paper' + doc, doc_data)
        self.assertEqual(6, len(doc_data))

        # With paperAB2 excluded, Author, B. no longer has an ORCID ID match.
        # There are no affiliation overlaps.
        # Now Author, Eee E.'s more full name should put that chain
        # on top.
        source = "Author, A"
        dest = "Author, G"
        exclude = ['paperAB2']
        scored_chains, doc_data = run_pf(source, dest, exclude)
        
        self.assertEqual([chain for _, chain, _ in scored_chains],
                         [['Author, Aaa', 'Author, Eee E.', 'Author, G.'],
                          ['Author, A.', 'Author, Bbb', 'Author, G.']])
        
        self.assertEqual([score for score, _, _ in scored_chains],
                         [.1 * 13/20, .1 * 10/20])
        
        paper_choices = [pc for _, _, pc in scored_chains]
        self.assertEqual(paper_choices[0],
                         ((('paperAE', 0, 1), ('paperEG', 0, 1)),))
        self.assertEqual(paper_choices[1],
                         ((('paperAB', 0, 1), ('paperBG', 0, 1)),
                          (('paperAB', 0, 1), ('paperBCG', 0, 2))))
        
        for doc in ['AB', 'BCG', 'BG', 'AE', 'EG']:
            self.assertIn('paper' + doc, doc_data)
        self.assertEqual(5, len(doc_data))

        # Finally, ensure no errors when there's only one chain
        source = "Author, D."
        dest = "Author, I."
        exclude = []
        scored_chains, doc_data = run_pf(source, dest, exclude)
        
        self.assertEqual([chain for _, chain, _ in scored_chains],
                         [['Author, D.', 'Author, J. J.', 'Author, I.']])
        
        self.assertEqual([score for score, _, _ in scored_chains],
                         [.3 * 1/3 + .1 * 6/20])
        
        paper_choices = [pc for _, _, pc in scored_chains]
        self.assertEqual(paper_choices[0],
                         ((('paperDJ', 0, 1), ('paperIJ', 0, 1)),))
        
        for doc in ['DJ', 'IJ']:
            self.assertIn('paper' + doc, doc_data)
        self.assertEqual(2, len(doc_data))
    
    def test_handling_exclusions(self):
        """paperKL2 has two authors matching "Author, L.", namely
        "Author, L." and "Author, L. L.". PathFinder should handle this
        without any trouble, but we need to ensure the chain shows
        "Author, L. L.", and not the excluded "Author, L.".
        
        This is coming from a real-life situation."""
        src = "Author, L"
        dest = "Author, A"
        exclude = ["=Author, L."]
        pf = path_finder.PathFinder(src, dest, exclude)
        pf.find_path()

        scored_chains, doc_data = route_ranker.process_pathfinder(pf)
        self.assertEqual([chain for _, chain, _ in scored_chains],
                         [["Author, L. L.", "Author, K.", "Author, Aaa"]])
        #                   ^ Author, L. L., _not_ Author, L.
        paper_choices = [pc for _, _, pc in scored_chains]
        self.assertEqual(paper_choices[0],
                         ((('paperKL2', 1, 2), ('paperAK', 1, 0),),))
        for doc in ['KL2', 'AK']:
            self.assertIn('paper' + doc, doc_data)
        self.assertEqual(2, len(doc_data))
