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

OUTPUT FORMAT (chỉ trả về JSON thuần, không markdown, không giải thích):
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
# CLOUDFLARE WORKERS AI — Model miễn phí
# Docs: https://developers.cloudflare.com/workers-ai/models/
# Endpoint OpenAI-compatible:
#   https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1
# =============================================
CF_MODELS = [
    "@cf/meta/llama-3.1-8b-instruct",    # Nhanh, instruction following tốt
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",  # Mạnh hơn, vẫn free
]

# Fallback cuối cùng nếu Cloudflare lỗi
FALLBACK_PROVIDERS = [
    {
        "name": "GPT-4o-mini",
        "model": "gpt-4o-mini",
        "base_url": None,
        "api_key_env": "OPENAI_API_KEY",
    },
]


class LLMRouter:
    """
    Router thông minh dùng Cloudflare Workers AI (miễn phí, 1 key).
    Fallback về GPT-4o-mini nếu Cloudflare lỗi.
    Fallback cuối về rule-based nếu tất cả thất bại.

    Cần env vars:
        CLOUDFLARE_API_TOKEN  — API token từ dash.cloudflare.com
        CLOUDFLARE_ACCOUNT_ID — Account ID từ dash.cloudflare.com
        OPENAI_API_KEY        — Backup, chỉ dùng khi CF lỗi
    """

    def __init__(self):
        self.cf_clients = []
        self.fallback_clients = []

        # Khởi tạo Cloudflare client (1 key, nhiều model)
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        if cf_token and cf_account:
            cf_base_url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/v1"
            cf_client = AsyncOpenAI(
                api_key=cf_token,
                base_url=cf_base_url,
                timeout=6.0,
            )
            for model in CF_MODELS:
                self.cf_clients.append({"name": f"CF/{model.split('/')[-1]}", "model": model, "client": cf_client})
            logger.info(f"[LLMRouter] Cloudflare AI: {len(CF_MODELS)} models sẵn sàng")
        else:
            logger.warning("[LLMRouter] Thiếu CLOUDFLARE_API_TOKEN hoặc CLOUDFLARE_ACCOUNT_ID")

        # Khởi tạo fallback providers
        for p in FALLBACK_PROVIDERS:
            api_key = os.getenv(p["api_key_env"])
            if api_key:
                client = AsyncOpenAI(api_key=api_key, base_url=p["base_url"], timeout=5.0)
                self.fallback_clients.append({"name": p["name"], "model": p["model"], "client": client})
                logger.info(f"[LLMRouter] Fallback: {p['name']}")

        all_providers = self.cf_clients + self.fallback_clients
        if not all_providers:
            logger.warning("[LLMRouter] Không có provider nào! Sẽ dùng rule-based.")

    async def _call(self, provider: dict, question: str) -> dict:
        """Gọi 1 provider, raise exception nếu thất bại."""
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
        Thử lần lượt:
          1. Cloudflare llama-3.1-8b (free, nhanh)
          2. Cloudflare llama-3.3-70b (free, mạnh hơn)
          3. GPT-4o-mini (paid backup)
          4. Raise → pipeline fallback về rule-based
        """
        for provider in self.cf_clients + self.fallback_clients:
            try:
                result = await self._call(provider, question)
                logger.info(f"[LLMRouter] [{provider['name']}] → tool={result['tool']}")
                return result
            except Exception as e:
                logger.warning(f"[LLMRouter] [{provider['name']}] lỗi ({type(e).__name__}: {e}), thử tiếp...")
                continue

        logger.error("[LLMRouter] Tất cả providers thất bại")
        raise RuntimeError("All LLM router providers failed")
