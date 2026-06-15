import os
import re
from openai import OpenAI, AsyncOpenAI
from core.logger import get_logger
from langfuse import observe
from jinja2 import Environment, FileSystemLoader

logger = get_logger(__name__)

class LLMGenerator:
    """
    Trình sinh văn bản tinh gọn, chạy độc quyền qua Ollama Local API hoặc vLLM.
    ĐÃ NÂNG CẤP HYBRID ARCHITECTURE (BRAIN - VOICE).
    """

    def __init__(
        self, 
        mode: str = "ollama", 
        vllm_model: str = "qwen-vivu", 
        vllm_base_url: str = None, 
        vllm_api_key: str = "sk-no-key",
        ollama_model: str = "hf.co/thanhdo881/qwen3-1.7b-vivu-travel-vn-GGUF:Q4_K_M",
        temperature: float = 0.1
    ):
        self.mode = mode
        self.temperature = temperature
        
        # ==========================================
        # 1. BRAIN CLIENT (CHUYÊN DÙNG CHO ROUTER)
        # ==========================================
        # Sử dụng Qwen2.5-1.5B-Instruct chạy Local trên Ollama làm Não (Router).
        # Bản Instruct gốc giữ được khả năng tuân thủ JSON xuất sắc.
        self.brain_model = "hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M"
        
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        
        self.async_brain_client = AsyncOpenAI(
            base_url=ollama_base_url, 
            api_key="ollama" # Gọi thẳng xuống Ollama Local/Cloud
        )
        
        # ==========================================
        # 2. VOICE CLIENT (CHUYÊN DÙNG ĐỂ NÓI CHUYỆN)
        # ==========================================
        self.vllm_model = vllm_model
        self.vllm_client = OpenAI(base_url=vllm_base_url, api_key=vllm_api_key)
        self.async_vllm_client = AsyncOpenAI(base_url=vllm_base_url, api_key=vllm_api_key)
        
        self.ollama_model = ollama_model
        self.ollama_client = OpenAI(base_url=ollama_base_url, api_key="ollama")
        self.async_ollama_client = AsyncOpenAI(base_url=ollama_base_url, api_key="ollama")

        # Khởi tạo Jinja2 Environment cho Prompts
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompts_dir = os.path.join(base_dir, "prompts")
        self.jinja_env = Environment(loader=FileSystemLoader(prompts_dir))
        
        logger.info(f"[LLMGenerator] Đã khởi tạo Hybrid Architecture (Mode: {self.mode})")

    def _get_voice_config(self):
        """Lấy Voice Client dựa trên chế độ hiện tại."""
        if self.mode == "ollama":
            return self.ollama_model, self.ollama_client, self.async_ollama_client
        else: # "vllm"
            return self.vllm_model, self.vllm_client, self.async_vllm_client

    def _render_prompt(self, template_name: str, **kwargs) -> str:
        """Đọc và render prompt từ Jinja2 template."""
        template = self.jinja_env.get_template(template_name)
        return template.render(**kwargs).strip()

    def generate(self, prompt: str, user_input: str, temperature: float = None) -> str:
        """Hàm gọi API OpenAI/vLLM nguyên thủy (Voice)."""
        temp = temperature if temperature is not None else self.temperature
        active_model, active_client, _ = self._get_voice_config()
        
        messages = []
        if prompt:
            messages.append({"role": "system", "content": prompt})
        messages.append({"role": "user", "content": user_input})
        
        # Đã thêm Phạt lặp (Repetition Penalty) siêu mạnh để trị bệnh lặp từ
        kwargs = {
            "model": active_model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": 2048,
            "stop": ["<|im_end|>", "<|endoftext|>"],
            "frequency_penalty": 0.5,
            "presence_penalty": 0.5
        }
        
        if self.mode == "ollama":
            kwargs["extra_body"] = {
                "keep_alive": "30m",
                "options": {
                    "num_predict": 512,
                    "num_ctx": 3072
                }
            }
        elif self.mode == "vllm":
            kwargs["extra_body"] = {"repetition_penalty": 1.05}
            
        response = active_client.chat.completions.create(**kwargs)
        
        ans = response.choices[0].message.content.strip()
        ans = re.sub(r'<think>.*?</think>\s*', '', ans, flags=re.DOTALL)
        ans = ans.replace('</think>', '').replace('<think>', '').strip()
        return ans

    @observe(as_type="generation", name="3_vLLM_Generate")
    def generate_answer(self, question: str, chunks: list[dict]) -> str:
        filtered_chunks = chunks
        if not filtered_chunks:
            logger.warning(f" [LLM] Không tìm thấy ngữ cảnh cho câu hỏi: {question}. Từ chối tĩnh.")
            return "🌴 Xin lỗi, ViVu hiện chưa có thông tin chi tiết về câu hỏi này."

        context = self._build_context(filtered_chunks)
        rendered_prompt = self._render_prompt("generation/rag_answer.jinja", context=context, question=question)
        ans = self.generate(prompt="", user_input=rendered_prompt)
        ans = self._fix_formatting(ans)
        if not ans.startswith('🌴'):
            ans = '🌴 ' + ans
        return ans

    async def generate_stream(self, prompt: str, user_input: str, temperature: float = None):
        """Stream từng token qua OpenAI-compatible API (Voice model)."""
        temp = temperature if temperature is not None else self.temperature
        active_model, _, active_async_client = self._get_voice_config()

        messages = []
        if prompt:
            messages.append({"role": "system", "content": prompt})
        messages.append({"role": "user", "content": user_input})

        kwargs = {
            "model": active_model,
            "messages": messages,
            "stream": True,
            "temperature": temp,
            "max_tokens": 2048,
            "stop": ["<|im_end|>", "<|endoftext|>"],
            "frequency_penalty": 0.5,
            "presence_penalty": 0.5
        }

        if self.mode == "ollama":
            # Model SFT-only → tắt thinking_budget để tránh output lỗi. Đảm bảo num_predict cao để không bị ngắt chữ.
            kwargs["extra_body"] = {
                "keep_alive": "30m",
                "options": {
                    "num_predict": 512,
                    "num_ctx": 3072
                }
            }
        elif self.mode == "vllm":
            kwargs["extra_body"] = {"repetition_penalty": 1.05}

        print(f"[LLM] Mode={self.mode} | Model={active_model} | Đang gọi Voice API stream...")
        try:
            response_stream = await active_async_client.chat.completions.create(**kwargs)
        except Exception as e:
            print(f"[LLM ERROR] Không thể kết nối tới LLM: {type(e).__name__}: {e}")
            raise

        in_think_block = False
        async for chunk in response_stream:
            token = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta.content else ""
            if token:
                if "<think>" in token:
                    in_think_block = True
                    token = token.replace("<think>", "")
                if "</think>" in token:
                    in_think_block = False
                    token = token.replace("</think>", "")
                    continue
                if not in_think_block and token:
                    yield token

    @observe(as_type="generation", name="3_vLLM_Generate_Stream")
    async def generate_answer_stream(self, question: str, chunks: list[dict]):
        filtered_chunks = chunks
        if not filtered_chunks:
            logger.warning(f" [LLM Stream] Context trống cho: {question}. Chặn ảo giác trực tiếp.")
            yield "🌴 Xin lỗi, ViVu hiện chưa có thông tin chi tiết về câu hỏi này."
            return

        context = self._build_context(filtered_chunks)
        rendered_prompt = self._render_prompt("generation/rag_answer.jinja", context=context, question=question)

        print(f"[LLM] Bắt đầu generate_answer_stream | Mode={self.mode}")
        yield "🌴 "
        try:
            async for token in self.generate_stream(prompt="", user_input=rendered_prompt):
                yield token
        except Exception as e:
            print(f"[LLM ERROR] generate_stream thất bại: {type(e).__name__}: {e}")
            yield f"\n\n Lỗi kết nối LLM ({self.mode}): {e}"


    async def decide_tool_async(self, question: str) -> str:
        """Gọi BRAIN LLM để quyết định xem có gọi hàm không."""
        from core.tools_def import get_tools_prompt_section, get_tool_json_schema
        from datetime import datetime
        import pytz
        
        tools_section = get_tools_prompt_section()
        schema_section = get_tool_json_schema()
        
        # Lấy ngày giờ thực tế (Múi giờ Việt Nam)
        tz_vn = pytz.timezone("Asia/Ho_Chi_Minh")
        now = datetime.now(tz_vn)
        current_datetime = now.strftime("%A, ngày %d/%m/%Y lúc %H:%M (GMT+7)")
        tomorrow_date = (now + __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
        today_date = now.strftime("%Y-%m-%d")
        
        # Render prompt bằng Jinja2
        rendered_prompt = self._render_prompt(
            "agent/router.jinja", 
            tools_section=tools_section, 
            schema_section=schema_section,
            current_datetime=current_datetime,
            today_date=today_date,
            tomorrow_date=tomorrow_date
        )
        
        messages = [
            {"role": "system", "content": rendered_prompt},
            {"role": "user", "content": question}
        ]
        
        kwargs = {
            "model": self.brain_model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 128,
            "response_format": {"type": "json_object"},
            "extra_body": {
                "keep_alive": "30m",
                "options": {
                    "num_ctx": 4096,
                    "num_predict": 256
                }
            }
        }
        
        # === ROUTER CACHE (Giảm latency ~100% cho query lặp lại) ===
        # Normalize key: lowercase + bỏ dấu câu thừa
        cache_key = question.lower().strip()
        if hasattr(self, '_router_cache') and cache_key in self._router_cache:
            cached_result, cached_time = self._router_cache[cache_key]
            # Cache TTL = 3 phút (180s) - đủ để không stale với thời tiết realtime
            if (datetime.now(tz_vn) - cached_time).seconds < 180:
                print(f"[AGENT ROUTER] ⚡ Cache HIT cho: '{question[:40]}...'")
                return cached_result
        
        print(f"[AGENT ROUTER] Đang gọi BRAIN LLM (Local 1.5B) quyết định route cho câu hỏi: '{question}'...")
        try:
            response = await self.async_brain_client.chat.completions.create(**kwargs)
            ans = response.choices[0].message.content.strip()
            
            # Lưu vào cache
            if not hasattr(self, '_router_cache'):
                self._router_cache = {}
            self._router_cache[cache_key] = (ans, datetime.now(tz_vn))
            # Giới hạn cache tối đa 200 entries để không tốn RAM
            if len(self._router_cache) > 200:
                oldest = min(self._router_cache.items(), key=lambda x: x[1][1])
                del self._router_cache[oldest[0]]
            
            return ans
        except Exception as e:
            logger.error(f"[AGENT ROUTER] Lỗi kết nối tới BRAIN API: {e}")
            # Fallback thảm họa: Nếu Brain chết, bắt buộc không gọi Tool nữa
            return ""

    async def generate_direct_stream(self, text: str):
        # Do Router trả lời quá thô cứng, ta dùng lại Voice để nói cho mượt
        rendered_prompt = f"Người dùng có một câu hỏi/thông báo ngoài lề. Bạn hãy trả lời lại dựa trên dữ kiện sau một cách thân thiện: {text}"
        try:
            async for token in self.generate_stream(prompt="", user_input=rendered_prompt):
                yield token
        except Exception:
            # Fallback nếu Voice lỗi
            words = text.split(" ")
            for word in words:
                yield word + " "
                import asyncio
                await asyncio.sleep(0.01)

    async def generate_weather_stream(self, question: str, weather_info: str):
        rendered_prompt = self._render_prompt("generation/weather_answer.jinja", weather_info=weather_info, question=question)
        yield "⛅ "
        async for token in self.generate_stream(prompt="", user_input=rendered_prompt):
            yield token

    async def generate_budget_stream(self, question: str, budget_json: str, travel_style: str = "mid"):
        """Giải thích ngân sách ước tính theo cách thân thiện."""
        rendered_prompt = self._render_prompt(
            "generation/budget_answer.jinja",
            question=question,
            budget_json=budget_json,
            travel_style=travel_style
        )
        yield "💰 "
        async for token in self.generate_stream(prompt="", user_input=rendered_prompt):
            yield token

    async def generate_combined_stream(self, question: str, weather_info: str, chunks: list[dict]):
        """Tổng hợp cả thời tiết + địa điểm RAG trong một câu trả lời mạch lạc."""
        context = self._build_context(chunks) if chunks else ""
        rendered_prompt = self._render_prompt(
            "generation/combined_answer.jinja",
            weather_info=weather_info,
            context=context,
            question=question
        )
        yield "⛅🌴 "
        async for token in self.generate_stream(prompt="", user_input=rendered_prompt):
            yield token

    async def generate_itinerary_stream(self, question: str, chunks: list[dict],
                                         destination: str = "", num_days: int = 3,
                                         travel_style: str = "mid", num_people: int = 1):
        """Sinh lịch trình du lịch chi tiết từng ngày."""
        context = self._build_context(chunks) if chunks else ""
        rendered_prompt = self._render_prompt(
            "generation/itinerary_answer.jinja",
            question=question,
            context=context,
            destination=destination,
            num_days=num_days,
            travel_style=travel_style,
            num_people=num_people
        )
        yield "🗓️ "
        async for token in self.generate_stream(prompt="", user_input=rendered_prompt):
            yield token

    async def generate_full_trip_stream(self, question: str, chunks: list[dict],
                                         destination: str = "", num_days: int = 3,
                                         travel_style: str = "mid", num_people: int = 1,
                                         weather_info: str = ""):
        """Lập lịch trình đầy đủ kết hợp thời tiết + địa điểm + ngân sách."""
        context = self._build_context(chunks) if chunks else ""
        rendered_prompt = self._render_prompt(
            "generation/itinerary_answer.jinja",
            question=question,
            context=context,
            destination=destination,
            num_days=num_days,
            travel_style=travel_style,
            num_people=num_people
        )
        # Prepend weather summary nếu có
        if weather_info:
            import json as _json
            try:
                w = _json.loads(weather_info)
                fc = w.get("focus_forecast", {})
                weather_note = f"\n\nLƯU Ý THỜI TIẾT: {fc.get('condition','')}, {fc.get('min_temp_C','?')}-{fc.get('max_temp_C','?')}°C\n"
                rendered_prompt = rendered_prompt + weather_note
            except Exception:
                pass
        yield "🗓️⛅ "
        async for token in self.generate_stream(prompt="", user_input=rendered_prompt):
            yield token

    async def generate_multi_tool_stream(self, question: str, chunks: list[dict],
                                          tool_contexts: dict, tool_names: list[str]):
        """
        Tổng hợp kết quả từ nhiều tool chạy song song thành 1 câu trả lời.
        tool_contexts: {tool_name: data_dict} — VD: {"estimate_budget": {...budget...}}
        """
        from core.tool_formatters import format_budget_text, format_weather_text
        context = self._build_context(chunks) if chunks else ""

        # Build extra context từ tool results (weather, budget, etc.)
        extra_sections = []
        for tname, data in (tool_contexts or {}).items():
            if data and tname == "estimate_budget":
                extra_sections.append(f"NGÂN SÁCH ƯỚC TÍNH:\n{format_budget_text(data)}")
            elif data and tname == "get_weather":
                extra_sections.append(f"DỮ LIỆU THỜI TIẾT:\n{format_weather_text(data)}")

        extra = "\n\n".join(extra_sections)
        combined_prompt = f"""Trả lời ĐẦY ĐỦ câu hỏi sau dựa trên các dữ liệu được cung cấp:

CÂU HỎI: {question}

{extra}

THÔNG TIN ĐỊA ĐIỂM (TỪ KNOWLEDGE BASE):
{context if context else "Không có thông tin cụ thể từ knowledge base."}

YÊU CẦU: Trả lời tự nhiên, thân thiện. Tổng hợp các thông tin trên thành một bài viết hoàn chỉnh. KHÔNG bịa đặt."""

        yield "🔍 "
        async for token in self.generate_stream(prompt="", user_input=combined_prompt):
            yield token

    def _fix_formatting(self, text: str) -> str:
        text = re.sub('([^\\r\\n])(\\n?- )', '\\1\n\n- ', text)
        text = text.replace('\u2022 ', '\n\n- ')
        text = re.sub('\n{3,}', '\n\n', text)
        return text.strip()

    def _build_context(self, chunks: list[dict]) -> str:
        parts = []
        import re
        for i, c in enumerate(chunks):
            text_content = c.get("text", "").strip() 
            if not text_content:
                continue

            text_content = text_content.replace("###", "")
            text_content = re.sub(r'\d+(\.\d+)+', '', text_content)
            text_content = re.sub(r'Ngày \d+:?', '', text_content)
            text_content = re.sub(r'(Sáng|Trưa|Chiều|Tối):', '', text_content)

            if "Nội dung: " in text_content:
                text_content = text_content.split("Nội dung: ", 1)[-1].strip()

            parts.append(f"- {text_content}")

        return "\n\n".join(parts)
