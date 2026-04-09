# 🇻🇳 Travel AI Assistant — Hệ thống RAG Du lịch Việt Nam

Dự án phát triển mô hình ngôn ngữ nhỏ cho hệ thống hỏi - đáp tiếng Việt về địa điểm du lịch trong nước, ứng dụng kiến trúc Retrieval-Augmented Generation (RAG) kết hợp với Vector Database và LLM nội bộ.



## Kiến trúc hệ thống (tóm tắt)

1) Ingestion pipeline

Raw data (JSON/TXT) → Preprocess → Chunk → Embed (bge-m3) → Store (Qdrant)

2) Query pipeline

User Query → Query Analyzer (intent/destination) → Embed query (bge-m3) → Vector Search (Qdrant) → LLM generation (Ollama / HF / Gemini)

---

## Các thành phần chính (quick map)

- `src/api/routes.py` — FastAPI routes, dependency singletons và endpoint `/api/v1/chat`.
- `src/api/schemas.py` — Pydantic schemas cho request/response (ChatRequest, ChatResponse, SourceChunk).
- `src/service/embedding.py` — `EmbeddingService` chuyển văn bản thành vector (SentenceTransformers / BGE).
- `src/vector_store/qdrant.py` — Wrapper kết nối và thao tác với Qdrant.
- `src/retrieval/` — `query_analyzer.py`, `retriever.py`, `search.py` — logic truy xuất, filter metadata, và tìm kiếm vector.
- `src/generator/llm.py` — `LLMGenerator` hỗ trợ 3 chế độ: `hf`, `ollama`, `gemini`.
- `src/pipeline/rag_pipeline.py` — Ghép nối retriever + generator để trả về (answer, sources).
- `src/main.py` — Entrypoint FastAPI (uvicorn).

---

## Yêu cầu & Cài đặt nhanh

Yêu cầu hệ thống
- Python 3.10+ 
- Ollama + GGUF giúp giảm yêu cầu RAM của Python process.

Cài dependencies (Windows example)

```powershell
#  thư mục dự án 
cd D:\2026\rag-demo

# Tạo & kích hoạt virtualenv (ví dụ dùng venv)
python -m venv .venv
.venv\Scripts\activate

# Cài các gói
pip install -r requirement.txt
```

---

## Khởi tạo LLM / Models

Tuỳ theo `mode` của LLM:

1) Ollama 
- Cài Ollama theo hướng dẫn chính thức.
- Kéo model GGUF (ví dụ Qwen2.5 3B) bằng Ollama:

```bash
ollama pull hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M
# hoặc chạy model trực tiếp để tải xuống
ollama run hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M
```

2) HuggingFace local (`hf` mode)
- Phù hợp khi bạn muốn load model trực tiếp trong Python (transformers + accelerate + bitsandbytes).
- Yêu cầu nhiều RAM/GPU; nếu dùng quantization, đọc cảnh báo về `llm_int8_enable_fp32_cpu_offload` và thiết lập `device_map` phù hợp như thông báo runtime từ transformers.

3) Google Gemini (`gemini` mode)
- Yêu cầu `google-generativeai` và API key (GEMINI_API_KEY).

---

## Cấu hình môi trường (ví dụ `.env`)

Tạo file `.env` ở root dự án nếu cần:

```text
QDRANT_HOST=localhost
QDRANT_PORT=6333
OLLAMA_HOST=http://localhost:11434
GEMINI_API_KEY=ya29.xxxxxx   
```

---

## Chạy Qdrant (Docker)

```powershell
cd infra
docker compose up -d
```

Kiểm tra:

```bash
curl http://localhost:6333/healthz
```

---

## Khởi động API Server

Từ thư mục gốc (sau khi active .venv):

```powershell
cd src
uvicorn main:app --reload --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs

---

## API: POST /api/v1/chat

Mô tả: nhận payload truy vấn, trả về câu trả lời từ RAG kèm danh sách nguồn trích dẫn.

Request (JSON):

```json
{
  "query": "An Giang có món gì ngon?",
  "top_k": 5,
  "destination": "An Giang",
  "category": "food",
  "mode": "ollama"
}
```

- `mode` (chuỗi): chọn chế độ LLM cho yêu cầu này. Hỗ trợ: `"ollama"` (mặc định), `"hf"`, `"gemini"`.

Response (tóm tắt): ChatResponse gồm
- `answer`: chuỗi câu trả lời
- `sources`: danh sách `SourceChunk` (text, destination, category, score)
- `processing_time`: thời gian xử lý (s)



## Ví dụ  (curl)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"query":"An Giang có món gì ngon?","top_k":3,"mode":"ollama"}'
```

---

## Logger

- 500 Internal Server Error: kiểm tra log tại `logs/travel_assistant.log` và console của uvicorn để xem stack trace. 
 
## Hướng dẫn chạy hệ thống (Run App)

Hệ thống hoạt động theo mô mô hình Client-Server. Thực hiện các bước theo thứ tự để đảm bảo các dịch vụ kết nối thông suốt.

### Bước 1: Khởi động Qdrant (Vector Database)
Trước khi khởi động API, đảm bảo `Qdrant` đang chạy — nơi lưu trữ và truy vấn vector.

**Sử dụng Docker :**

    cd infra
    docker compose up -d

Kiểm tra trạng thái hoạt động:

    # Kiểm tra health endpoint qua cURL
    curl http://localhost:6333/healthz

Hoặc truy cập giao diện quản lý: `http://localhost:6333/dashboard`

---

### Bước 2: Khởi động API Server (Backend)
Mở Terminal 1 (đảm bảo đã kích hoạt môi trường ảo `\.venv`):

    cd src
    .venv\Scripts\activate
    uvicorn main:app --reload --port 8000

Địa chỉ API: `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`

> Lưu ý: Backend cần khởi động xong trước khi chạy Frontend.

---

### Bước 3: Khởi động Giao diện Chatbot (Frontend)

    cd src
    .venv\Scripts\activate
    chainlit run app.py -w --port 8001

Truy cập giao diện: `http://localhost:8001`

.\.venv\Scripts\activate
chainlit run app.py -w --port 8001