import cache_db_access

class PaperCache:
    
    def __init__(self):
        self.cnx = cache_db_access.create_db_connection()
    
    def get_papers_for_author(self, author):
        return False, []
    
    def submit_records_for_caching(self, records):
        pass