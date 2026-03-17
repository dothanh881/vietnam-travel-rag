import os
import torch
from sentence_transformers import SentenceTransformer
from core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    EmbeddingService: Sử dụng model BGE (BAAI General Embedding) chạy Local.
    Phù hợp cho cả tiếng Việt và tiếng Anh (phiên bản m3 hoặc multilingual).
    """

    def __init__(
            self,
            model_name: str = "BAAI/bge-m3",  # Model đa ngôn ngữ cực tốt cho tiếng Việt
            device: str = None
    ):
        """
        Args:
            model_name: Tên model trên HuggingFace.
                        - 'BAAI/bge-small-en-v1.5' (Nhẹ)
                        - 'BAAI/bge-m3'
            device: 'cuda', 'cpu
                    Nếu để None sẽ tự động chọn.
        """
        self.model_name = model_name

        # Tự động chọn thiết bị chạy (Ưu tiên GPU nếu có)
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Đang tải model Embedding: {model_name} trên thiết bị: {self.device}")

        # Tải model về máy (chỉ tải lần đầu)
        self.model = SentenceTransformer(model_name, device=self.device)

        logger.info(f"EmbeddingService initialized | model={model_name} | dim={self.dimension}")

    @property
    def dimension(self) -> int:
        """Trả về dimension của model hiện tại."""
        return self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> list[float]:
        """Embed 1 đoạn text đơn lẻ."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Embed danh sách văn bản.
        Sentence-transformers đã tối ưu sẵn việc chạy batch và song song trên GPU.
        """
        if not texts:
            return []

        logger.info(f"Bắt đầu encode {len(texts)} chunks bằng {self.model_name}...")

        # BGE thường cần thêm hướng dẫn (instruction) để đạt hiệu quả cao nhất
        # Tuy nhiên với bge-m3 thì không bắt buộc cho document.
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """
        Embed câu hỏi của người dùng.
        'Represent this sentence for searching relevant passages: '

        """
        return self.embed_text(query)