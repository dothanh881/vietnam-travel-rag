from ingestion.knowledge_loader import KnowledgeLoader
from vector_store.qdrant import TravelVectorStore
from service.embedding import EmbeddingService

class IngestionPipeline:
    def __init__(self):
        self.vector_store = TravelVectorStore()
        self.embedding_service = EmbeddingService()
        # Pipeline sở hữu một Loader để làm việc
        self.loader = KnowledgeLoader(self.vector_store, self.embedding_service)

    def run(self, file_path: str):
        """Chạy luồng ingest rút gọn cho Base Knowledge"""
        chunks = self.loader.load_json(file_path)
        result = self.loader.process_and_store(chunks)
        return result