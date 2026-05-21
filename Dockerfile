FROM python:3.11-slim

WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết (nếu có) cho việc biên dịch
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirement.txt từ thư mục gốc
COPY requirement.txt .

# Cài đặt Python dependencies
RUN pip install --no-cache-dir -r requirement.txt

# Copy thư mục backend vào
COPY backend/ ./backend/

# Đặt biến môi trường
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

# Expose port (mặc định 8000)
EXPOSE 8000

# Chạy uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
