import json
import re
from typing import Dict, Optional
from core.logger import get_logger

logger = get_logger(__name__)

class TravelQueryAnalyzer:
    """
    Analyzer chuyên biệt cho Domain Du lịch.
    Nhiệm vụ: 
    1. Phân loại Ý định (Intent).
    2. Chuẩn hóa địa danh/tỉnh thành (Destination).
    3. Làm giàu từ khóa tìm kiếm (Expanded Query).
    """

    def __init__(self, llm_generator):
        """
        Args:
            llm_generator: Instance của class LLMGenerator (chạy mode Ollama).
        """
        self.llm = llm_generator

    def _generate_slug(self, text: str) -> Optional[str]:
        """Chuyển đổi Tiếng Việt có dấu thành slug không dấu chuẩn."""
        if not text:
            return None
        
        # Bảng mã chuyển đổi
        s1 = u'ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỴỵỶỷỸỹ'
        s0 = u'AAAAEEEIIOOOOUUYaaaaeeeiiiiiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYy'
        s = ""
        for char in text:
            if char in s1:
                s += s0[s1.index(char)]
            else:
                s += char
        
        # Lowercase, loại bỏ ký tự đặc biệt, thay khoảng trắng bằng gạch ngang
        s = s.lower().strip()
        s = re.sub(r'[^a-z0-9\s-]', '', s)
        s = re.sub(r'\s+', '-', s)
        return s

    def analyze(self, query: str) -> Dict[str, Optional[str]]:
        """
        Nhận vào câu hỏi thô và trả về cấu trúc phân tích JSON.
        """
        if not self.llm:
            logger.warning("[QueryAnalyzer] Chưa có LLMGenerator. Trả về giá trị mặc định.")
            return self._fallback(query)

        # Prompt được thiết kế để ép Qwen 3B hoạt động như một cỗ máy logic
        system_prompt = """Bạn là chuyên gia phân tích truy vấn du lịch.
Nhiệm vụ: Trích xuất địa danh và làm giàu từ khóa từ câu hỏi của khách.

QUY TẮC:
1. Destination: Trích xuất Tên Tỉnh/Thành/Địa danh (Yêu cầu có dấu, VD: "An Giang", "Phú Quốc"). Nếu không có thì để null.
2. Expanded_query: Bổ sung từ khóa mở rộng NHƯNG PHẢI ĐÚNG VỚI Ý ĐỊNH của khách. 
   - TUYỆT ĐỐI KHÔNG thêm từ khóa "món ăn", "ẩm thực" nếu khách chỉ hỏi về chỗ đi chơi, tham quan.
   - Nếu khách hỏi "chơi gì / tham quan": Mở rộng thành "địa điểm du lịch, vui chơi, giải trí, check-in, phong cảnh".
   - Nếu khách hỏi "ăn gì": Mở rộng thành "ẩm thực, đặc sản, nhà hàng, quán ăn ngon".
   - Nếu khách hỏi "ở đâu / vị trí": Mở rộng thành "địa chỉ, nằm ở tỉnh nào, thuộc vùng nào".
TRẢ VỀ JSON DUY NHẤT:
{
  "destination": "Tên địa danh có dấu",
  "expanded_query": "Câu đã làm giàu"
}"""

        try:
            # Gọi LLM với temperature = 0.0 để kết quả thực thể luôn ổn định
            raw_response = self.llm.generate(
                prompt=system_prompt,
                user_input=f"Câu hỏi của khách: '{query}'",
                temperature=0.0
            )

            # Làm sạch dữ liệu JSON (đề phòng model sinh dư thừa markdown)
            result = self._parse_json_robustly(raw_response)
            

            if not result:
                return self._fallback(query)

            logger.info(f" [Analyzer] Gốc: {query} \n -> Dest: {result.get('destination')} \n -> Expanded Query: {result.get('expanded_query')}")
            return result

        except Exception as e:
            logger.error(f" [Analyzer] Lỗi nghiêm trọng: {e}")
            return self._fallback(query)

    def _parse_json_robustly(self, raw_text: str) -> Optional[Dict]:
        """Trích xuất JSON từ chuỗi văn bản một cách an toàn."""
        try:
            # Gọt sạch markdown code blocks
            clean_text = re.sub(r"```json|```", "", raw_text).strip()
            
            # Tìm cặp dấu ngoặc nhọn đầu và cuối
            start = clean_text.find('{')
            end = clean_text.rfind('}') + 1
            if start != -1 and end != 0:
                clean_text = clean_text[start:end]
                
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"[Analyzer] Không thể parse JSON: {e}")
            return None

    def _fallback(self, query: str) -> Dict:
        """Kết quả dự phòng khi hệ thống lỗi."""
        return {
            "destination": None,
            "expanded_query": query
        }