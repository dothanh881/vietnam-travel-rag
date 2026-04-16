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
        1. Nhận diện địa danh & rã câu hỏi ghép qua Local Analyzer siêu tốc
        2. Truy vấn Hybrid (Dense + Sparse) có Filter (Đơn lẻ hoặc Sub-queries)
        3. Lọc kết quả và Deduplicate (Score >= 0.35)
        """
        # 1. DÙNG ANALYZER (Zero-LLM) ĐỂ PHÂN TÍCH SÂU
        analysis = self.analyzer.analyze(query)
        
        final_destination = analysis.get("destination") or destination
        search_query = analysis.get("expanded_query") or query
        sub_queries = analysis.get("sub_queries", [])

        logger.info(f" [Retriever] Query: {query} -> Dest: {final_destination} | SubQueries: {len(sub_queries)}")

        all_results = []
        
        # 2A. TRANH THỦ CHIA TRỊ NẾU LÀ CÂU HỎI GHÉP (Compound Query)
        if sub_queries and len(sub_queries) > 1:
            k_per_query = max(int((top_k / len(sub_queries)) + 1), 3)
            merged_ids = set()
            for sq in sub_queries:
                q_vec = self.embedding_service.embed_query(sq)
                s_vec = self.bm25_encoder.encode_query(sq) if self.bm25_encoder else None
                res = self.search_engine.search(
                    query_vector=q_vec,
                    sparse_vector=s_vec,
                    destination=final_destination, 
                    top_k=k_per_query
                )
                for r in res:
                    u_id = r.get("id", r.get("text", "")) # Hash tạm bằng text nếu thiếu id
                    if u_id not in merged_ids and r.get("score", 0.0) >= 0.35:
                        merged_ids.add(u_id)
                        all_results.append(r)
        
        # 2B. CÂU HỎI ĐƠN
        else:
            query_vector = self.embedding_service.embed_query(search_query)
            sparse_vector = None
            if self.bm25_encoder:
                sparse_vector = self.bm25_encoder.encode_query(search_query)

            results = self.search_engine.search(
                query_vector=query_vector,
                sparse_vector=sparse_vector,
                destination=final_destination, 
                top_k=top_k
            )

            # LỌC THEO NGƯỠNG ĐIỂM
            all_results = [r for r in results if r.get("score", 0.0) >= 0.35]

        # Sắp xếp lại tổng thể nếu lấy từ nhiều nguồn
        if sub_queries and len(sub_queries) > 1:
            all_results = sorted(all_results, key=lambda x: x.get("score", 0.0), reverse=True)
            if len(all_results) > top_k:
                all_results = all_results[:top_k]

        logger.info(f" [Retriever] Giữ lại {len(all_results)} kết quả (Score >= 0.35)")

        return all_results
