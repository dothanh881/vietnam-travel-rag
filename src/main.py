import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import router mà bạn đã viết ở bước trước
from api.routes import router as travel_router

app = FastAPI(
    title="Travel AI Assistant API",
    description="Backend API cho hệ thống RAG hỏi - đáp địa điểm du lịch trong nước.",
    version="1.0.0"
)

# Cấu hình CORS để cho phép Frontend chạy ở cổng 3000) gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Khi deploy thật,  thay bằng domain cụ thể (VD: "http://localhost:3000")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nhúng toàn bộ các endpoint từ routes.py vào app với tiền tố /api/v1
app.include_router(travel_router, prefix="/api/v1")

# Endpoint mặc định để kiểm tra server có đang sống (Health Check)
@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "online",
        "message": "Hệ thống Travel RAG đang hoạt động. Truy cập /docs để xem Swagger UI."
    }

if __name__ == "__main__":
    print("Đang khởi động Travel RAG Server...")
    # Chạy server với uvicorn, bật chế độ reload để tự động cập nhật khi bạn sửa code
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)