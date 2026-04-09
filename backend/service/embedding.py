import torch
from sentence_transformers import SentenceTransformer
from core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    EmbeddingService (BGE optimized)

    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = None
    ):
        self.model_name = model_name

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        logger.info(f"Loading embedding model: {model_name} on {self.device}")

        self.model = SentenceTransformer(model_name, device=self.device, local_files_only=True)

        logger.info(f"EmbeddingService initialized | dim={self.dimension}")

    # --------------------------------------------------
    # PROPERTIES
    # --------------------------------------------------

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    # --------------------------------------------------
    # CORE EMBEDDING
    # --------------------------------------------------

    def _encode(self, texts, batch_size=32):
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True   # 🔥 QUAN TRỌNG
        )

    # --------------------------------------------------
    # DOCUMENT EMBEDDING
    # --------------------------------------------------

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []

        logger.info(f"Encoding {len(texts)} documents...")

        #  BGE không bắt buộc instruction cho document
        embeddings = self._encode(texts, batch_size=batch_size)

        return embeddings.tolist()

    # --------------------------------------------------
    # QUERY EMBEDDING ( QUAN TRỌNG NHẤT)
    # --------------------------------------------------

    def embed_query(self, query: str) -> list[float]:
        """
        BGE yêu cầu prefix để search tốt hơn
        """

        #  KEY IMPROVEMENT
        query_text = f"Represent this sentence for searching relevant passages: {query}"

        embedding = self._encode([query_text])[0]

        return embedding.tolist()

    # --------------------------------------------------
    # SINGLE TEXT
    # --------------------------------------------------

    def embed_text(self, text: str) -> list[float]:
        embedding = self._encode([text])[0]
        return embedding.tolist()