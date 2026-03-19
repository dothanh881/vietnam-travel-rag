import re
from typing import Dict, Optional


class TravelQueryAnalyzer:
    """
    Phân tích query cho travel domain
    Sử dụng Regex biên dịch sẵn (Pre-compiled) để tăng tốc độ

    """

    def __init__(self):
        # 1. Cấu hình Keyword cho Intent
        # Dùng \b để bắt ranh giới từ độc lập, tránh lỗi "chăn" nhận thành "ăn"
        self.intent_rules = {
            "food": [r"\băn\b", "món", "đặc sản", "nhà hàng", "quán", "ẩm thực"],
            "place": ["đi đâu", "chơi", "tham quan", "địa điểm", "cảnh đẹp", "check in", "check-in"],
            "itinerary": ["lịch trình", "plan", "itinerary", "kế hoạch", "gợi ý chuyến đi"]
        }

        # 2. Cấu hình Keyword cho Destination (Dễ dàng thêm 63 tỉnh thành)
        self.destination_rules = {
            "Đà Lạt": ["đà lạt", "dalat"],
            "Phú Quốc": ["phú quốc", "phu quoc"],
            "Sa Pa": ["sapa", "sa pa"],
            "An Giang": ["an giang", "châu đốc", "thất sơn"],
            "Đà Nẵng": ["đà nẵng", "da nang"],
            "Hà Nội": ["hà nội", "hanoi"],
            "Hồ Chí Minh": ["sài gòn", "hồ chí minh", "hcm", "tphcm"]
        }

        # 3. Biên dịch Regex ngay khi khởi tạo (Chỉ chạy 1 lần lúc bật server)
        self.compiled_intents = self._compile_rules(self.intent_rules)
        self.compiled_destinations = self._compile_rules(self.destination_rules)

    def _compile_rules(self, rules: Dict[str, list]) -> Dict[str, re.Pattern]:
        """Gom nhóm các từ khóa thành 1 bộ lọc Regex siêu tốc"""
        compiled = {}
        for key, keywords in rules.items():
            # Tạo chuỗi regex dạng: (?i)(ăn|món|đặc sản)
            # (?i) để không phân biệt hoa thường
            pattern = f"({'|'.join(keywords)})"
            compiled[key] = re.compile(pattern, re.IGNORECASE)
        return compiled

    def analyze(self, query: str) -> Dict[str, Optional[str]]:
        """Nhận diện Intent và Destination từ câu hỏi"""

        # -------- detect intent --------
        intent = "general"
        for key, pattern in self.compiled_intents.items():
            if pattern.search(query):
                intent = key
                break  # Ưu tiên intent đầu tiên tìm thấy

        # -------- detect destination --------
        destination = None
        for key, pattern in self.compiled_destinations.items():
            if pattern.search(query):
                destination = key
                break

        return {
            "intent": intent,
            "destination": destination
        }