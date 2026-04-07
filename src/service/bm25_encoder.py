import os
import re
import math
import json
from pathlib import Path
from qdrant_client.models import SparseVector
from core.logger import get_logger

logger = get_logger(__name__)

# BM25 hyperparameters — Dành cho văn bản review/mô tả du lịch (thường ngắn đến trung bình)
_K1: float = 1.5   # Kiểm soát ảnh hưởng của TF (tần số xuất hiện của từ khóa)
_B:  float = 0.75  # Kiểm soát ảnh hưởng của độ dài document (phạt các bài review quá dài)

# ---------------------------------------------------------------------------
# Vietnamese Travel Stopwords
# Loại bỏ từ nối và những "rác ngữ nghĩa" xuất hiện ở mọi bài review du lịch.
# Các danh từ riêng (tên quán, địa danh) và tính từ đặc tả (ngon, rẻ, đẹp) ĐƯỢC GIỮ LẠI.
# ---------------------------------------------------------------------------
VIETNAMESE_TRAVEL_STOPWORDS: frozenset[str] = frozenset([
    # Đại từ / Liên từ / Từ đệm phổ biến
    "đây", "đó", "để", "đến", "được", "điều", "đi", "đã",
    "và", "với", "về", "vì", "vậy", "vẫn", "vào",
    "các", "của", "có", "còn", "cũng", "càng", "cần", "cả",
    "là", "lên", "lại", "lúc", "loại",
    "trong", "theo", "tại", "từ", "tới",
    "khi", "không", "khác", "hoặc", "hơn", "hết",
    "này", "nếu", "như", "nhưng", "những",
    "bằng", "bất", "bên", "bởi",
    "mà", "mỗi", "mọi", "một", "mới",
    "sẽ", "sau", "so", "qua", "chỉ", "cho", "chưa", "giữa",
    "rằng", "rất", "thì", "thêm", "thu",
    "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười",
    
    # Từ rác đặc thù mảng Du lịch (xuất hiện khắp nơi, làm nhiễu BM25)
    "du_lịch", "khách", "du_khách", "địa_điểm", "nơi", "vùng", 
    "chuyến", "tham_quan", "trải_nghiệm", "cảm_nhận", "người",
    "chi_tiết", "tổng_quan", "thông_tin", "nội_dung", "bài_viết"
])

