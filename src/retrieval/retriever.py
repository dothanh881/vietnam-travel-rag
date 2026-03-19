class TravelRetriever:
    def __init__(self, embedding_service, search_engine, analyzer):
        self.embedding_service = embedding_service
        self.search_engine = search_engine
        self.analyzer = analyzer

    def retrieve(self, query: str, top_k: int = 5, destination: str = None, category: str = None):
        # 1. Phân tích câu hỏi để tự động tìm tỉnh/thành và danh mục
        analyzed = self.analyzer.analyze(query)

        # 2. Gộp dữ liệu: Ưu tiên những gì AI phân tích được từ câu hỏi,
        # nếu không có thì mới xài cái UI truyền xuống (destination, category)
        final_destination = analyzed.get("destination") or destination

        # Intent từ analyzer ('food', 'place'...) sẽ biến thành category
        final_category = analyzed.get("intent") if analyzed.get("intent") != "general" else category

        # 3. Biến câu hỏi thành Vector
        query_vector = self.embedding_service.embed_query(query)

        # 4. Tìm kiếm với Search Engine (đã được bơm đầy đủ filter)
        # Lưu ý: Tên hàm có thể là .search() hoặc .search_travel() tùy vào file search.py của bạn
        results = self.search_engine.search(
            query_vector=query_vector,
            destination=final_destination,
            category=final_category,
            top_k=top_k
        )

        return results