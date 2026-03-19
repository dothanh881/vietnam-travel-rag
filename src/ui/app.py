import httpx
import chainlit as cl

API_URL = "http://localhost:8000/api/v1/chat"


@cl.on_chat_start
async def start():
    # Chỉ giữ lại phần chọn LLM và số lượng kết quả để demo
    settings = await cl.ChatSettings(
        [
            cl.input_widget.Select(
                id="mode",
                label="🤖 Chế độ mô hình (LLM)",
                values=["ollama", "gemini", "hf"],
                initial_index=0,
            ),
            cl.input_widget.Slider(
                id="top_k",
                label="📚 Số chunk trích xuất (Top K)",
                initial=5,
                min=1,
                max=10,
                step=1,
            )
        ]
    ).send()

    cl.user_session.set("settings", settings)

    welcome_msg = """ **Chào bạn! Mình là Trợ lý Du lịch Việt Nam AI.**

Hãy hỏi mình bất cứ điều gì tự nhiên nhất nhé!
"""
    await cl.Message(content=welcome_msg).send()


@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("settings", settings)


@cl.on_message
async def main(message: cl.Message):
    settings = cl.user_session.get("settings", {})
    mode = settings.get("mode", "ollama")
    top_k = settings.get("top_k", 5)

    # Payload gửi xuống backend giờ chỉ có câu hỏi thuần túy
    payload = {
        "query": message.content,
        "top_k": int(top_k),
        "mode": mode
    }

    msg = cl.Message(content="*Đang phân tích câu hỏi và tìm kiếm...* 🔍")
    await msg.send()

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(API_URL, json=payload)
            response.raise_for_status()
            data = response.json()

            answer = data.get("answer", "Xin lỗi, đã xảy ra lỗi.")
            sources = data.get("sources", [])
            proc_time = data.get("processing_time", 0.0)

            msg.content = answer + f"\n\n*(⏱️ Hoàn thành trong: {proc_time}s)*"

            source_elements = []
            if sources:
                for i, src in enumerate(sources):
                    s_dest = src.get("destination", "Không rõ")
                    s_cat = src.get("category", "Không rõ")
                    score = src.get("score", 0.0)
                    text = src.get("text", "")

                    details = f"📍 **Địa điểm:** {s_dest} | 🏷️ **Danh mục:** {s_cat} | 🎯 **Điểm:** {score:.3f}\n\n📝 **Nội dung:**\n{text}"

                    source_elements.append(
                        cl.Text(name=f"📚 Nguồn {i + 1} ({s_dest})", content=details, display="inline")
                    )

            msg.elements = source_elements
            await msg.update()

        except Exception as e:
            msg.content = f"❌ **Lỗi hệ thống:** {str(e)}"
            await msg.update()