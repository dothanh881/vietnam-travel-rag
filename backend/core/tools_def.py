import json

# Định nghĩa rõ ràng danh sách các công cụ có sẵn (Tools Schema)
AVAILABLE_TOOLS = [
    {
        "name": "search_knowledge_base",
        "description": "Dùng để tìm kiếm thông tin chi tiết về địa điểm, khách sạn, nhà hàng, ẩm thực, lịch trình du lịch, giá vé tại Việt Nam.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa tìm kiếm ngắn gọn, tối ưu cho semantic search."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_weather",
        "description": "Dùng để kiểm tra dự báo thời tiết và phân tích mức độ phù hợp cho các hoạt động du lịch.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Tên địa danh/tỉnh thành cần xem thời tiết."
                },
                "activity": {
                    "type": "string",
                    "description": "Hoạt động du lịch dự kiến (trekking, beach, camping, cloud hunting, sightseeing...). Trả về rỗng nếu không rõ."
                },
                "date": {
                    "type": "string",
                    "description": "Thời gian (hôm nay, ngày mai, 3 ngày tới...). Mặc định là 'today'."
                }
            },
            "required": ["location"]
        }
    }
]

def get_tools_prompt_section() -> str:
    """
    Hàm này tự động chuyển đổi danh sách các Tools thành một chuỗi văn bản format đẹp
    để nhúng vào System Prompt một cách gọn gàng, không làm rác prompt chính.
    """
    prompt_lines = ["CÁC CÔNG CỤ CÓ SẴN (TOOLS):"]
    for i, tool in enumerate(AVAILABLE_TOOLS, 1):
        prompt_lines.append(f"{i}. {tool['name']}: {tool['description']}")
    
    return "\n".join(prompt_lines)

def get_tool_json_schema() -> str:
    """Trả về format mẫu JSON để hướng dẫn LLM"""
    return '''```json
{
  "tool": "tên_công_cụ",
  "kwargs": {
    "tham_so_1": "giá trị 1",
    "tham_so_2": "giá trị 2"
  }
}
```'''
