import time
from sentence_transformers import CrossEncoder
from core.logger import get_logger

logger = get_logger(__name__)

class Reranker:
    """
    Reranker sử dụng mô hình Cross-Encoder chuyên dụng (bge-reranker-m3).
    Tối ưu cho Tiếng Việt, tốc độ siêu nhanh, chấm điểm chính xác.
    """
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        logger.info(f"Đang nạp mô hình Reranker: {model_name}...")
        
        import torch
        # Tự động lấy device tương thích để tránh lỗi Torch not compiled with CUDA
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Chạy Reranker trên thiết bị: {device}")
        
        # local_files_only=True để tránh check update lên HuggingFace khi server HF bị lỗi
        self.model = CrossEncoder(model_name, max_length=512, device=device, local_files_only=True)
        logger.info("Nạp Reranker thành công!")

    def rerank(self, query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
        if not candidates:
            return []

        top_n = min(top_n, len(candidates))
        logger.info(f"Đang Rerank {len(candidates)} candidates -> Lấy Top {top_n}")
        t0 = time.perf_counter()

        # Tạo danh sách các cặp [Câu hỏi, Tài liệu]
        # Cross-Encoder yêu cầu đầu vào là 1 mảng các cặp câu
        sentence_pairs = [[query, doc["text"]] for doc in candidates]

        # Model tự động tính điểm cho tất cả các cặp trong 1 nốt nhạc
        scores = self.model.predict(sentence_pairs)

        # Gắn điểm vào candidates và sắp xếp
        scored_candidates = []
        for doc, score in zip(candidates, scores):
            doc["rerank_score"] = float(score) # Điểm số là 1 số float
            scored_candidates.append(doc)

        # Sắp xếp từ cao xuống thấp
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        top_results = scored_candidates[:top_n]

        elapsed = time.perf_counter() - t0
        logger.info(f"Reranking hoàn tất trong {elapsed:.2f}s")
        
        return top_results