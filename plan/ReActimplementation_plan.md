# Tích hợp ReAct Agent Loop cho Tư vấn Du lịch Toàn diện

Mục tiêu: Chuyển đổi từ mô hình "Định tuyến 1 lần (Single-shot Routing)" sang mô hình **ReAct (Reasoning and Acting) Agent** thực thụ. Hệ thống sẽ có khả năng tự suy luận, tự phát hiện thiếu sót thông tin (như điểm đi, thời gian) và gọi liên tiếp nhiều tools để thu thập đủ dữ liệu trước khi sinh câu trả lời cuối cùng.

## Vấn đề của mô hình hiện tại
Hiện tại, pipeline gọi công cụ song song trong 1 lượt (Parallel Execution). Mặc dù nhanh, nhưng nó thiếu chiều sâu. Ví dụ:
- Để tính Budget chuẩn, cần giá Flight.
- Để tính giá Flight, cần biết điểm xuất phát và thời gian.
- Nếu gọi song song, Budget không thể chờ Flight chạy xong để lấy giá. 

## Giải pháp: Kiến trúc "ViVu ReAct Engine"

Chúng ta sẽ xây dựng một class `ReActAgent` đóng vai trò "Bộ não" (Brain), sử dụng model lớn (GPT-4o-mini hoặc Cloudflare Llama-3.3-70B) để thực hiện vòng lặp suy luận.

### Sơ đồ vòng lặp (ReAct Loop)
1. **User:** "Đi Phú Quốc 4 ngày tốn bao nhiêu?"
2. **Brain (Vòng 1):**
   - *Thought:* Cần tính ngân sách. Nhưng để tính ngân sách cần biết giá vé máy bay. Mình sẽ gọi tool tìm chuyến bay trước.
   - *Action:* Gọi `search_flights(destination="Phú Quốc")`.
3. **Brain (Vòng 2):**
   - *Observation:* Giá vé khứ hồi Vietjet là 2 triệu.
   - *Thought:* Giờ mình đã có giá vé. Mình sẽ gọi tool tính ngân sách và truyền giá vé này vào.
   - *Action:* Gọi `estimate_budget(..., flight_cost=2000000)`.
4. **Brain (Vòng 3):**
   - *Observation:* Ngân sách tổng là 7.3 triệu.
   - *Thought:* Để tư vấn thêm hấp dẫn, mình nên tìm vài địa điểm chơi ở Phú Quốc.
   - *Action:* Gọi `search_knowledge_base(query="địa điểm chơi Phú Quốc")`.
5. **Brain (Vòng 4):**
   - *Observation:* Có VinWonders, Safari...
   - *Thought:* Mình đã có đủ thông tin (Vé máy bay, Ngân sách, Địa điểm). Kết thúc vòng lặp.
   - *Action:* `FINISH`.

6. **ViVu 1.7B (Tổng hợp):** Toàn bộ "bức tranh" dữ liệu (Observation) thu thập được từ ReAct Loop sẽ được gom lại thành văn bản thuần và truyền cho ViVu 1.7B để nó dùng văn phong thân thiện, tiếng Việt tự nhiên trả lời cho khách hàng + Bắn Data ra biểu đồ UI.

## Chi tiết các bước thay đổi mã nguồn (Proposed Changes)

### 1. `backend/core/react_agent.py` [NEW]
- Xây dựng class `ReActAgent` với hàm `run(question)` chứa vòng lặp `while step < MAX_STEPS`.
- Define system prompt nghiêm ngặt bắt buộc LLM trả về JSON cấu trúc: `{"thought": "...", "tool": "...", "kwargs": {...}}`.

### 2. `backend/core/tools_exec_flights.py` [NEW]
- Xây dựng tool `search_flights` giả lập (Mock API) lấy giá vé giữa các thành phố phổ biến tại VN.

### 3. `backend/core/tools_exec_budget.py` [MODIFY]
- Chỉnh sửa để hàm `estimate_budget` có thể nhận tham số `flight_cost_override` do ReAct Agent truyền vào. Nếu không truyền, nó báo lỗi hoặc yêu cầu Agent đi tìm chuyến bay trước.

### 4. `backend/pipeline/rag_pipeline.py` [MODIFY]
- Đổi `ask_stream` từ việc gọi `LLMRouter` sang gọi `ReActAgent`.
- Sau khi ReActAgent thu thập đủ Context, truyền Context đó vào `llm_generator.generate_multi_tool_stream`.

## User Review Required

> [!IMPORTANT]
> Việc xây dựng ReAct loop là cực kỳ thông minh nhưng sẽ đổi lại **độ trễ (latency)** cao hơn. 
> Thay vì mất 3 giây như hiện tại, 1 câu hỏi có thể mất 7-10 giây để Agent "suy nghĩ" và dạo qua 3-4 tools trước khi ViVu 1.7B bắt đầu nhả chữ.
>
> **Câu hỏi cho bạn:**
> 1. Bạn đồng ý đánh đổi một chút thời gian chờ (latency) để lấy khả năng phân tích cực sâu của ReAct Agent chứ? (Chúng ta có thể làm UI hiển thị *"Đang tìm vé máy bay...", "Đang tính ngân sách..."* để khách khỏi sốt ruột).
> 2. Kế hoạch này sẽ thay thế trực tiếp module LLMRouter cũ bằng ReActAgent. Bạn duyệt cho tôi triển khai theo hướng này nhé?
