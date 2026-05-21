import json
import re

# 1. Hàm Tracking/Bóc tách JSON (Câu trả lời cho câu hỏi của bạn)
def parse_tool_call(response_text: str):
    """
    Hàm này dùng Regular Expression (Regex) để tìm và "móc" chuỗi JSON ra khỏi văn bản.
    Bởi vì đôi khi LLM sẽ sinh ra kiểu: "Dạ đây là tool: ```json {...} ```"
    """
    # Regex tìm đoạn text nằm giữa cặp ```json và ```
    pattern = r"```json\s*(\{.*?\})\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    
    if match:
        json_str = match.group(1)
        try:
            # Parse chuỗi string thành Dictionary (Object) của Python
            tool_call_dict = json.loads(json_str)
            return tool_call_dict
        except json.JSONDecodeError:
            print("Lỗi: LLM sinh ra JSON không hợp lệ.")
            return None
    
    # Nếu không tìm thấy markdown json, thử tìm cặp ngoặc nhọn đầu tiên
    pattern_fallback = r"(\{.*?\})"
    match_fallback = re.search(pattern_fallback, response_text, re.DOTALL)
    if match_fallback:
        json_str = match_fallback.group(1)
        try:
            tool_call_dict = json.loads(json_str)
            # Kiểm tra xem nó có đúng là tool call không (có chứa key 'tool')
            if "tool" in tool_call_dict:
                return tool_call_dict
        except json.JSONDecodeError:
            pass
            
    return None

# 2. Định nghĩa System Prompt với hướng dẫn rõ ràng
SYSTEM_PROMPT = """Bạn là ViVu, một trợ lý ảo du lịch tại Việt Nam thông minh và lịch sự.
Bạn có khả năng quyết định khi nào cần tìm kiếm thông tin hoặc kiểm tra thời tiết.

CÔNG CỤ CÓ SẴN (TOOLS):
1. search_knowledge_base: Dùng để tìm kiếm thông tin địa điểm, khách sạn, nhà hàng, kinh nghiệm du lịch tại Việt Nam.
2. get_weather: Dùng để kiểm tra thời tiết hiện tại của một địa danh.

QUY TẮC PHẢN HỒI:
- Nếu bạn cần dùng công cụ, BẮT BUỘC TRẢ VỀ ĐÚNG định dạng JSON sau:
```json
{
  "tool": "tên_công_cụ",
  "query": "tham_số_tìm_kiếm_hoặc_địa_điểm"
}
```
- Không giải thích gì thêm khi trả về JSON.
- Nếu câu hỏi là lời chào hoặc bạn đã có đủ thông tin, hãy trả lời trực tiếp bằng tiếng Việt lịch sự.

VÍ DỤ (FEW-SHOT):
User: Chào ViVu nhé.
Assistant: Dạ, ViVu xin chào ạ. ViVu có thể giúp gì cho chuyến du lịch sắp tới của bạn không?
User: Đà Lạt có quán cafe nào view đồi thông đẹp không?
Assistant: ```json
{"tool": "search_knowledge_base", "query": "quán cafe view đồi thông Đà Lạt"}
```
User: Nhiệt độ Hà Nội hôm nay sao?
Assistant: ```json
{"tool": "get_weather", "query": "Hà Nội"}
```"""

# 3. Các hàm Tool giả lập
def dummy_rag_search(query: str) -> str:
    print(f"\n[HỆ THỐNG ĐANG CHẠY RAG] Đang tìm trong Vector DB với query: '{query}'...")
    # Giả lập RAG trả về kết quả
    if "đà lạt" in query.lower():
        return "Túi Mơ To là quán cafe nổi tiếng ở Đà Lạt với view đồi thông và nhà kính."
    return "Không tìm thấy thông tin cụ thể trong dữ liệu."

