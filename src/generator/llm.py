import torch


class LLMGenerator:
    """
    Gộp:
    - ContextBuilder
    - PromptBuilder
    - Generator (Qwen)

    Dùng cho demo RAG
    """

    def __init__(self, model, tokenizer, device="cuda"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    # ==================================================
    # MAIN API
    # ==================================================

    def generate_answer(self, question: str, chunks: list[dict]) -> str:
        if not chunks:
            return "Hiện tại mình chưa có thông tin trong dữ liệu."

        # 1. build context
        context = self._build_context(chunks)

        # 2. build prompt
        prompt = self._build_prompt(context, question)

        # 3. generate
        return self._generate(prompt)

    # ==================================================
    # CONTEXT
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
            return (
                f"Tên: {content.get('name')}\n"
                f"Giá: {content.get('average_price')}"
            )

        elif category == "place":
            return (
                f"Tên: {content.get('name')}\n"
                f"Địa chỉ: {content.get('address')}"
            )

        elif category == "destination":
            return (
                f"Tên: {content.get('name')}\n"
                f"Khí hậu: {content.get('climate')}"
            )

        elif category == "itinerary":
            return (
                f"Thời gian: {content.get('duration')}\n"
                f"Lịch trình: {content.get('schedule')}"
            )

        return ""

    # ==================================================
    # PROMPT
    # ==================================================

    def _build_prompt(self, context, question):
        return f"""
Bạn là trợ lý du lịch AI trung thực.
Chỉ trả lời dựa trên thông tin trong ngữ cảnh.
Nếu không có thông tin, hãy nói không biết.

NGỮ CẢNH:
{context}

CÂU HỎI:
{question}
"""

    # ==================================================
    # GENERATE
    # ==================================================

    def _generate(self, prompt):
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.1,
                do_sample=False,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id
            )

        decoded = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # remove prompt
        return decoded[len(prompt):].strip()