class TravelBM25Encoder:
    """
    BM25 Sparse Encoder chuyên dụng cho văn bản Du Lịch Việt Nam.

    Chuyển text → sparse vector {index: weight} để lưu vào Qdrant (Hybrid Search).
    Điểm nổi bật:
        1. Dùng Underthesea để giữ nguyên tên món ăn, địa danh (VD: "gỏi_đu_đủ", "núi_Sam").
        2. Tự động loại bỏ các từ vô giá trị (IDF thấp).
        3. Lưu trạng thái (Persist) để đồng bộ Vector không bị lệch khi restart API.
    """

    def __init__(
        self,
        vocab_path: str = None,
        stopwords: frozenset[str] = None,
        min_idf_threshold: float = 0.15,
    ):
        """
        Args:
            vocab_path: Đường dẫn file JSON để lưu/load vocabulary.
            stopwords: Tập từ dừng. None = dùng VIETNAMESE_TRAVEL_STOPWORDS.
            min_idf_threshold: Ngưỡng IDF. Từ nào xuất hiện ở quá nhiều bài viết (< 0.15) sẽ bị loại.
        """
        self.vocab_path = vocab_path
        self.stopwords: frozenset[str] = (
            stopwords if stopwords is not None else VIETNAMESE_TRAVEL_STOPWORDS
        )
        self.min_idf_threshold = min_idf_threshold

        self.vocab: dict[str, int] = {}    # token → index
        self.idf: dict[str, float] = {}    # token → idf weight
        self.avg_len: float = 50.0         # avg document length, mặc định 50 cho du lịch
        self._fitted = False               # Cờ đánh dấu đã fit data hay chưa

        # Tự động load vocab nếu file đã tồn tại
        if vocab_path and os.path.exists(vocab_path):
            self.load(vocab_path)

    # ------------------------------------------------------------------
    # 1. Tokenization (Tách từ)
    # ------------------------------------------------------------------
    def _tokenize(self, text: str) -> list[str]:
        """
        Tách từ tiếng Việt chuẩn xác bằng Underthesea.
        Đảm bảo "gỏi đu đủ" -> "gỏi_đu_đủ" chứ không bị nát thành 3 từ.
        """
        try:
            from underthesea import word_tokenize
            segmented = word_tokenize(text.lower(), format="text")
        except ImportError:
            logger.warning("[BM25] underthesea chưa cài → fallback whitespace. Khuyên dùng: pip install underthesea")
            segmented = text.lower()

        # Loại bỏ dấu câu, chỉ giữ chữ và số và dấu gạch dưới (_)
        tokens = re.split(r"[^\w]+", segmented)
        
        # Lọc tokens ngắn và stopwords
        tokens = [
            t for t in tokens
            if len(t) >= 2 and t not in self.stopwords
        ]
        return tokens

    # ------------------------------------------------------------------
    # 2. Huấn luyện (Fit) - Tính toán Trọng số
    # ------------------------------------------------------------------
    def fit(self, texts: list[str]):
        """
        Huấn luyện BM25 trên tập dữ liệu Du Lịch (Corpus).
        Chạy 1 lần duy nhất lúc Ingest dữ liệu ban đầu.
        """
        logger.info("Đang huấn luyện BM25 trên %d chunks dữ liệu du lịch...", len(texts))

        # Bước 1: Tokenize toàn bộ
        tokenized_docs = [self._tokenize(t) for t in texts]

        # Bước 2: Tính tần suất Document Frequency (DF)
        N = len(tokenized_docs)
        df: dict[str, int] = {}
        for doc_tokens in tokenized_docs:
            for token in set(doc_tokens):
                df[token] = df.get(token, 0) + 1

        # Tính IDF thô
        raw_idf: dict[str, float] = {
            token: math.log((N - freq + 0.5) / (freq + 0.5) + 1)
            for token, freq in df.items()
        }

        # Bước 3: Tính chiều dài trung bình của các bài viết
        total_tokens = sum(len(doc) for doc in tokenized_docs)
        self.avg_len = total_tokens / N if N > 0 else 1.0
        logger.info("Chiều dài chunk trung bình (avg_len): %.1f tokens", self.avg_len)

        # Bước 4: Lọc rác (Những từ có IDF quá thấp)
        kept_tokens = {
            token for token, idf_val in raw_idf.items()
            if idf_val >= self.min_idf_threshold
        }
        filtered_count = len(raw_idf) - len(kept_tokens)
        if filtered_count:
            logger.info("Đã lọc %d tokens rác vì xuất hiện quá thường xuyên (IDF < %.2f)", 
                        filtered_count, self.min_idf_threshold)

        # Bước 5: Build Vocabulary chính thức
        self.idf = {t: v for t, v in raw_idf.items() if t in kept_tokens}
        self.vocab = {
            token: idx
            for idx, token in enumerate(sorted(kept_tokens))
        }

        self._fitted = True
        logger.info("BM25 Fit Hoàn tất | Kích thước Vocab: %d", len(self.vocab))

        # Bước 6: Lưu ra file để lần sau API gọi không cần fit lại
        if self.vocab_path:
            self.save(self.vocab_path)

    # ------------------------------------------------------------------
    # 3. Mã hóa (Encode) - Xuất Sparse Vector cho Qdrant
    # ------------------------------------------------------------------
    def encode(self, text: str, is_query: bool = False) -> SparseVector:
        """
        Chuyển văn bản thành Sparse Vector.
        - is_query=False: Dùng lúc nạp dữ liệu (Ingest) -> Áp dụng chuẩn BM25 TF-IDF.
        - is_query=True: Dùng lúc người dùng hỏi -> Chỉ lấy IDF để tăng tốc và ưu tiên từ khóa hiếm.
        """
        if not self._fitted:
            raise RuntimeError("TravelBM25Encoder chưa được fit. Hãy gọi fit() hoặc load() trước.")

        tokens = self._tokenize(text)
        if not tokens:
            return SparseVector(indices=[], values=[])

        # Tính Term Frequency (TF)
        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        indices = []
        values = []

        for token, count in tf.items():
            if token not in self.vocab:
                continue  # Bỏ qua từ vựng nằm ngoài từ điển (Out-of-vocabulary)

            idx = self.vocab[token]
            idf_weight = self.idf.get(token, 0.0)

            if is_query:
                # Nếu là câu hỏi của khách, chỉ dùng IDF (Từ nào độc lạ sẽ được điểm cao)
                weight = idf_weight
            else:
                # Nếu là tài liệu nạp vào DB, tính theo công thức BM25 đầy đủ
                tf_norm = (
                    (count * (_K1 + 1))
                    / (count + _K1 * (1 - _B + _B * len(tokens) / self.avg_len))
                )
                weight = tf_norm * idf_weight

            if weight > 0:
                indices.append(idx)
                values.append(float(weight))

        return SparseVector(indices=indices, values=values)

    def encode_documents(self, texts: list[str]) -> list[SparseVector]:
        """Tiện ích encode cùng lúc nhiều documents."""
        return [self.encode(text, is_query=False) for text in texts]

    def encode_query(self, query: str) -> SparseVector:
        """Tiện ích encode câu hỏi của người dùng."""
        return self.encode(query, is_query=True)

    # ------------------------------------------------------------------
    # 4. Quản lý trạng thái (Save / Load)
    # ------------------------------------------------------------------
    def save(self, path: str):
        """Lưu toàn bộ mô hình ra file JSON."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "vocab": self.vocab,
            "idf": self.idf,
            "avg_len": self.avg_len,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Đã lưu BM25 Vocab tại: %s", path)

    def load(self, path: str):
        """Tải mô hình từ file JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vocab = data["vocab"]
        self.idf = data["idf"]
        self.avg_len = data.get("avg_len", 50.0)
        self._fitted = True
        logger.info("Đã tải BM25 Vocab | Vocab size: %d", len(self.vocab))