import json
import logging
import os
from typing import Dict, Optional
from flashtext import KeywordProcessor

logger = logging.getLogger(__name__)

class TravelQueryAnalyzer:
    """
    Analyzer Zero-LLM siêu tốc cho hệ thống RAG.
    Sử dụng FlashText (Aho-Corasick) thay vì LLM để giảm độ trễ từ 1000ms xuống < 5ms.
    """

    def __init__(self, mapping_path: str = None, **kwargs):
        if mapping_path is None:
            # Default to backend/config/location_mapping.json
            mapping_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'location_mapping.json')

        # 1. Khởi tạo công cụ trích xuất địa danh siêu tốc
        self.keyword_processor = KeywordProcessor(case_sensitive=False)
        try:
            with open(mapping_path, 'r', encoding='utf-8') as f:
                location_mapping = json.load(f)
                self.keyword_processor.add_keywords_from_dict(location_mapping)
        except Exception as e:
            logger.error(f"[Analyzer] Lỗi load từ điển địa điểm: {e}")

        # 2. Mở rộng Intent bằng Rule-based (Nhanh gấp vạn lần LLM)
        # Giữ lại để hỗ trợ thêm cho nhánh Sparse Vector (BM25) nếu bạn có dùng
        self.intent_expansion = {
            "ăn": "ẩm thực món ngon nhà hàng quán đặc sản",
            "món": "ẩm thực món ngon đặc sản",
            "chơi": "vui chơi giải trí tham quan check-in",
            "ngủ": "khách sạn homestay resort chỗ nghỉ lưu trú",
            "nghỉ": "khách sạn homestay resort chỗ nghỉ lưu trú",
            "giá": "chi phí tiền mức giá",
            "vé": "giá vé vé vào cổng vé tham quan",
            "chi phí": "ngân sách bảng giá",
            "đẹp": "view phong cảnh chụp hình",
            "mua": "đặc sản lưu niệm mua sắm chợ",
            "quà": "đặc sản lưu niệm quà tặng mua sắm"
        }

    def analyze(self, query: str) -> Dict[str, Optional[str]]:
        """
        Phân tích truy vấn chỉ trong < 5ms.
        """
        query_lower = query.lower()
        
        # 1. TRÍCH XUẤT ĐỊA DANH BẰNG FLASHTEXT (Chính xác & Siêu tốc)
        found_locations = self.keyword_processor.extract_keywords(query)
        # Nếu có nhiều địa danh (VD: "Từ Hà Nội đi Sapa"), lấy điểm đến cuối cùng
        detected_dest = found_locations[-1] if found_locations else None

        # 2. LÀM GIÀU TỪ KHÓA BẰNG RULE-BASED
        expanded_parts = [query]
        if detected_dest:
             expanded_parts.append(detected_dest) # Nhấn mạnh địa danh

        import re
        for key, expansion in self.intent_expansion.items():
            if re.search(rf'\b{key}\b', query_lower, re.UNICODE):
                expanded_parts.append(expansion)
        
        expanded_query = " ".join(expanded_parts)

        # 3. PHÂN TÁCH SUBCONTEXT (Compound Query)
        # Tách các câu hỏi ghép siêu nhẹ (Tốc độ ~0.1ms) không cần LLM
        sub_queries = []
        split_pattern = r'(?i)\b(và|cũng như|kết hợp|rồi|mà còn)\b|[,;]'
        raw_subs = [sq.strip() for sq in re.split(split_pattern, query) 
                    if sq and sq.strip().lower() not in ['và', 'cũng như', 'kết hợp', 'rồi', 'mà còn', ',', ';']]
        
        if len(raw_subs) > 1:
            for sq in raw_subs:
                # Bỏ qua chuỗi quá ngắn
                if len(sq.split()) <= 1:
                    continue
                sq_expanded = [sq]
                if detected_dest and detected_dest.lower() not in sq.lower():
                    sq_expanded.append(detected_dest)
                
                # Áp dụng rule-based intent
                for key, expansion in self.intent_expansion.items():
                    if re.search(rf'\b{key}\b', sq.lower(), re.UNICODE):
                        sq_expanded.append(expansion)
                        
                sub_queries.append(" ".join(sq_expanded))

        logger.info(f"[Analyzer] Query: '{query}' -> Dest: {detected_dest} | Expanded: {expanded_query} | SubQueries: {len(sub_queries)}")

        return {
            "destination": detected_dest,
            "expanded_query": expanded_query,
            "sub_queries": sub_queries
        }
