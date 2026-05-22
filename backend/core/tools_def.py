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
    },
    {
        "name": "search_transport",
        "description": "Dùng để ước tính chi phí di chuyển (vé máy bay, xe khách, tàu hỏa) giữa 2 thành phố.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_city": {"type": "string", "description": "Thành phố xuất phát"},
                "to_city": {"type": "string", "description": "Thành phố đến"},
                "transport_type": {"type": "string", "description": "Loại phương tiện: 'flight', 'bus', hoặc 'train' (mặc định là 'flight')"}
            },
            "required": ["from_city", "to_city"]
        }
    },
    {
        "name": "estimate_budget",
        "description": "Dùng để ước lượng ngân sách chuyến đi du lịch cho 1 hoặc nhiều người.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {"type": "string", "description": "Điểm đến (Thành phố/Tỉnh)"},
                "num_days": {"type": "integer", "description": "Số ngày du lịch"},
                "num_people": {"type": "integer", "description": "Số người tham gia (mặc định 1)"},
                "travel_style": {"type": "string", "description": "Kiểu du lịch: 'budget', 'mid', 'luxury'"},
                "transport_cost_per_person": {"type": "integer", "description": "Chi phí di chuyển khứ hồi/người (Lấy từ search_transport nếu có)"},
                "additional_entrance_fees": {"type": "integer", "description": "Phí tham quan đặc biệt cộng thêm (VD vé VinWonders 950k) lấy từ RAG."}
            },
            "required": ["destination", "num_days"]
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
