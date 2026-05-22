# Tích hợp ReAct Agent Loop Cấp Độ 2 (Multi-Turn & Multi-Transport)

Mục tiêu: Đưa Agentic RAG lên mức độ "tự nhận thức". Khi thiếu thông tin quan trọng để lập kế hoạch, Agent sẽ chủ động dừng lại và hỏi người dùng thay vì tự bịa (hallucinate) thông tin. Đồng thời hỗ trợ đa dạng loại hình phương tiện di chuyển.

## Phân tích bài toán của bạn
Bạn đã chỉ ra một "lỗ hổng" lớn của các Bot thông thường: Khi người dùng hỏi *"Đi du lịch tốn bao nhiêu?"*, Bot thường tự động gán mặc định (ví dụ đi 3 ngày, đi máy bay).
Một hệ thống **Agentic thực thụ** phải có khả năng:
1. Nhận biết mình thiếu `from_city`, `to_city`, `num_days`.
2. Dừng việc gọi các Tool tính toán lại.
3. Chuyển sang hành động **Ask_User** (Hỏi lại người dùng).
4. Lưu trữ trạng thái vào bộ nhớ (Memory/Chat History) để khi người dùng trả lời *"Từ Hà Nội đi Phú Quốc 4 ngày"*, nó nối tiếp luồng tính toán.
5. So sánh hoặc lựa chọn giữa các phương tiện (Máy bay, Xe khách).

## Kiến trúc "Stateful ReAct Engine"

Chúng ta sẽ xây dựng class `ReActAgent` với bộ công cụ đa dạng và logic xử lý đa lượt (multi-turn).

### Sơ đồ vòng lặp Đa lượt (Multi-turn ReAct Loop)
- **User (Turn 1):** *"Tôi muốn đi du lịch Phú Quốc tính giúp chi phí."*
- **Brain (Agent Loop):**
  - *Thought:* Người dùng muốn tính ngân sách đi Phú Quốc, nhưng thiếu `from_city` (để tính tiền vé) và `num_days`.
  - *Action:* Gọi tool `ask_user(question="Bạn dự định xuất phát từ đâu và đi trong mấy ngày? Bạn muốn đi máy bay hay xe khách?")`.
  - *(Luồng backend tạm dừng, trả câu hỏi về cho UI)*

- **User (Turn 2):** *"Tôi đi từ Hà Nội, đi 4 ngày, đi máy bay nhé."*
- **Brain (Agent Loop):**
  - *Thought:* (Đọc lịch sử chat) Đã có đủ `from_city: Hà Nội`, `to_city: Phú Quốc`, `days: 4`, `transport: flight`. Tiến hành lập kế hoạch.
  - *Action 1:* Gọi `search_transport(from="Hà Nội", to="Phú Quốc", type="flight")`.
  - *Observation 1:* Giá vé khứ hồi 2 triệu.
  - *Action 2:* Gọi `search_knowledge_base(query="địa điểm chơi, quán ăn Phú Quốc")`.
  - *Observation 2:* VinWonders (giá vé 950k), Bún Quậy Kiến Xây...
  - *Action 3:* Gọi `estimate_budget(flight=2M, hotel=..., days=4)`.
  - *Action 4:* `FINISH` (Đẩy mọi data cho ViVu 1.7B tổng hợp ra câu trả lời tự nhiên).

## Chi tiết các bước triển khai (Proposed Changes)

### 1. `backend/core/react_agent.py` [NEW]
- Xây dựng class `ReActAgent`.
- Thêm cơ chế nhận diện Missing Parameters. Nếu thiếu, Agent sẽ route thẳng tới tool `ask_user`.

### 2. `backend/core/tools_exec_transport.py` (Mở rộng từ flight) [NEW]
- Hỗ trợ hàm `search_transport(from, to, type="flight" | "bus" | "train")`. 
- Trả về mức giá ước tính khác nhau (Vé xe giường nằm rẻ hơn vé máy bay).

### 3. `backend/core/tools_exec_budget.py` [MODIFY]
- Sửa hàm `estimate_budget` để tính toán động dựa trên danh sách địa điểm/quán ăn lấy từ RAG (VD: nếu RAG nói VinWonders 950k, thì nạp luôn số 950k vào `entrance_fee` thay vì dùng mức 100k mặc định).

### 4. Xử lý Lịch sử Chat (Chat History) trong Pipeline
- Để Agent biết câu trả lời *"4 ngày"* ở Turn 2 là đang nối tiếp câu hỏi ở Turn 1, Pipeline bắt buộc phải truyền kèm `history` (mảng tin nhắn cũ) vào Prompt của ReActAgent.

## User Review Required

> [!IMPORTANT]
> Đây là một kiến trúc rất phức tạp và cực kỳ sát với các hệ thống AI Agent cấp độ doanh nghiệp (như AutoGPT).
> 
> **Xin ý kiến chốt hạ của bạn:**
> 1. **Về Memory:** Để Agent nhớ được "Điểm đi, điểm đến" qua nhiều lượt chat, hệ thống cần gửi kèm lịch sử chat từ UI xuống Backend. Bạn đồng ý triển khai luôn phần truyền History này chứ?
> 2. **Về Transport:** Tôi sẽ tạo 1 Tool `search_transport` hỗ trợ cả Máy bay và Xe khách (Bus). Tùy vào khoảng cách (VD: Hà Nội - Sài Gòn xa quá sẽ tự gợi ý máy bay, còn Hà Nội - Sa Pa thì sẽ gợi ý xe khách). Hợp lý không?
> 3. Chúng ta bắt tay vào Code ngay module `react_agent.py` nhé?
