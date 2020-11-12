import copy
from unittest import TestCase
from unittest.mock import patch, MagicMock

from cache import cache_buddy

import ads_buddy
from repository import Repository
from tests import mock_backing_cache


@patch.object(ads_buddy, "requests", MagicMock)
class TestRecordCompression(TestCase):
    """Uses mock_backing_cache records to test compression & decompression
    
    Loads the author and document records. Checks that the decompressed
    records appear consistent. Re-compresses those records and checks that
    they match the compressed source records."""
    def setUp(self):
        self.real_backing_cache = cache_buddy.backing_cache
        cache_buddy.backing_cache = mock_backing_cache
        self.repository = Repository()
    
    def tearDown(self):
        cache_buddy.backing_cache = self.real_backing_cache
        self.real_backing_cache = None
        cache_buddy._loaded_authors = {}
        cache_buddy._loaded_documents = {}
    
    def test_author_record_compression(self):
        for author in mock_backing_cache.authors:
            raw_data = mock_backing_cache.load_author(author)
            raw_data = {**raw_data}
            del raw_data['version']
            record = self.repository.get_author_record(author)
            
            # We have an uncompressed record. Check it for consistency
            for alias in record.appears_as:
                raw_datum = raw_data['appears_as'][alias].split(',')
                self.assertEqual(len(record.appears_as[alias]),
                                 len(raw_datum))
                for idx, bibcode in zip(raw_datum, record.appears_as[alias]):
                    self.assertEqual(bibcode, record.documents[int(idx)])
            
            for coauthor in record.coauthors:
                raw_datum = raw_data['coauthors'][coauthor].split(',')
                self.assertEqual(len(record.coauthors[coauthor]),
                                 len(raw_datum))
                for idx, bibcode in zip(raw_datum, record.coauthors[coauthor]):
                    self.assertEqual(bibcode, record.documents[int(idx)])
            
            uncompressed_appears_as = copy.deepcopy(record.appears_as)
            uncompressed_coauthors = copy.deepcopy(record.coauthors)

            # Make sure the copy is independent of the original
            native_copy = record.copy()
            record.compress()
            self.assertNotEqual(record.asdict(), native_copy.asdict())

            for alias in record.appears_as:
                self.assertEqual(len(record.appears_as[alias].split(',')),
                                 len(uncompressed_appears_as[alias]))
            
            for coauthor in record.coauthors:
                self.assertEqual(len(record.coauthors[coauthor].split(',')),
                                 len(uncompressed_coauthors[coauthor]))
            
            # The source record in mock_backing_cache is compressed. Check that
            # it matches the re-compressed record
            self.assertEqual(raw_data, record.asdict())

            # Make sure the copy is independent of the original
            native_copy = record.copy()
            record.decompress()
            self.assertNotEqual(record.asdict(), native_copy.asdict())

    def test_document_record_compression(self):
        for document, raw_data in mock_backing_cache.documents.items():
            raw_data = {**raw_data}
            del raw_data['version']
            record = self.repository.get_document(document)
            
            # We have an uncompressed record. Check it for consistency
            self.assertEqual(len(record.authors), len(record.affils))
            self.assertEqual(len(record.authors), len(record.orcid_ids))
            self.assertEqual(len(record.authors), len(record.orcid_id_src))
            for orcid_id, src in zip(record.orcid_ids, record.orcid_id_src):
                if orcid_id == '':
                    self.assertEqual(src, 0)
                if src != 0:
                    self.assertNotEqual('', orcid_id)
            
            uncompressed_affils = copy.deepcopy(record.affils)
            uncompressed_orcid_ids = copy.deepcopy(record.orcid_ids)
            uncompressed_orcid_srcs = copy.deepcopy(record.orcid_id_src)

            # Make sure the copy is independent of the original
            native_copy = record.copy()
            record.compress()
            self.assertNotEqual(record.asdict(), native_copy.asdict())
            
            # Ensure only empty items are removed
            for affil in uncompressed_affils[len(record.affils):]:
                self.assertEqual(affil, '')
            for orcid_id in uncompressed_orcid_ids[len(record.orcid_ids):]:
                self.assertEqual(orcid_id, '')
            for orcid_src in uncompressed_orcid_srcs[len(record.orcid_id_src.split(',')):]:
                self.assertEqual(orcid_src, 0)
            
            # The source record in mock_backing_cache is compressed. Check that
            # it matches the re-compressed record
            self.assertEqual(raw_data, record.asdict())

            # Make sure the copy is independent of the original
            native_copy = record.copy()
            record.decompress()
            self.assertNotEqual(record.asdict(), native_copy.asdict())
