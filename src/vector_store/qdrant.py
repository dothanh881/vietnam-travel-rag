import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    PayloadSchemaType,
    Filter,
    FieldCondition,
    MatchValue
)


class TravelVectorStore:
    def __init__(self, collection_name="travel_knowledge_base", dimension=1024, url="http://localhost:6333"):
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.dimension = dimension

        # Tự động khởi tạo collection và index
        self.recreate_collection()

    def recreate_collection(self):
        """Xóa và tạo lại collection."""
        self.client.delete_collection(collection_name=self.collection_name)
        self._ensure_collection()

    def _ensure_collection(self):
        """Tạo collection và đánh index cho các trường cần lọc."""
        collections = [c.name for c in self.client.get_collections().collections]

        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
            )
            # Tạo Payload Index để lọc theo địa danh và hạng mục cực nhanh [cite: 118, 120]
            self.client.create_payload_index(self.collection_name, "destination", PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(self.collection_name, "category", PayloadSchemaType.KEYWORD)

    def upsert_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        """
        Đưa tất cả các trường từ file chunk vào Payload. [cite: 104, 116]
        """
        points = []
        for chunk, emb in zip(chunks, embeddings):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb,  # Sử dụng embedding của trường 'text' [cite: 69]
                    payload={
                        "chunk_id": chunk.get("chunk_id"),
                        "doc_id": chunk.get("doc_id"),
                        "destination": chunk.get("destination"),  # Dùng để filter theo vùng miền [cite: 121]
                        "category": chunk.get("category"),  # Dùng để filter theo loại hình (food, place) [cite: 78]
                        "content": chunk.get("content"),  # Metadata chi tiết: giá, địa chỉ... [cite: 111]
                        "text": chunk.get("text")  # Ngữ cảnh cho LLM [cite: 101]
                    }
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    def search_travel(self, query_vector: list[float], destination: str = None, category: str = None, top_k: int = 5):
        """
        Tìm kiếm có hỗ trợ lọc theo địa danh và hạng mục.
        """
        search_filter = None
        conditions = []

        if destination:
            conditions.append(FieldCondition(key="destination", match=MatchValue(value=destination)))
        if category:
            conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))

        if conditions:
            search_filter = Filter(must=conditions)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=top_k,
            with_payload=True
        )
        return results