from pydantic import BaseModel, Field
from typing import Optional, List

# ==========================================
# REQUEST SCHEMAS (Client -> Server)
# ==========================================

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str = Field(..., description="Câu hỏi du lịch của người dùng")
    top_k: int = Field(default=5, ge=1, le=20, description="Số lượng kết quả tìm kiếm")
    mode: str = Field(default="vllm", description="Chế độ chạy LLM (vllm hoặc ollama)")
    session_id: Optional[str] = Field(default=None, description="Định danh luồng hội thoại Redis")
    history: List[ChatMessage] = Field(default_factory=list, description="Lịch sử chat")

class IngestRequest(BaseModel):
    destination: Optional[str] = Field(None, description="Lọc theo tỉnh/thành (VD: 'an-giang'). Nếu để trống sẽ quét tất cả.")
    category: Optional[str] = Field(None, description="Lọc theo danh mục (VD: 'food'). Nếu để trống sẽ quét tất cả.")
    file_name: Optional[str] = Field(None, description="Tên file cụ thể (VD: 'merged_an-giang_food_chunks.json'). Nếu để trống sẽ quét tất cả.")
# ==========================================
# RESPONSE SCHEMAS (Server -> Client)
# ==========================================

class SourceChunk(BaseModel):
    text: str = Field(..., description="Nội dung trích dẫn")
    destination: Optional[str] = Field(None, description="Địa điểm")
    category: Optional[str] = Field(None, description="Phân loại (food/place/itinerary)")
    score: float = Field(..., description="Điểm tương đồng Cosine")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời từ AI")
    sources: List[SourceChunk] = Field(default_factory=list, description="Danh sách tài liệu tham khảo")
    processing_time: float = Field(..., description="Thời gian xử lý (giây)")

class IngestResponse(BaseModel):
    status: str = Field(..., description="Trạng thái (thành công/thất bại)")
    chunks_inserted: int = Field(..., description="Số lượng bản ghi đã nạp vào Qdrant")
