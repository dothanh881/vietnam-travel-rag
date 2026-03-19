from pydantic import BaseModel, Field
from typing import Optional, List

# ==========================================
# REQUEST SCHEMAS (Client -> Server)
# ==========================================

class ChatRequest(BaseModel):
    query: str = Field(..., description="Câu hỏi du lịch của người dùng")
    top_k: int = Field(default=5, ge=1, le=10, description="Số lượng kết quả tìm kiếm")
    destination: Optional[str] = Field(None, description="Lọc theo tỉnh/thành (VD: 'An Giang')")
    category: Optional[str] = Field(None, description="Lọc theo danh mục (VD: 'food')")
    mode: str = Field(default="ollama", description="Chế độ chạy LLM: 'ollama', 'gemini', hoặc 'hf'")

class IngestRequest(BaseModel):
    file_path: str = Field(..., description="Đường dẫn tới file JSON chứa dữ liệu du lịch")

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