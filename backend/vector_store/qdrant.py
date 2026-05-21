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
    def __init__(self, collection_name="travel_knowledge_base", dimension=1024):
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY")
        
        self.client = QdrantClient(
            url=url,
            api_key=api_key if api_key else None,  # Bỏ qua nếu rỗng (Qdrant local)
            timeout=15
        )
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
                        "destination": chunk.get("destination"), # Ví dụ: "An Giang"
                        "category": chunk.get("category"),
                        "content": chunk.get("content"),
                        "text": chunk.get("text") or chunk.get("chunk_text"),
                        "source": ", ".join([s.get("url") for s in chunk.get("sources", []) if s.get("url")])
                    }
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    def search_travel(self, query_vector, sparse_query, destination=None, top_k=5):
        search_filter = None
        conditions = []

        if destination:
            conditions.append(FieldCondition(key="destination", match=MatchValue(value=destination)))
        
        if conditions:
            search_filter = Filter(must=conditions)

        print(f" [DEBUG QDRANT] Đang tìm kiếm với - Dest: {destination}")

        results = None
        if sparse_query:
            results = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        query=query_vector,
                        using="dense",
                        limit=top_k + 3,  # Giảm từ top_k*2 xuống top_k+3
                        filter=search_filter
                    ),
                    Prefetch(
                        query=sparse_query,
                        using="sparse",
                        limit=top_k + 3,
                        filter=search_filter
                    )
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=top_k,
                with_payload=True
            )
        else:
            # Fallback chỉ dùng Dense nếu không có Sparse
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                query_filter=search_filter,
                limit=top_k,
                with_payload=True
            )

        # For new qdrant-client versions, hits live in results.points
        hits = getattr(results, "points", results)

        formatted = []
        for point in hits:
            payload = point.payload or {}
            formatted.append({
                "chunk_id": payload.get("chunk_id"),
                "text": payload.get("text"), 
                "destination": payload.get("destination"),
                "category": payload.get("category"),
                "content": payload.get("content"),
                "source": payload.get("source"),
                "score": point.score
            })

        return formatted
