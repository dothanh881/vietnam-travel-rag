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
        Quy trình tối ưu:
        1. Phân tích query (Zero-LLM)
        2. Chạy Dense + Sparse embedding SONG SONG
        3. Truy vấn Qdrant Hybrid Search
        4. Lọc và dedup kết quả
        """
        from concurrent.futures import ThreadPoolExecutor

        # 1. Phân tích query
        analysis = self.analyzer.analyze(query)
        final_destination = analysis.get("destination") or destination
        search_query = analysis.get("expanded_query") or query
        sub_queries = analysis.get("sub_queries", [])

        logger.info(f" [Retriever] Query: {query} -> Dest: {final_destination} | SubQueries: {len(sub_queries)}")

        def _embed_pair(q: str):
            """Chạy Dense + Sparse embedding song song cho 1 query."""
            with ThreadPoolExecutor(max_workers=2) as ex:
                f_dense = ex.submit(self.embedding_service.embed_query, q)
                f_sparse = ex.submit(self.bm25_encoder.encode_query, q) if self.bm25_encoder else None
                q_vec = f_dense.result()
                s_vec = f_sparse.result() if f_sparse else None
            return q_vec, s_vec

        all_results = []

        # 2A. Câu hỏi ghép
        if sub_queries and len(sub_queries) > 1:
            k_per_query = max(int((top_k / len(sub_queries)) + 1), 3)
            merged_ids = set()
            for sq in sub_queries:
                q_vec, s_vec = _embed_pair(sq)
                res = self.search_engine.search(
                    query_vector=q_vec,
                    sparse_vector=s_vec,
                    destination=final_destination,
                    top_k=k_per_query
                )
                for r in res:
                    u_id = r.get("id", r.get("text", ""))
                    if u_id not in merged_ids and r.get("score", 0.0) >= 0.35:
                        merged_ids.add(u_id)
                        all_results.append(r)

        # 2B. Câu hỏi đơn
        else:
            q_vec, s_vec = _embed_pair(search_query)
            results = self.search_engine.search(
                query_vector=q_vec,
                sparse_vector=s_vec,
                destination=final_destination,
                top_k=top_k
            )
            all_results = [r for r in results if r.get("score", 0.0) >= 0.35]

        if sub_queries and len(sub_queries) > 1:
            all_results = sorted(all_results, key=lambda x: x.get("score", 0.0), reverse=True)
            if len(all_results) > top_k:
                all_results = all_results[:top_k]

        logger.info(f" [Retriever] Giữ lại {len(all_results)} kết quả (Score >= 0.35)")
        return all_results
