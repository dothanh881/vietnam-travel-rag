# Kế hoạch Triển khai Single Model Agentic RAG cho ViVu Assistant

## Mục tiêu (Goal)
Nâng cấp hệ thống ViVu Assistant từ kiến trúc **Naive RAG** (luôn luôn tìm kiếm vector) lên **Agentic RAG** (tự quyết định khi nào cần tìm kiếm hoặc dùng công cụ), sử dụng duy nhất mô hình Qwen 2.5 3B đã SFT hiện tại của bạn.

Vì chúng ta chưa fine-tune lại model với tập data Tool Calling, phương pháp chính ở bước này là sử dụng **System Prompt Engineering kết hợp Few-shot Examples** để "ép" mô hình tuân thủ định dạng.

## User Review Required
> [!IMPORTANT]
> Phương pháp này phụ thuộc vào khả năng Zero-shot/Few-shot của mô hình Qwen 2.5 3B SFT hiện tại. Nếu mô hình đã bị "catastrophic forgetting" (quên cách viết JSON do train quá nhiều data hội thoại thuần), tỉ lệ lỗi cú pháp (Syntax Error) khi sinh JSON có thể sẽ cao. Bước này là phép thử nghiệm để đánh giá giới hạn của model hiện tại.

## Open Questions
> [!WARNING]
> 1. Hiện tại ở Backend (`d:\2026\travel-agent\backend`), bạn đang tự viết logic bằng Python thuần hay đang dùng framework như LangChain / LlamaIndex? Việc này ảnh hưởng đến cách chúng ta viết Orchestrator code.
> 2. Ngoài tool `search_tourism_database` (RAG hiện tại), bạn có muốn test thêm tool `get_weather` ngay trong bước này không, hay chỉ tập trung biến RAG thành Tool trước?

---

## Chi tiết Đề xuất Thay đổi (Proposed Changes)

### 1. Thiết kế lại System Prompt & Tool Schema
Thay vì system prompt chỉ quy định "bạn là trợ lý du lịch", chúng ta phải nâng cấp nó thành một bản hướng dẫn sử dụng công cụ.

**Định nghĩa Tool (Ví dụ):**
```json
[
  {
    "name": "search_knowledge_base",
    "description": "Sử dụng công cụ này khi cần tìm kiếm thông tin về địa điểm du lịch, khách sạn, nhà hàng, lịch trình tại Việt Nam.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Câu truy vấn tìm kiếm ngắn gọn, tối ưu cho semantic search."
        }
      },
      "required": ["query"]
    }
  }
]
```

### 2. Chuẩn bị Few-shot Examples (Rất quan trọng)
Cần nhúng ít nhất 2-3 ví dụ vào prompt để mô hình bắt chước cách hành xử.

*   **Ví dụ 1 (Không cần Tool):**
    *   *User:* "Chào ViVu nhé."
    *   *Assistant:* "Dạ, ViVu xin chào ạ. ViVu có thể giúp gì cho chuyến du lịch sắp tới của bạn không?"
*   **Ví dụ 2 (Cần Tool):**
    *   *User:* "Đà Lạt có quán cafe nào view đồi thông đẹp không?"
    *   *Assistant:* ````json\n{"tool": "search_knowledge_base", "query": "quán cafe view đồi thông Đà Lạt"}\n````

### 3. Xây dựng Orchestrator Logic (Vòng lặp Agent)
Logic ở Backend (API endpoint) sẽ thay đổi thành một vòng lặp `while` (tối đa 2-3 bước).

*   **Vòng 1 (Nghĩ & Quyết định):**
    *   Đẩy [System Prompt + Few shot + User Question] vào Qwen 3B.
    *   Bắt chuỗi output.
*   **Vòng 2 (Xử lý Tool):**
    *   *Nếu Output là chuỗi JSON:* Hệ thống sẽ parse JSON, lấy hàm `search_knowledge_base` và chạy tìm kiếm Qdrant. Sau đó, append kết quả tìm kiếm vào tin nhắn dưới dạng: `<tool_result>Kết quả từ DB: ...</tool_result>`. Tiếp tục gọi mô hình lần 2 để nó tổng hợp câu trả lời dựa trên `<tool_result>`.
    *   *Nếu Output là Text thường:* Coi như đó là câu trả lời cuối, trả về luôn cho Frontend.

---

## Kế hoạch Kiểm tra (Verification Plan)

### Kiểm tra Thủ công (Manual Verification)
1.  **Test Case 1 (Small Talk):** Gửi các câu chào hỏi ("Hello", "Bạn tên gì?"). Kiểm tra xem mô hình có trả lời trực tiếp mà không bịa ra một chuỗi JSON lỗi hay không.
2.  **Test Case 2 (RAG Trigger):** Gửi câu hỏi yêu cầu thông tin ("Giá vé Vinpearl Nam Hội An"). Kiểm tra xem:
    *   Mô hình có xuất ra đúng định dạng `{"tool": ...}` không.
    *   Hệ thống code có parse thành công JSON không.
    *   Mô hình có lấy kết quả RAG để trả lời tiếng Việt chuẩn hay không.
3.  **Test Case 3 (Out-of-scope):** Gửi câu hỏi không liên quan. Kiểm tra xem nó có từ chối theo persona hay không.

### Bước tiếp theo
Nếu bạn đồng ý với hướng tiếp cận này và giải đáp các Open Questions, tôi sẽ tiến hành viết script test/demo (Orchestrator) trực tiếp trong thư mục backend của bạn.
