from core.logger import get_logger
from langfuse import observe

logger = get_logger(__name__)

class TravelRetriever:
    def __init__(self, embedding_service, search_engine, analyzer, bm25_encoder=None):
        self.embedding_service = embedding_service
        self.search_engine = search_engine
        self.analyzer = analyzer
        self.bm25_encoder = bm25_encoder

    @observe(as_type="generation", name="1_Qdrant_Search")
    def retrieve(self, query: str, top_k: int = 5, destination: str = None):
        """
        Quy trình chuẩn:
        1. Nhận diện địa danh & mở rộng truy vấn qua LLM Analyzer
        2. Truy vấn Hybrid (Dense + Sparse) có Filter
        3. Lọc kết quả theo ngưỡng Score 0.35
        """
        # 1. DÙNG ANALYZER (LLM) ĐỂ PHÂN TÍCH SÂU
        analysis = self.analyzer.analyze(query)
        
        final_destination = analysis.get("destination") or destination
        search_query = analysis.get("expanded_query") or query

        logger.info(f" [Retriever] Query: {query} -> Dest: {final_destination} | Expanded: {search_query}")

        # 2. Chuyển đổi sang Vectors dùng expanded_query
        query_vector = self.embedding_service.embed_query(search_query)
        
        # Sparse Vector (Keyword matching)
        sparse_vector = None
        if self.bm25_encoder:
            sparse_vector = self.bm25_encoder.encode_query(search_query)

        # 3. Truy vấn Qdrant với STRICT FILTER theo destination
        results = self.search_engine.search(
            query_vector=query_vector,
            sparse_vector=sparse_vector,
            destination=final_destination, 
            top_k=top_k
        )

        # 4. LỌC THEO NGƯỠNG ĐIỂM (Score >= 0.35)
        # Điểm Cosine Similarity mốc 0.35 là mốc an toàn để loại bỏ kết quả nhiễu
        filtered_results = [r for r in results if r.get("score", 0.0) >= 0.35]
        
        logger.info(f" [Retriever] Tìm thấy {len(results)} kết quả -> Giữ lại {len(filtered_results)} kết quả (Score >= 0.35)")

        return filtered_results
