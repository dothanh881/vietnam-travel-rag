import os
from functools import lru_cache
from langchain_openai import OpenAIEmbeddings
from core.logger import get_logger

logger = get_logger(__name__)

# Module-level cache: key = query text, value = embedding list
# Giữ tối đa 256 query gần nhất trong RAM
_EMBED_CACHE: dict = {}


class EmbeddingService:
    """
    EmbeddingService (OpenAI optimized)
    Sử dụng model text-embedding-3-small của OpenAI.
    """

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        device: str = None # Không dùng tới cho OpenAI API nhưng giữ lại để tương thích signature cũ
    ):
        self.model_name = model_name
        
        # Load API key từ môi trường
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY không được tìm thấy trong biến môi trường! EmbeddingService có thể sẽ lỗi.")

        logger.info(f"Loading embedding model: {model_name} via OpenAI API")

        self.model = OpenAIEmbeddings(
            model=self.model_name,
            openai_api_key=api_key
        )

        logger.info(f"EmbeddingService initialized via OpenAI.")

    # --------------------------------------------------
    # PROPERTIES
    # --------------------------------------------------

    @property
    def dimension(self) -> int:
        # text-embedding-3-small có mặc định 1536 chiều
        return 1536

    # --------------------------------------------------
    # DOCUMENT EMBEDDING
    # --------------------------------------------------

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []

        logger.info(f"Encoding {len(texts)} documents using OpenAI...")

        # OpenAI API xử lý batch tự động khá tốt, nhưng ta có thể chunk ra nếu số lượng lớn
        # Langchain OpenAIEmbeddings mặc định chia chunk 1000 cho embed_documents
        embeddings = self.model.embed_documents(texts)

        return embeddings

    # --------------------------------------------------
    # QUERY EMBEDDING ( QUAN TRỌNG NHẤT)
    # --------------------------------------------------

    def embed_query(self, query: str) -> list[float]:
        """
        Có embedding cache để tránh gọi API lại cho cùng câu hỏi.
        """
        # Cache key = normalized query
        cache_key = query.strip().lower()
        if cache_key in _EMBED_CACHE:
            logger.debug(f"[EmbedCache] HIT: '{query[:40]}'")
            return _EMBED_CACHE[cache_key]
        
        embedding = self.model.embed_query(query)
        
        # Lưu cache, giới hạn 256 entry (xóa entry cũ nhất nếu đầy)
        if len(_EMBED_CACHE) >= 256:
            oldest = next(iter(_EMBED_CACHE))
            del _EMBED_CACHE[oldest]
        _EMBED_CACHE[cache_key] = embedding
        
        return embedding

    # --------------------------------------------------
    # SINGLE TEXT
    # --------------------------------------------------

    def embed_text(self, text: str) -> list[float]:
        return self.embed_query(text)
