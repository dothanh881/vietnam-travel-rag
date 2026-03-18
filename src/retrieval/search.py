class VectorSearchEngine:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(self, query_vector, top_k=5, filters=None):
        destination = None
        category = None

        if filters:
            destination = filters.get("destination")
            category = filters.get("category")

        return self.vector_store.search_travel(
            query_vector=query_vector,
            destination=destination,
            category=category,
            top_k=top_k
        )