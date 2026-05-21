import os
import json
from openai import AsyncOpenAI
from core.logger import get_logger

logger = get_logger(__name__)

ROUTER_SYSTEM_PROMPT = """Bạn là bộ định tuyến thông minh cho ứng dụng du lịch Việt Nam ViVu.
Phân tích câu hỏi và trả về JSON định tuyến CHÍNH XÁC theo schema sau.

TOOLS CÓ SẴN:
- get_weather: Hỏi thời tiết, dự báo, có mưa không, nhiệt độ
- plan_itinerary: Lập lịch trình, kế hoạch chuyến đi theo ngày
- estimate_budget: Ước tính ngân sách, chi phí chuyến đi
- search_flights: Tìm chuyến bay, vé máy bay
- search_knowledge_base: Hỏi địa điểm, ăn gì, chơi đâu, khách sạn, ẩm thực
- combined_weather_rag: Hỏi thời tiết KÈM gợi ý địa điểm/hoạt động
- plan_full_trip: Lập TOÀN BỘ chuyến đi (lịch + ngân sách + thời tiết cùng lúc)

OUTPUT FORMAT (chỉ trả về JSON, không giải thích):
{
  "tool": "tên_tool",
  "kwargs": {
    "location": "tên địa danh hoặc null",
    "date": "today|tomorrow|YYYY-MM-DD hoặc null",
    "num_days": số ngày hoặc null,
    "travel_style": "budget|mid|luxury hoặc null",
    "num_people": số người hoặc null,
    "query_arg": "câu hỏi tìm kiếm tối ưu cho RAG",
    "from_city": "thành phố xuất phát hoặc null",
    "to_city": "thành phố đến hoặc null",
    "activity": "hoạt động dự kiến hoặc null"
  }
}

VÍ DỤ:
- "Thời tiết Hà Nội ngày mai?" → tool: get_weather, location: Hà Nội, date: tomorrow
- "Lập lịch 3 ngày Đà Lạt" → tool: plan_itinerary, location: Đà Lạt, num_days: 3
- "Đi Phú Quốc 4 ngày tốn bao nhiêu?" → tool: estimate_budget, location: Phú Quốc, num_days: 4
- "Có gì ăn ở Hội An?" → tool: search_knowledge_base, query_arg: ẩm thực đặc sản Hội An
- "Thời tiết Sa Pa, phù hợp trekking không?" → tool: combined_weather_rag, location: Sa Pa
- "Lập lịch + ngân sách 5 ngày Hạ Long cho 2 người" → tool: plan_full_trip
"""

# =============================================
# CẤU HÌNH FALLBACK CHAIN: Gemini → Groq → GPT
# =============================================
PROVIDERS = [
    {
        "name": "Gemini",
        "model": "gemini-2.0-flash-lite",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
    },
    {
        "name": "Groq",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
    },
    {
        "name": "GPT-4o-mini",
        "model": "gpt-4o-mini",
        "base_url": None,  # OpenAI default
        "api_key_env": "OPENAI_API_KEY",
    },
]


class LLMRouter:
    """
    Router thông minh với fallback chain: Gemini Flash → Groq → GPT-4o-mini.
    Tự động chuyển sang provider tiếp theo nếu bị rate-limit hoặc lỗi.
    """

    def __init__(self):
        self.providers = []
        for p in PROVIDERS:
            api_key = os.getenv(p["api_key_env"])
            if api_key:
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=p["base_url"],
                    timeout=5.0,
                )
                self.providers.append({
                    "name": p["name"],
                    "model": p["model"],
                    "client": client,
                })
                logger.info(f"[LLMRouter] Đã cấu hình provider: {p['name']} ({p['model']})")

        if not self.providers:
            logger.warning("[LLMRouter] Không có API key nào! Sẽ dùng rule-based fallback.")

    async def _call_provider(self, provider: dict, question: str) -> dict:
        """Gọi một provider cụ thể, raise nếu thất bại."""
        response = await provider["client"].chat.completions.create(
            model=provider["model"],
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        tool = parsed.get("tool", "search_knowledge_base")
        kwargs = {k: v for k, v in parsed.get("kwargs", {}).items() if v is not None}
        return {"tool": tool, "kwargs": kwargs}

    async def route(self, question: str) -> dict:
        """
        Thử lần lượt từng provider theo thứ tự: Gemini → Groq → GPT-4o-mini.
        Fallback về RAG nếu tất cả đều thất bại.
        """
        for provider in self.providers:
            try:
                result = await self._call_provider(provider, question)
                logger.info(f"[LLMRouter] [{provider['name']}] → tool={result['tool']} | {list(result['kwargs'].keys())}")
                return result
            except Exception as e:
                logger.warning(f"[LLMRouter] [{provider['name']}] thất bại ({type(e).__name__}), thử provider tiếp theo...")
                continue

        # Tất cả provider đều thất bại
        logger.error("[LLMRouter] Tất cả providers thất bại, fallback về RAG")
        return {
            "tool": "search_knowledge_base",
            "kwargs": {"query_arg": question}
        }
