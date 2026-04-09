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
                label=" Chọn Động cơ Suy luận (LLM)",
                values=["vllm", "ollama"],
                initial_index=0,
            ),
            cl.input_widget.Slider(
                id="top_k",
                label=" Số chunk trích xuất (Top K)",
                initial=3,
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
    top_k = settings.get("top_k", 3)

    # Payload gửi xuống backend giờ bao gồm cả mode
    payload = {
        "query": message.content,
        "top_k": int(top_k),
        "mode": mode
    }

    API_URL_STREAM = API_URL + "/stream"
    msg = cl.Message(content="")
    await msg.send()

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            import json
            async with client.stream("POST", API_URL_STREAM, json=payload) as response:
                response.raise_for_status()

                source_elements = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        
                        try:
                            data_json = json.loads(data_str)
                            
                            if data_json.get("type") == "status":
                                status_msg = data_json.get("data", "")
                                # Nếu đang trong quá trình hoặc sau khi stream, thì chỉ nối thêm vào cuối
                                if msg.content and "⏳" not in msg.content:
                                    msg.content += f"\n\n{status_msg}"
                                else:
                                    msg.content = status_msg
                                await msg.update()
                            
                            elif data_json.get("type") == "sources":
                                sources = data_json.get("data", [])
                                for i, src in enumerate(sources):
                                    s_dest = src.get("destination", "Không rõ")
                                    s_cat = src.get("category", "Không rõ")
                                    # Ưu tiên lấy điểm Rerank để hiển thị độ chính xác mới
                                    score = src.get("rerank_score") or src.get("score", 0.0)
                                    text = src.get("text", "")

                                    details = f" **Địa điểm:** {s_dest} |  **Danh mục:** {s_cat} |  **Điểm:** {score:.3f}\n\n **Nội dung:**\n{text}"

                                    source_elements.append(
                                        cl.Text(name=f" Nguồn {i + 1} ({s_dest})", content=details, display="inline")
                                    )
                                msg.elements = source_elements
                            
                            elif data_json.get("type") == "token":
                                token = data_json.get("data", "")
                                # Xoá message chờ nếu đây là token đầu tiên (🌴)
                                if "⏳" in msg.content:
                                    msg.content = ""
                                await msg.stream_token(token)
                                
                            elif data_json.get("type") == "error":
                                await msg.stream_token(f"\n\n LỖI: {data_json.get('data')}")
                                
                        except Exception as e:
                            print(f"Lỗi parse SSE JSON: {e}")

            await msg.update()

        except Exception as e:
            msg.content = f" **Lỗi hệ thống:** {str(e)}"
            await msg.update()