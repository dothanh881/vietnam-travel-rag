import os
import torch

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

    def generate_answer(self, question: str, chunks: list[dict]) -> str:
        if not chunks:
            return "Hiện tại mình chưa có thông tin trong dữ liệu về địa điểm này."

        # 1. Build context
        context = self._build_context(chunks)

        # 2. Build system/user prompt cơ bản
        prompt_dict = self._build_prompt(context, question)

        # 3. Điều hướng bộ sinh text tùy theo mode
        if self.mode == "hf":
            return self._generate_hf(prompt_dict)
        elif self.mode == "ollama":
            return self._generate_ollama(prompt_dict)
        elif self.mode == "gemini":
            return self._generate_gemini(prompt_dict)

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

    def _build_prompt(self, context, question):
        # Trả về Dictionary để các hàm generate tự parse theo chuẩn API của nó
        return {
            "system": "Bạn là trợ lý du lịch AI am hiểu về Việt Nam. Chỉ trả lời dựa trên thông tin được cung cấp trong ngữ cảnh. Nếu không có thông tin, hãy nói 'Mình chưa có thông tin về vấn đề này'.",
            "user": f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI:\n{question}"
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
        prompt_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.tokenizer(
            prompt_text, return_tensors="pt", truncation=True, max_length=2048
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.1,
                do_sample=False,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.pad_token_id
            )

        input_length = inputs['input_ids'].shape[1]
        generated_tokens = outputs[0][input_length:]
        return self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

    def _generate_ollama(self, prompt_dict):
        """Xử lý gọi qua Ollama local server"""
        messages = [
            {"role": "system", "content": prompt_dict["system"]},
            {"role": "user", "content": prompt_dict["user"]}
        ]
        response = ollama.chat(
            model=self.ollama_model,
            messages=messages
        )
        return response['message']['content'].strip()

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