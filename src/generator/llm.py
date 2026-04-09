import os
import re
from openai import OpenAI, AsyncOpenAI
from core.logger import get_logger

logger = get_logger(__name__)

class LLMGenerator:
    """
    Trình sinh văn bản tinh gọn, chạy độc quyền qua Ollama Local API.
    """

    def __init__(
        self, 
        mode: str = "vllm", 
        vllm_model: str = "qwen-vivu", 
        vllm_base_url: str = None, 
        vllm_api_key: str = "sk-no-key",
        ollama_model: str = "hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M",
        temperature: float = 0.1
    ):
        self.mode = mode
        self.temperature = temperature
        self.system_prompt = self._load_system_prompt()
        
        # 1. Cấu hình cho vLLM (Cloud / Colab)
        self.vllm_model = vllm_model
        self.vllm_client = OpenAI(base_url=vllm_base_url, api_key=vllm_api_key)
        self.async_vllm_client = AsyncOpenAI(base_url=vllm_base_url, api_key=vllm_api_key)
        
        # 2. Cấu hình cho Ollama (Desktop Local)
        self.ollama_model = ollama_model
        self.ollama_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        self.async_ollama_client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        
        logger.info(f"[LLMGenerator] Đã khởi tạo thành công (Chế độ mặc định: {self.mode})")

    def _get_active_config(self):
        """Lấy đúng Config (Model, Client) dựa trên chế độ hiện tại."""
        if self.mode == "ollama":
            return self.ollama_model, self.ollama_client, self.async_ollama_client
        else: # "vllm"
            return self.vllm_model, self.vllm_client, self.async_vllm_client

    def _load_system_prompt(self) -> str:
        """Đọc file system_prompt_travel.md từ thư mục gốc."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            prompt_path = os.path.join(base_dir, "system_prompt_travel.md")
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("Không tìm thấy file system_prompt_travel.md. Dùng prompt mặc định.")
            return "Bạn là trợ lý du lịch AI am hiểu về Việt Nam. Chỉ trả lời dựa trên thông tin được cung cấp trong ngữ cảnh."


    def generate(self, prompt: str, user_input: str, temperature: float = None) -> str:
        """Hàm gọi API OpenAI/vLLM nguyên thủy."""
        temp = temperature if temperature is not None else self.temperature
        active_model, active_client, _ = self._get_active_config()
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input}
        ]
        
        response = active_client.chat.completions.create(
            model=active_model,
            messages=messages,
            temperature=temp,
            frequency_penalty=0.1
        )
        
        ans = response.choices[0].message.content.strip()
        
        # Dọn dẹp thẻ <think> đặc thù của các model hệ DeepSeek / Qwen Reasoning
        ans = re.sub(r'<think>.*?</think>\s*', '', ans, flags=re.DOTALL)
        ans = ans.replace('</think>', '').replace('<think>', '').strip()
        return ans


    def generate_answer(self, question: str, chunks: list[dict]) -> str:
        """Hàm chính thức phục vụ luồng RAG, nhận list chunks từ Qdrant."""
        if not chunks:
            return "Hiện tại ViVu chưa có thông tin trong dữ liệu về địa điểm/câu hỏi này."

        # 1. Build context
        context = self._build_context(chunks)

        # 2. Xử lý Prompt
        if "{context}" in self.system_prompt and "{query}" in self.system_prompt:
            user_prompt = self.system_prompt.replace("{context}", context).replace("{query}", question)
            system_prompt = "Bạn là ViVu, trợ lý du lịch AI am hiểu về Việt Nam. QUY TẮC SỐ 1: BẮT BUỘC chỉ trả lời thông tin có trong NGỮ CẢNH cung cấp. Tuyệt đối không bịa đặt."
        else:
            system_prompt = self.system_prompt
            user_prompt = f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI:\n{question}"

        # 3. Gọi lõi Generate
        ans = self.generate(prompt=system_prompt, user_input=user_prompt)

        # 4. Mồi thêm icon cho sinh động giống phiên bản cũ của bạn
        if not ans.startswith('🌴'):
            ans = '🌴 ' + ans
            
        return ans

    async def generate_stream(self, prompt: str, user_input: str, temperature: float = None):
        """Hàm stream từng token (Server-Sent Events) qua OpenAI API."""
        temp = temperature if temperature is not None else self.temperature
        active_model, _, active_async_client = self._get_active_config()
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input}
        ]
        
        response_stream = await active_async_client.chat.completions.create(
            model=active_model,
            messages=messages,
            stream=True,
            temperature=temp,
            frequency_penalty=0.1
        )
        
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

    async def generate_answer_stream(self, question: str, chunks: list[dict]):
        """Hàm trả về luồng text streaming cho RAG."""
        if not chunks:
            yield "🌴 Hiện tại ViVu chưa có thông tin trong dữ liệu về địa điểm/câu hỏi này."
            return

        context = self._build_context(chunks)

        if "{context}" in self.system_prompt and "{query}" in self.system_prompt:
            user_prompt = self.system_prompt.replace("{context}", context).replace("{query}", question)
            system_prompt = "Bạn là ViVu, trợ lý du lịch AI am hiểu về Việt Nam. QUY TẮC SỐ 1: BẮT BUỘC chỉ trả lời thông tin có trong NGỮ CẢNH cung cấp. Tuyệt đối không bịa đặt."
        else:
            system_prompt = self.system_prompt
            user_prompt = f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI:\n{question}"

        yield "🌴 "
        async for token in self.generate_stream(prompt=system_prompt, user_input=user_prompt):
            yield token

    # ==================================================
    # UTILS FORMATTER
    # ==================================================
    def _build_context(self, chunks: list[dict]) -> str:
        """Xây dựng context string từ các chunks và lọc bỏ rác văn bản mạnh tay."""
        parts = []
        import re
        
        for i, c in enumerate(chunks):
            text_content = c.get("text", "").strip() 
            if not text_content:
                continue

            # XỬ LÝ LỌC SẠN CẤP ĐỘ MẠNH
            # 1. Xóa các tiêu đề markdown ###
            text_content = text_content.replace("###", "")
            # 2. Xóa các ký hiệu số thứ tự dạng 4.4.4 hoặc 1. 2.
            text_content = re.sub(r'\d+(\.\d+)+', '', text_content)
            # 3. Xóa các chữ "Ngày 1", "Sáng:", "Trưa:", "Chiều:", "Tối:"
            text_content = re.sub(r'Ngày \d+:?', '', text_content)
            text_content = re.sub(r'(Sáng|Trưa|Chiều|Tối):', '', text_content)

            # 4. Filter đoạn prefix 'Nội dung: '
            if "Nội dung: " in text_content:
                text_content = text_content.split("Nội dung: ", 1)[-1].strip()

            parts.append(f"- THÔNG TIN {i+1}:\n{text_content}")

        return "\n\n".join(parts)