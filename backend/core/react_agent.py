import os
import json
from openai import AsyncOpenAI
from core.logger import get_logger
from core.tools_def import get_tools_prompt_section
from core.llm_router import CF_MODELS, FALLBACK_PROVIDERS

logger = get_logger(__name__)

REACT_SYSTEM_PROMPT = """Bạn là một AI Travel Agent (ReAct Agent) của ViVu.
Mục tiêu của bạn là giải quyết yêu cầu của người dùng bằng cách Suy luận (Thought) và Hành động (Action) từng bước một.

{tools_section}
Ngoài ra, bạn có 2 công cụ ĐẶC BIỆT sau:
- ask_user: Hỏi lại người dùng nếu thiếu thông tin quan trọng. (params: {{"question": "câu hỏi của bạn"}})
- finish: Trả về kết quả cuối cùng cho người dùng khi đã tổng hợp đủ thông tin. (params: {{"answer": "câu trả lời tự nhiên của bạn"}})

LUẬT CƠ BẢN:
1. LUÔN LUÔN hoạt động theo cấu trúc JSON. Không trả về markdown thừa.
2. Nếu người dùng yêu cầu "Tính chi phí", "Lập lịch trình" nhưng THIẾU các thông tin bắt buộc như: "from_city" (Điểm xuất phát), "to_city" (Điểm đến), "num_days" (Số ngày đi), bạn KHÔNG ĐƯỢC TỰ BỊA RA. Phải ngay lập tức gọi tool `ask_user`.
3. Nếu bạn đã có đủ thông tin (hoặc đã gọi tool đủ để giải quyết), hãy dùng action `finish`.

OUTPUT FORMAT (Bạn phải trả về đúng chuẩn JSON này):
{{
  "thought": "Suy luận hiện tại của bạn",
  "action": "tên_công_cụ",
  "action_input": {{
    "tham_so_1": "gia_tri",
    "tham_so_2": "gia_tri"
  }}
}}
"""

class ReActAgent:
    def __init__(self):
        self.cf_clients = []
        self.fallback_clients = []

        # Tái sử dụng cấu hình provider từ LLMRouter
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        if cf_token and cf_account:
            cf_base_url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/v1"
            cf_client = AsyncOpenAI(
                api_key=cf_token,
                base_url=cf_base_url,
                timeout=10.0,
            )
            for model in CF_MODELS:
                self.cf_clients.append({"name": f"CF/{model.split('/')[-1]}", "model": model, "client": cf_client})

        for p in FALLBACK_PROVIDERS:
            api_key = os.getenv(p["api_key_env"])
            if api_key:
                client = AsyncOpenAI(api_key=api_key, base_url=p["base_url"], timeout=15.0)
                self.fallback_clients.append({"name": p["name"], "model": p["model"], "client": client})

    async def _call_llm(self, messages: list) -> dict:
        providers = self.cf_clients + self.fallback_clients
        if not providers:
            raise RuntimeError("Không có LLM Provider nào được cấu hình cho ReAct Agent.")

        for provider in providers:
            try:
                kwargs = {
                    "model": provider["model"],
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 512,
                }
                if provider["name"].startswith("OpenAI"):
                    kwargs["response_format"] = {"type": "json_object"}
                
                response = await provider["client"].chat.completions.create(**kwargs)
                raw = response.choices[0].message.content.strip()
                
                # Cleanup raw JSON if needed
                import re
                match = re.search(r'```(?:json)?\s*({.*?})\s*```', raw, re.DOTALL)
                if match:
                    raw = match.group(1)
                else:
                    start = raw.find('{')
                    end = raw.rfind('}')
                    if start != -1 and end != -1:
                        raw = raw[start:end+1]

                return json.loads(raw)
            except Exception as e:
                logger.warning(f"[ReActAgent] Provider {provider['name']} lỗi: {e}")
                continue
        raise RuntimeError("ReActAgent: Tất cả provider đều thất bại.")

    async def run(self, user_query: str, chat_history: list = None, max_steps: int = 5):
        """
        Vòng lặp ReAct thực thi từ câu hỏi người dùng.
        Hàm này sẽ trả về step cuối cùng là "ask_user" hoặc "finish".
        (Thực tế ở đây chỉ return loop output, pipeline.py sẽ gọi execute tool sau).
        """
        if chat_history is None:
            chat_history = []
            
        system_content = REACT_SYSTEM_PROMPT.format(tools_section=get_tools_prompt_section())
        messages = [{"role": "system", "content": system_content}]
        
        # Append chat history (to help agent know the missing parameters like "4 days")
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        messages.append({"role": "user", "content": user_query})
        
        steps = []
        # Simulate local ReAct single step logic here for routing
        # (Để đơn giản, router sẽ gọi agent.run để lấy next action, hoặc pipeline tự quản lý vòng lặp)
        
        next_action_json = await self._call_llm(messages)
        return next_action_json
