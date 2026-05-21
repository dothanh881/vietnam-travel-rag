import json
from core.logger import get_logger

logger = get_logger(__name__)

class KnowledgeLoader:
    def __init__(self, vector_store, embedding_service, bm25_encoder=None):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.bm25_encoder = bm25_encoder

    def load_json(self, file_path: str):
        """Đọc file JSON và chuẩn bị dữ liệu"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def process_and_store(self, chunks: list[dict]) -> int:
        """
        Nhận list các chunk, tính embedding và lưu vào Vector Store.
        """
        # Sửa 'text' thành 'chunk_text' cho khớp với Payload của Chunk Layer
        texts_to_embed = [chunk.get('chunk_text', '') for chunk in chunks]
        embeddings = self.embedding_service.embed_documents(texts_to_embed)
        
        # Calculate sparse embeddings if encoder is available and fitted
        if self.bm25_encoder and self.bm25_encoder._fitted:
            sparse_embeddings = self.bm25_encoder.encode_documents(texts_to_embed)
        else:
            sparse_embeddings = [None] * len(texts_to_embed)

        self.vector_store.upsert_chunks(chunks, embeddings, sparse_embeddings)
        return len(chunks)
