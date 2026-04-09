import httpx
import chainlit as cl
import json

API_URL = "http://localhost:8000/api/v1/chat/stream"


@cl.on_chat_start
async def start():
    # Chỉ giữ lại phần chọn LLM và số lượng kết quả để demo
    settings = await cl.ChatSettings(
        [
            cl.input_widget.Select(
                id="mode",
                label=" Chế độ mô hình (LLM)",
                values=["ollama", "gemini", "hf"],
                initial_index=0,
            ),
            cl.input_widget.Slider(
                id="top_k",
                label=" Số chunk trích xuất (Top K)",
                initial=5,
                min=1,
                max=10,
                step=1,
            )
        ]
    ).send()

    cl.user_session.set("settings", settings)

    welcome_msg = """ **Chào bạn! Mình là ViVu - Trợ lý Du lịch Việt Nam.**

Mình đã được nâng cấp hệ thống **Cohere Reranker Cloud** và luồng **Streaming** mới. Hãy thử hỏi mình bất cứ điều gì nhé!
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

    payload = {
        "query": message.content,
        "top_k": int(top_k),
        "mode": mode
    }

    # 1. Khởi tạo tin nhắn trống để stream
    msg = cl.Message(content="")
    await msg.send()

    # 2. Xử lý Streaming
    full_answer = ""
    status_lines = []
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream("POST", API_URL, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line: continue
                    if not line.startswith("data: "): continue
                    
                    raw_data = line[6:].strip()
                    if raw_data == "[DONE]": break
                        
                    data = json.loads(raw_data)
                    dtype = data.get("type")
                    content = data.get("data")

                    if dtype == "token":
                        full_answer += content
                        # Cập nhật nội dung chính (Text + Status)
                        footer = "\n\n" + "\n".join(status_lines)
                        msg.content = full_answer + footer
                        await msg.update()

                    elif dtype == "status":
                        status_lines.append(content)
                        footer = "\n\n" + "\n".join(status_lines)
                        msg.content = full_answer + footer
                        await msg.update()

                    elif dtype == "sources":
                        source_elements = []
                        for i, src in enumerate(content):
                            s_dest = src.get("destination", "Không rõ")
                            score = src.get("score", 0.0)
                            r_score = src.get("rerank_score")
                            text = src.get("text", "")
                            
                            score_info = f"Điểm vector: {score:.3f}"
                            if r_score: 
                                score_info += f" | Điểm Rerank: {r_score:.3f}"

                            details = f" **Địa điểm:** {s_dest} | {score_info}\n\n **Nội dung:**\n{text}"
                            source_elements.append(
                                cl.Text(name=f" Nguồn {i+1} ({s_dest})", content=details, display="inline")
                            )
                        msg.elements = source_elements
                        await msg.update()

                    elif dtype == "error":
                        msg.content = f" **Lỗi hệ thống:** {content}"
                        await msg.update()

        except Exception as e:
            msg.content = f" **Lỗi kết nối:** {str(e)}"
            await msg.update()