def dummy_get_weather(location: str) -> str:
    print(f"\n[HỆ THỐNG ĐANG GỌI API] Lấy thời tiết thực tế cho: '{location}'...")
    # Giả lập gọi API
    if "hà nội" in location.lower():
        return "Nhiệt độ hiện tại: 25 độ C, trời nhiều mây, không mưa."
    return "Nhiệt độ hiện tại: 22 độ C, trời nắng đẹp."

# 4. Orchestrator Logic (Vòng lặp Agentic)
def agentic_rag_flow(user_message: str, mock_llm_response_1: str, mock_llm_response_2: str = None):
    print(f"\n{'='*50}\nUser: {user_message}\n")
    
    # BƯỚC 1: LLM NGHĨ VÀ QUYẾT ĐỊNH (Tự động hoặc gọi Tool)
    # Giả lập việc đẩy System Prompt và User Message vào Model và lấy câu trả lời
    print(f"-> [LLM Output Bước 1]: {mock_llm_response_1}")
    
    # --- ĐÂY LÀ ĐOẠN TRẢ LỜI CÂU HỎI CỦA BẠN (TRACKING ROUTE) ---
    tool_call = parse_tool_call(mock_llm_response_1)
    
    if tool_call:
        tool_name = tool_call.get("tool")
        tool_query = tool_call.get("query")
        print(f"\n[ROUTER] Phát hiện LLM muốn gọi Tool: {tool_name} với tham số: {tool_query}")
        
        # BƯỚC 2: THỰC THI TOOL
        tool_result = ""
        if tool_name == "search_knowledge_base":
            tool_result = dummy_rag_search(tool_query)
        elif tool_name == "get_weather":
            tool_result = dummy_get_weather(tool_query)
        else:
            tool_result = "Công cụ không hợp lệ."
            
        print(f"[TOOL RESULT]: {tool_result}")
        
        # BƯỚC 3: LLM TỔNG HỢP CÂU TRẢ LỜI
        # Ta sẽ nhét tool_result vào prompt và gọi lại LLM (giả lập là mock_llm_response_2)
        print(f"\n-> [LLM Output Bước 3 (Dựa trên kết quả Tool)]: {mock_llm_response_2}")
        return mock_llm_response_2
        
    else:
        # LLM trả lời trực tiếp, không gọi Tool
        print("\n[ROUTER] LLM trả lời trực tiếp văn bản, không dùng công cụ.")
        return mock_llm_response_1

if __name__ == "__main__":
    # --- TEST CASE 1: LỜI CHÀO ---
    agentic_rag_flow(
        user_message="Hello bạn, mình chuẩn bị đi chơi.",
        mock_llm_response_1="Dạ, ViVu xin chào ạ! Bạn dự định đi du lịch ở đâu vậy, để ViVu tư vấn cho nhé?"
    )
    
    # --- TEST CASE 2: HỎI RAG ---
    agentic_rag_flow(
        user_message="Giới thiệu cho mình vài quán cafe view đồi thông ở Đà Lạt với",
        mock_llm_response_1='```json\n{"tool": "search_knowledge_base", "query": "quán cafe view đồi thông Đà Lạt"}\n```',
        mock_llm_response_2="Dạ, theo thông tin ViVu tìm hiểu được, ở Đà Lạt có quán cafe Túi Mơ To rất nổi tiếng với view nhìn ra đồi thông và khu nhà kính đó ạ. Bạn có muốn biết thêm chi tiết về quán này không?"
    )
    
    # --- TEST CASE 3: HỎI THỜI TIẾT ---
    agentic_rag_flow(
        user_message="Hà Nội hôm nay nóng không?",
        mock_llm_response_1='Để mình kiểm tra. ```json\n{"tool": "get_weather", "query": "Hà Nội"}\n```',
        mock_llm_response_2="Dạ, nhiệt độ hiện tại ở Hà Nội đang là 25 độ C, trời nhiều mây và không mưa ạ. Thời tiết rất mát mẻ để dạo phố đó bạn."
    )
