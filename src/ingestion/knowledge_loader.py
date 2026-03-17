import json
from core.logger import get_logger

logger = get_logger(__name__)

class KnowledgeLoader:
    def __init__(self, vector_store, embedding_service):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def load_json(self, file_path: str):
        """Đọc file JSON và chuẩn bị dữ liệu"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def process_and_store(self, chunks: list[dict]) -> int:
        """
        Nhận list các chunk, tính embedding và lưu vào Vector Store.
        """
        texts_to_embed = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_service.embed_documents(texts_to_embed)

        self.vector_store.upsert_chunks(chunks, embeddings)
        return len(chunks)
