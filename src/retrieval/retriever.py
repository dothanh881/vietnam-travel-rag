from core.logger import get_logger

logger = get_logger(__name__)

class TravelRetriever:
    def __init__(self, embedding_service, search_engine, analyzer, bm25_encoder=None):
        self.embedding_service = embedding_service
        self.search_engine = search_engine
        self.analyzer = analyzer
        self.bm25_encoder = bm25_encoder

    def retrieve(self, query: str, top_k: int = 5, destination: str = None):
        # SIÊU TỐC ĐỘ: Dùng trực tiếp query để tìm kiếm
        search_query = query
        final_destination = destination

        # NHẬN DIỆN ĐỊA DANH THÔNG MINH (Bằng từ khóa để bỏ qua LLM delay)
        query_lower = query.lower()
        if "đà lạt" in query_lower:
            final_destination = "Đà Lạt"
        elif "an giang" in query_lower:
            final_destination = "An Giang"
        elif "phú quốc" in query_lower:
            final_destination = "Phú Quốc"

        logger.info(f" [Retriever] Fast Search Query: {search_query} | Auto-Dest: {final_destination}")

        # 3. Chuyển đổi sang Vectors dùng expanded_query
        # Dense Vector (Semantic)
        query_vector = self.embedding_service.embed_query(search_query)
        
        # Sparse Vector (Keyword matching)
        sparse_vector = None
        if self.bm25_encoder:
            # Bạn nên dùng search_query ở đây để BM25 bắt được nhiều từ khóa "địa chỉ", "giá vé" hơn
            sparse_vector = self.bm25_encoder.encode_query(search_query)

        # 4. Truy vấn Qdrant
        # Đảm bảo hàm search này trong search_engine xử lý Filter theo "Phú Quốc" (có dấu)
        results = self.search_engine.search(
            query_vector=query_vector,
            sparse_vector=sparse_vector,
            destination=final_destination, 
            top_k=top_k
        )

        return results