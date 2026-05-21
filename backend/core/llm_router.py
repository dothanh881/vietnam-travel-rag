import os
import json
from openai import AsyncOpenAI
from core.logger import get_logger

logger = get_logger(__name__)

ROUTER_SYSTEM_PROMPT = """Bạn là bộ định tuyến thông minh cho ứng dụng du lịch Việt Nam ViVu.
Phân tích câu hỏi và trả về JSON định tuyến CHÍNH XÁC.

TOOLS CÓ SẴN:
- get_weather: Thời tiết, dự báo, nhiệt độ
- plan_itinerary: Lập lịch trình, kế hoạch theo ngày
- estimate_budget: Ước tính ngân sách, chi phí
- search_flights: Tìm chuyến bay, vé máy bay
- search_knowledge_base: Địa điểm, ăn gì, chơi đâu, khách sạn, ẩm thực

OUTPUT FORMAT — chỉ trả về JSON thuần:
Câu hỏi đơn (1 mục tiêu):
{"tool": "tên_tool", "kwargs": {...}}

Câu hỏi kết hợp (nhiều mục tiêu song song):
{"tools": ["tool1", "tool2"], "kwargs": {...}}

THAM SỐ KWARGS:
- location: tên địa danh (null nếu không có)
- date: "today"|"tomorrow"|"YYYY-MM-DD" (null nếu không có)
- num_days: số ngày (null nếu không có)
- travel_style: "budget"|"mid"|"luxury" (null nếu không có)
- num_people: số người (null nếu không có)
- query_arg: câu hỏi tối ưu cho RAG search
- from_city: thành phố xuất phát (null nếu không có)
- to_city: thành phố đến (null nếu không có)
- activity: hoạt động dự kiến (null nếu không có)

VÍ DỤ:
- "Thời tiết Hà Nội ngày mai?" → {"tool":"get_weather","kwargs":{"location":"Hà Nội","date":"tomorrow"}}
- "Lập lịch 3 ngày Đà Lạt" → {"tool":"plan_itinerary","kwargs":{"location":"Đà Lạt","num_days":3}}
- "Có gì ăn ở Hội An?" → {"tool":"search_knowledge_base","kwargs":{"query_arg":"ẩm thực đặc sản Hội An"}}
- "Đi Phú Quốc 4 ngày tốn bao nhiêu, có gì vui?" → {"tools":["estimate_budget","search_knowledge_base"],"kwargs":{"location":"Phú Quốc","num_days":4,"query_arg":"địa điểm vui chơi Phú Quốc"}}
- "Lịch 3 ngày Đà Lạt và ngân sách" → {"tools":["plan_itinerary","estimate_budget"],"kwargs":{"location":"Đà Lạt","num_days":3}}
- "Thời tiết Sa Pa, phù hợp trekking không, có chỗ nào đẹp?" → {"tools":["get_weather","search_knowledge_base"],"kwargs":{"location":"Sa Pa","activity":"trekking","query_arg":"địa điểm trekking Sa Pa"}}
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
        kwargs_for_call = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            "temperature": 0.0,
            "max_tokens": 256,
        }
        
        # Cloudflare Workers AI hiện tại bị lỗi với {"type": "json_object"}
        if provider["name"].startswith("OpenAI"):
            kwargs_for_call["response_format"] = {"type": "json_object"}

        response = await provider["client"].chat.completions.create(**kwargs_for_call)
        raw = response.choices[0].message.content.strip()
        
        # Lọc bỏ markdown code block nếu có
        import re
        match = re.search(r'```(?:json)?\s*({.*?})\s*```', raw, re.DOTALL)
        if match:
            raw = match.group(1)
        else:
            # Fallback cắt thủ công từ { đến }
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                raw = raw[start:end+1]

        parsed = json.loads(raw)
        kwargs = {k: v for k, v in parsed.get("kwargs", {}).items() if v is not None}

        # Hỗ trợ cả "tool" (đơn) và "tools" (array)
        if "tools" in parsed and isinstance(parsed["tools"], list):
            return {"tools": parsed["tools"], "kwargs": kwargs}
        tool = parsed.get("tool", "search_knowledge_base")
        return {"tools": [tool], "kwargs": kwargs}

    async def route(self, question: str) -> dict:
        """
        Thử lần lượt: Cloudflare → GPT-4o-mini → raise.
        Luôn trả về {"tools": [...], "kwargs": {...}}
        """
        for provider in self.cf_clients + self.fallback_clients:
            try:
                result = await self._call(provider, question)
                logger.info(f"[LLMRouter] [{provider['name']}] → tools={result['tools']}")
                return result
            except Exception as e:
                logger.warning(f"[LLMRouter] [{provider['name']}] lỗi ({type(e).__name__}: {e}), thử tiếp...")
                continue

        logger.error("[LLMRouter] Tất cả providers thất bại")
        raise RuntimeError("All LLM router providers failed")
