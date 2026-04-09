import cohere
import os
from core.logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger(__name__)

class CohereReranker:
    """
    Reranker sử dụng Cohere Rerank API (Cloud).
    Model: rerank-multilingual-v3.0 (Tốt nhất cho tiếng Việt).
    """
    def __init__(self, api_key: str = None, model: str = "rerank-multilingual-v3.0"):
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        if not self.api_key:
            logger.error("COHERE_API_KEY không được tìm thấy trong môi trường (.env)")
            raise ValueError("Vui lòng cấu hình COHERE_API_KEY trong file .env")
        
        self.client = cohere.Client(self.api_key)
        self.model = model
        logger.info(f"CohereReranker khởi tạo thành công với model: {self.model}")

    def rerank(self, query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
        """
        Gửi danh sách candidates lên Cohere để sắp xếp lại.
        """
        if not candidates:
            return []
            
        # Trích xuất nội dung text để gửi lên API
        documents = [c.get("text", "") for c in candidates]
        
        try:
            # Gọi API Cohere
            response = self.client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=top_n
            )
            
            # Khớp lại kết quả với dữ liệu gốc
            reranked_results = []
            for result in response.results:
                original_idx = result.index
                doc = candidates[original_idx]
                doc["rerank_score"] = result.relevance_score
                reranked_results.append(doc)
                
            logger.info(f"Cohere Reranking hoàn tất cho {len(reranked_results)} kết quả.")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Lỗi khi gọi Cohere Rerank API: {str(e)}")
            # Nếu lỗi API, trả về kết quả gốc để không làm hỏng luồng RAG
            return candidates[:top_n]
