from unittest import TestCase
from unittest.mock import patch, MagicMock

from cache import cache_buddy

import ads_buddy
from repository import Repository
from tests import mock_backing_cache


@patch.object(ads_buddy, "requests", MagicMock)
class TestRepository(TestCase):
    def setUp(self):
        self.real_backing_cache = cache_buddy.backing_cache
        cache_buddy.backing_cache = mock_backing_cache
        self.repository = Repository()
        mock_backing_cache.store_author.reset_mock()
    
    def tearDown(self):
        cache_buddy.backing_cache = self.real_backing_cache
        cache_buddy._loaded_authors = {}
        cache_buddy._loaded_documents = {}
        mock_backing_cache.store_author.reset_mock()
    
    def test_get_author(self):
        record = self.repository.get_author_record('author, a.')
        record.compress()
        record = record.asdict()
        record['version'] = cache_buddy.AUTHOR_VERSION_NUMBER
        self.assertEqual(record,
                         mock_backing_cache.load_author('author, a.'))
    
    def test_get_document(self):
        record = self.repository.get_document('paperAB')
        record.compress()
        record = record.asdict()
        record['version'] = cache_buddy.DOCUMENT_VERSION_NUMBER
        self.assertEqual(record,
                         mock_backing_cache.documents['paperAB'])
    
    def test_author_record_generation(self):
        record = self.repository.get_author_record('>author, a.')
        self.assertEqual(len(record.documents), 3)
        self.assertEqual(record.documents[0], 'paperAB2')
        self.assertEqual(record.documents[1], 'paperAE')
        self.assertEqual(record.documents[2], 'paperAK')
        
        mock_backing_cache.store_author.assert_called_once()
        cached_record = mock_backing_cache.store_author.call_args[0][0]
        self.assertEqual(cached_record['name'], '>author, a.')
        self.assertEqual(cached_record['documents'], record.documents)
        mock_backing_cache.store_author.reset_mock()
        
        record = self.repository.get_author_record('=author, a.')
        
        self.assertEqual(len(record.documents), 1)
        self.assertEqual(sorted(record.documents)[0], 'paperAB')
        
        mock_backing_cache.store_author.assert_called_once()
        cached_record = mock_backing_cache.store_author.call_args[0][0]
        self.assertEqual(cached_record['name'], '=author, a.')
        self.assertEqual(cached_record['documents'], record.documents)
        mock_backing_cache.store_author.reset_mock()
        
        record = self.repository.get_author_record('<author, aa')
        
        self.assertEqual(len(record.documents), 1)
        self.assertEqual(sorted(record.documents)[0], 'paperAB')
        
        mock_backing_cache.store_author.assert_called_once()
        cached_record = mock_backing_cache.store_author.call_args[0][0]
        self.assertEqual(cached_record['name'], '<author, aa')
        self.assertEqual(cached_record['documents'], record.documents)
        mock_backing_cache.store_author.reset_mock()
