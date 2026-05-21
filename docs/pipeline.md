System Architecture – RAG Demo

Tài liệu này mô tả kiến trúc tổng thể của hệ thống Retrieval-Augmented Generation (RAG) được xây dựng cho bài toán hỏi đáp về du lịch Việt Nam.

Hệ thống kết hợp giữa:

mô hình embedding để truy xuất tài liệu

vector database để lưu trữ tri thức

mô hình ngôn ngữ lớn để sinh câu trả lời

Kiến trúc được thiết kế theo mô hình pipeline module hóa, giúp dễ dàng mở rộng hoặc thay thế các thành phần trong tương lai.

1. High-Level Architecture

Kiến trúc tổng thể của hệ thống được mô tả như sau:

                +-------------------+
                |      User         |
                +---------+---------+
                          |
                          v
                   +-------------+
                   |   FastAPI   |
                   |   API Layer |
                   +------+------+
                          |
                          v
                  +---------------+
                  |  Query Embed  |
                  |  (BGE Model)  |
                  +------+--------+
                         |
                         v
                 +---------------+
                 |  Vector DB    |
                 |   (Qdrant)    |
                 +------+--------+
                        |
                        v
              +---------------------+
              | Retrieved Documents |
              +----------+----------+
                         |
                         v
               +-------------------+
               | Prompt Template   |
               +---------+---------+
                         |
                         v
                 +---------------+
                 |  LLM Model    |
                 |  (Qwen2.5)    |
                 +------+--------+
                        |
                        v
                   +---------+
                   | Answer  |
                   +---------+
2. Data Ingestion Architecture

Trước khi hệ thống có thể truy xuất thông tin, dữ liệu cần được xử lý và lưu trữ vào vector database.

Pipeline ingestion:

Document Source
      |
      v
Text Extraction
(PDF / Documents)
      |
      v
Text Cleaning
      |
      v
Document Chunking
      |
      v
Embedding Generation
      |
      v
Vector Database (Qdrant)

Sau bước này, toàn bộ knowledge base được lưu dưới dạng vector embeddings để phục vụ truy xuất.

3. Retrieval-Augmented Generation Flow

Luồng xử lý chính của hệ thống khi người dùng gửi câu hỏi:

User Query
     |
     v
Query Embedding (BGE)
     |
     v
Vector Search (Qdrant)
     |
     v
Top-K Relevant Documents
     |
     v
Prompt Construction
     |
     v
LLM Generation (Qwen2.5)
     |
     v
Generated Answer

Quy trình này cho phép mô hình ngôn ngữ trả lời dựa trên tri thức được truy xuất, giúp giảm hiện tượng hallucination.

4. System Modules

Hệ thống được tổ chức theo cấu trúc module sau:

src/
 ├── api
 │    └── FastAPI endpoints
 │
 ├── embedding
 │    └── embedding model (BGE)
 │
 ├── ingestion
 │    └── document processing pipeline
 │
 ├── retrieval
 │    └── vector search logic
 │
 ├── generator
 │    └── LLM prompt & generation
 │
 └── main.py
      └── main RAG pipeline

Cấu trúc này giúp:

dễ phát triển từng module độc lập

dễ mở rộng hoặc thay thế mô hình

dễ triển khai production trong tương lai

5. Observability

Hệ thống hỗ trợ theo dõi hoạt động thông qua:

Logging

Ghi lại:

truy vấn người dùng

thời gian truy xuất

thời gian sinh câu trả lời

lỗi hệ thống

Log được lưu trong thư mục:

logs/
6. Future Extensions

Kiến trúc hệ thống được thiết kế để có thể mở rộng với các tính năng sau:

reranking model

caching layer

monitoring dashboard

LLM tracing

distributed vector database

knowledge base crawler integration