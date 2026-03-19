class VectorSearchEngine:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(self, query_vector: list[float], top_k: int = 5, destination: str = None, category: str = None):
        """
        Nhận vector câu hỏi và các bộ lọc từ Retriever,
        sau đó đẩy thẳng xuống cho Qdrant (TravelVectorStore) xử lý.
        """
        return self.vector_store.search_travel(
            query_vector=query_vector,
            destination=destination,
            category=category,
            top_k=top_k
        )