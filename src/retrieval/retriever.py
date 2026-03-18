class TravelRetriever:
    def __init__(self, embedding_service, search_engine, analyzer=None):
        self.embedding_service = embedding_service
        self.search_engine = search_engine
        self.analyzer = analyzer

    def retrieve(self, query: str, top_k=5):

        # -------- analyze query --------
        filters = None

        if self.analyzer:
            info = self.analyzer.analyze(query)

            filters = {}

            if info.get("destination"):
                filters["destination"] = info["destination"]

            if info.get("intent") != "general":
                filters["category"] = info["intent"]

        # -------- embed --------
        query_vector = self.embedding_service.embed_query(query)

        # -------- search --------
        results = self.search_engine.search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters
        )

        # fallback nếu filter fail
        if not results and filters:
            results = self.search_engine.search(
                query_vector=query_vector,
                top_k=top_k,
                filters=None
            )

        return results