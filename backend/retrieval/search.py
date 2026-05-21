class VectorSearchEngine:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(self, query_vector: list[float], sparse_vector, top_k: int = 5, destination: str = None):
        """
        Nhận vector câu hỏi và các bộ lọc từ Retriever,
        sau đó đẩy thẳng xuống cho Qdrant (TravelVectorStore) xử lý.
        """
        return self.vector_store.search_travel(
            query_vector=query_vector,
            sparse_query=sparse_vector,
            destination=destination,
            top_k=top_k
        )
