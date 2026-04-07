import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    PayloadSchemaType,
    Filter,
    FieldCondition,
    MatchValue,
    SparseVectorParams,
    SparseIndexParams,
    Prefetch,
    FusionQuery,
    Fusion,
    SparseVector
)


class TravelVectorStore:
    def __init__(self, collection_name="travel_knowledge_base", dimension=1024, url="http://localhost:6333"):
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.dimension = dimension

        self._ensure_collection()

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
                vectors_config={"dense": VectorParams(size=self.dimension, distance=Distance.COSINE)},
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=SparseIndexParams(on_disk=False)
                    )
                }
            )
            # Tạo Payload Index để lọc theo địa danh và hạng mục cực nhanh [cite: 118, 120]
            self.client.create_payload_index(self.collection_name, "destination", PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(self.collection_name, "category", PayloadSchemaType.KEYWORD)

    def upsert_chunks(self, chunks: list[dict], dense_embeddings: list[list[float]], sparse_embeddings: list[SparseVector]):
        """
        Đưa tất cả các trường từ file chunk vào Payload. [cite: 104, 116]
        """
        points = []
        for chunk, emb, sparse_emb in zip(chunks, dense_embeddings, sparse_embeddings):
            vector_dict = {"dense": emb}
            if sparse_emb is not None:
                vector_dict["sparse"] = sparse_emb
                
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector_dict,
                    payload={
                        "chunk_id": chunk.get("chunk_id"),
                        "doc_id": chunk.get("parent_doc_id") or chunk.get("doc_id"),
                        "destination": chunk.get("destination"),  # Dùng để filter theo vùng miền [cite: 121]
                        "category": chunk.get("category"),  # Dùng để filter theo loại hình (food, place) [cite: 78]
                        "content": chunk.get("content"),  # Metadata chi tiết: giá, địa chỉ... [cite: 111]
                        "text": chunk.get("chunk_text") or chunk.get("text")  # Ngữ cảnh cho LLM [cite: 101]
                    }
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    def search_travel(self, query_vector, sparse_query, destination=None, category=None, top_k=5):
        search_filter = None
        conditions = []

        # if destination:
        #     conditions.append(FieldCondition(key="destination", match=MatchValue(value=destination)))
        # if category:
        #     conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))
        #
        # if conditions:
        #     search_filter = Filter(must=conditions)

        print(f" [DEBUG QDRANT] Đang tìm kiếm với - Dest: {destination} | Cat: {category}")

        results = None
        if sparse_query:
            results = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        query=query_vector,
                        using="dense",
                        limit=top_k * 2,
                        filter=search_filter
                    ),
                    Prefetch(
                        query=sparse_query,
                        using="sparse",
                        limit=top_k * 2,
                        filter=search_filter
                    )
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=top_k,
                with_payload=True
            )
        else:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=search_filter,
                limit=top_k,
                with_payload=True
            )

        # For new qdrant-client versions, hits live in results.points
        hits = getattr(results, "points", results)

        formatted = []
        for r in hits:
            # r may be a tuple (point, score) in some APIs
            point = r[0] if isinstance(r, tuple) else r

            payload = getattr(point, "payload", None) or {}
            score = getattr(point, "score", None)

            formatted.append({
                "text": payload.get("text"),
                "destination": payload.get("destination"),
                "category": payload.get("category"),
                "content": payload.get("content"),
                "score": score
            })

        return formatted