import os
from dotenv import load_dotenv

# Tải biến môi trường từ thư mục root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(travel_router, prefix="/api/v1")


@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "online",
        "message": "Hệ thống Travel RAG đang hoạt động. Truy cập /docs để xem Swagger UI."
    }

if __name__ == "__main__":
    print("Đang khởi động Travel RAG Server...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
