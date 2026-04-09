import os
import torch
import re

# Import các thư viện API bên ngoài (Cần pip install ollama google-generativeai)
try:
    import ollama
except ImportError:
    ollama = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class LLMGenerator:
    """
    Hỗ trợ 3 chế độ (mode):
    1. 'hf': Chạy HuggingFace local (Qwen2.5 3B baseline hoặc Qwen + LoRA)
    2. 'ollama': Chạy qua Ollama local API (Tiết kiệm RAM, dễ quản lý)
    3. 'gemini': Chạy qua Google Gemini API (Cloud)
    """

    def __init__(
            self,
            mode: str = "hf",
            hf_model=None,
            hf_tokenizer=None,
            device="cuda",
            ollama_model="qwen2.5:3b",
            gemini_api_key=None
    ):
        self.mode = mode.lower()

        # 1. Cấu hình mode HuggingFace (Qwen/LoRA)
        if self.mode == "hf":
            if hf_model is None or hf_tokenizer is None:
                raise ValueError("Mode 'hf' yêu cầu truyền vào hf_model và hf_tokenizer.")
            self.model = hf_model
            self.tokenizer = hf_tokenizer
            self.device = device

        # 2. Cấu hình mode Ollama
        elif self.mode == "ollama":
            if ollama is None:
                raise ImportError("Vui lòng cài đặt thư viện: pip install ollama")
            self.ollama_model = ollama_model

        # 3. Cấu hình mode Gemini
        elif self.mode == "gemini":
            if genai is None:
                raise ImportError("Vui lòng cài đặt thư viện: pip install google-generativeai")
            api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("Mode 'gemini' cần GEMINI_API_KEY.")
            genai.configure(api_key=api_key)
            # Sử dụng model flash cho tốc độ nhanh, phù hợp RAG
            self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')

        else:
            raise ValueError(f"Mode không hợp lệ: {self.mode}. Chọn 'hf', 'ollama', hoặc 'gemini'.")

    # ==================================================
    # MAIN API
    # ==================================================

    async def generate_answer_stream(self, question: str, chunks: list[dict]):
        if not chunks:
            yield "🌴 Hiện tại mình chưa có thông tin trong dữ liệu về địa điểm này."
            return

        # 1. Build context & prompt
        context = self._build_context(chunks)
        prompt_dict = self._build_prompt(context, question)

        # 2. Điều hướng bộ luồng sinh text tùy theo mode
        if self.mode == "hf":
            async for token in self._generate_hf_stream(prompt_dict):
                yield token
        elif self.mode == "ollama":
            async for token in self._generate_ollama_stream(prompt_dict):
                yield token
        elif self.mode == "gemini":
            async for token in self._generate_gemini_stream(prompt_dict):
                yield token

    def generate_answer(self, question: str, chunks: list[dict]) -> str:
        if not chunks:
            return "Hiện tại mình chưa có thông tin trong dữ liệu về địa điểm này."

        # 1. Build context
        context = self._build_context(chunks)

        # 2. Build system/user prompt cơ bản
        prompt_dict = self._build_prompt(context, question)

        # 3. Điều hướng bộ sinh text tùy theo mode
        ans = ""
        if self.mode == "hf":
            ans = self._generate_hf(prompt_dict)
        elif self.mode == "ollama":
            ans = self._generate_ollama(prompt_dict)
        elif self.mode == "gemini":
            ans = self._generate_gemini(prompt_dict)
            
        # 4. Hậu kỳ (Post-processing) dọn dẹp rác từ SLM
        # Xóa khối <think>...</think> do model bản DeepSeek-distilled tự sinh ra
        ans = re.sub(r'<think>.*?</think>\s*', '', ans, flags=re.DOTALL)
        # Quét nốt các mảnh vỡ tag còn sót lại
        ans = ans.replace('</think>', '').replace('<think>', '').strip()
        
        return ans

    # ==================================================
    # STREAM GENERATORS CHO TỪNG MODE
    # ==================================================

    async def _generate_hf_stream(self, prompt_dict):
        """Streaming cho HuggingFace (Local) - Giả lập đơn giản cho demo"""
        ans = self._generate_hf(prompt_dict)
        yield ans

    async def _generate_ollama_stream(self, prompt_dict):
        """Streaming cho Ollama (Async)"""
        import ollama
        messages = [
            {"role": "system", "content": prompt_dict["system"]},
            {"role": "user", "content": prompt_dict["user"]}
        ]
        
        # Mồi chữ nếu cần
        yield "🌴 "

        # Gọi Async stream của ollama
        async for part in await ollama.AsyncClient().chat(
            model=self.ollama_model,
            messages=messages,
            stream=True,
            options={"temperature": 0.1}
        ):
            token = part['message']['content']
            yield token

    async def _generate_gemini_stream(self, prompt_dict):
        """Streaming cho Gemini Cloud API"""
        full_prompt = f"{prompt_dict['system']}\n\n{prompt_dict['user']}"
        response = self.gemini_model.generate_content(
            full_prompt,
            stream=True,
            generation_config=genai.types.GenerationConfig(temperature=0.1)
        )
        
        yield "🌴 "
        for chunk in response:
            if chunk.text:
                yield chunk.text

    # ==================================================
    # CONTEXT & PROMPT (Dùng chung cho cả 3 mode)
    # ==================================================

    def _build_context(self, chunks):
        parts = []
        for c in chunks:
            dest = c.get("destination", "")
            cat = c.get("category", "")
            content = c.get("content", {})
            text = c.get("text", "")

            structured = self._format_content(content, cat)
            block = (
                f"[Địa điểm: {dest} | Loại: {cat}]\n"
                f"{structured}\n"
                f"Mô tả: {text}"
            )
            parts.append(block)

        return "\n---\n".join(parts)

    def _format_content(self, content, category):
        if category == "food":
            return f"Tên: {content.get('name')}\nGiá: {content.get('average_price')}"
        elif category == "place":
            return f"Tên: {content.get('name')}\nĐịa chỉ: {content.get('address')}"
        elif category == "destination":
            return f"Tên: {content.get('name')}\nKhí hậu: {content.get('climate')}"
        elif category == "itinerary":
            return f"Thời gian: {content.get('duration')}\nLịch trình: {content.get('schedule')}"
        return ""

    def _load_system_prompt(self):
        try:
            # Tính toán đường dẫn tới system_prompt_travel.md nằm ngoài src/
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            prompt_path = os.path.join(base_dir, "system_prompt_travel.md")
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "Bạn là trợ lý du lịch AI am hiểu về Việt Nam. Chỉ trả lời dựa trên thông tin được cung cấp trong ngữ cảnh."
            
    def _build_prompt(self, context, question):
        # Đọc trực tiếp template từ file
        template = self._load_system_prompt()
        
        # Nếu template dùng chuẩn tag {} mới
        if "{context}" in template and "{query}" in template:
            user_prompt = template.replace("{context}", context).replace("{query}", question)
            # Nâng cấp System Prompt
            system_prompt = "Bạn là ViVu, trợ lý du lịch AI am hiểu về Việt Nam. Nhiệm vụ tối thượng của bạn là trả lời DỰA HOÀN TOÀN VÀO NGỮ CẢNH cung cấp. Tuyệt đối không tự bịa đặt thông tin ngoài ngữ cảnh."
        else:
            # Fallback nếu dùng prompt cũ
            system_prompt = template
            user_prompt = f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI:\n{question}"
            
        return {
            "system": system_prompt,
            "user": user_prompt
        }

    # ==================================================
    # GENERATORS CHO TỪNG MODE
    # ==================================================

    def _generate_hf(self, prompt_dict):
        """Xử lý sinh text cho Qwen / Qwen + LoRA local"""
        messages = [
            {"role": "system", "content": prompt_dict["system"]},
            {"role": "user", "content": prompt_dict["user"]}
        ]
        
        # Tạo chuỗi ChatML
        prompt_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        # KỸ THUẬT MỒI CHỮ (PRE-FILL): Ép thẳng vào đuôi chuỗi
        prefill_text = "🌴 Chào bạn, theo cẩm nang của ViVu, đây là những gợi ý:\n"
        prompt_text += prefill_text

        inputs = self.tokenizer(
            prompt_text, return_tensors="pt", truncation=True, max_length=2048
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,       # Nâng từ 0.1 lên 0.3 cho tự nhiên
                repetition_penalty=1.15, # Chống lặp từ
                do_sample=True,        # Phải là True nếu dùng temperature > 0
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.pad_token_id
            )

        # Cắt bỏ phần prompt đầu vào để lấy kết quả
        input_length = inputs['input_ids'].shape[1]
        generated_tokens = outputs[0][input_length:]
        ans = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        
        # Ghép lại phần đã mồi
        return prefill_text + ans

    def _generate_ollama(self, prompt_dict):
        """Xử lý gọi qua Ollama local server"""
        messages = [
            {"role": "system", "content": prompt_dict["system"]},
            {"role": "user", "content": prompt_dict["user"]}
        ]
        response = ollama.chat(
            model=self.ollama_model,
            messages=messages,
            options={
                "temperature": 0.1,    # Ép nhiệt độ thấp để tránh model bịa chuyện hoặc lặp từ vô tận
                "num_predict": 512
            }
        )
        ans = response['message']['content'].strip()
        
        # Xóa thẻ <think> do các model họ DeepSeek (như Qwen R1) sinh ra
        ans = re.sub(r'<think>.*?</think>\s*', '', ans, flags=re.DOTALL)
        ans = ans.replace('</think>', '').replace('<think>', '').strip()
        
        # Nếu model lười không sinh hình cây dừa (do bị User mồi trong prompt), ta chủ động bù vào
        if not ans.startswith('🌴'):
            ans = '🌴 ' + ans
            
        return ans

    def _generate_gemini(self, prompt_dict):
        """Xử lý gọi qua Gemini Cloud API"""
        # Gemini 1.5/2.0 API thường nhận system instruction trong cấu hình model,
        # nhưng ghép thẳng vào prompt cũng hoạt động rất tốt cho RAG.
        full_prompt = f"{prompt_dict['system']}\n\n{prompt_dict['user']}"

        response = self.gemini_model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
            )
        )
        return response.text.strip()