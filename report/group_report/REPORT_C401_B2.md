# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: C401 - B2
- **Team Members**: [Lê Thành Long, Đỗ Xuân Bằng, Trương Anh Long, Bùi Văn Đạt, Lã Thị Linh, Nguyễn Huy Hoàng, Đỗ Việt Anh]
- **Deployment Date**: 6/4/2026

---

## 1. Executive Summary

Hệ thống agent được xây dựng nhằm hỗ trợ tra cứu điểm chuẩn và tư vấn chọn trường đại học dựa trên điểm số hoặc ngành học. So với chatbot thông thường, agent sử dụng mô hình ReAct (Reasoning + Acting) để thực hiện truy vấn đa bước thông qua tool.

- **Success Rate**: ~87,5% trên 8 testcase
- **Key Outcome**: Agent xử lý tốt các câu hỏi đa bước (multi-step queries), đặc biệt là:
- Tra cứu ngành → lọc theo điểm
Kết hợp reasoning + tool usage

---

          ┌──────────────┐
          │  User Input  │   <- Người dùng nhập câu hỏi
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │   Thought    │   <- LLM phân tích ý định, xác định bước tiếp theo
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │    Action    │   <- LLM chọn công cụ (tra_cuu_diem/loc_truong_theo_diem)  và input
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │ Observation  │   <- Nhận kết quả từ tool
          └──────┬───────┘
                 ↓
        ┌────────┴────────┐
        │ Enough info?    │   <- Kiểm tra đã đủ thông tin để trả Final Answer?
        └──────┬──────────┘
           No  ↓        Yes
        ┌──────────┐     ↓
        │ Thought  │  ┌──────────────┐
        └────┬─────┘  │ Final Answer │  <- Trả kết quả cho người dùng
             ↓        └──────────────┘
        (Loop lại nếu chưa đủ thông tin)

### 2.2 Tool Definitions (Inventory)

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `tra_cuu_diem` | `string` | Tra cứu điểm chuẩn theo ngành. |
| `loc_truong_theo_diem` | `float` | Lọc trường phù hợp theo điểm. |

### 2.3 LLM Providers Used

- **Primary**: gemini-3-flash-preview

---

## 3. Telemetry & Performance Dashboard

- **Average Latency (P50)**: ~ 9.96s
- **Max Latency (P99)**: ~ 19.60s
- **Average Tokens per Task**: ~ 2459.75 tokens/task
- **Total Cost of Test Suite**: ~ $0.01968

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study 1: Synonym Mismatch / Hallucinated Argument

- **Input**: "Tôi muốn điểm chuẩn ngành Công nghệ thông tin của các trường đại học là bao nhiêu?"
- **Observation**: Agent gọi `Action: tra_cuu_diem(args='Công nghệ thông tin')` trong khi đó DB lại để là CNTT
- **Root Cause**: 
  - Không đồng nhất giữa output của LLM và regex parser  
  - Không có cơ chế mapping synonym (Công nghệ thông tin ↔ CNTT)
  - Parser chỉ xử lý format cố định, không normalize args
  - Không có bước validate/clean input trước khi gọi tool 

### Case Study 2: Noisy / Invalid Input Handling

- **Input**: Agent xử lý input không hợp lệ như một câu hỏi bình thường: `@@@ CNTT ???`
- **Observation**: Agent vẫn xử lý như câu hỏi hợp lệ và gọi `tra_cuu_diem`
- **Root Cause**: 
  - Không có input validation
  - Không phân biệt noise vs intent
  - System prompt không yêu cầu clarify
  - LLM "đoán" từ keyword → sai logic
  - Không có confidence check
  - Luôn trả về Final Answer

### Case Study 3: Wrong Tool Selection

- **Input**: "Điểm chuẩn ngành CNTT của ĐH Bách Khoa là bao nhiêu?"
- **Observation**: Agent chọn `loc_truong_theo_diem` thay vì `tra_cuu_diem`
- **Root Cause**: 
  - Tool descriptions mơ hồ (đều chứa từ "điểm")
  - LLM không phân biệt rõ lookup query vs filtering query
  - Thiếu examples trong system prompt
  - Không có bước intent classification trước khi chọn tool

---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt v1 vs Prompt v2

**Diff:**

- **Prompt v1**:
  - Không có hướng dẫn xử lý input nhiễu (noisy input)
  - Không có normalize synonym (CNTT ↔ Công nghệ thông tin)
  - Không yêu cầu validate tham số trước khi gọi tool
  - Không có rule rõ ràng khi nào cần gọi tool
  - Không xử lý trường hợp input không hợp lệ

- **Prompt v2**:
  - Thêm rule input sanitization (loại bỏ ký tự đặc biệt, input rác)
  - Thêm normalize args để xử lý synonym (tin học, IT → CNTT)
  - Thêm argument validation trước khi gọi tool
  - Bổ sung rule rõ ràng về tool usage
  - Thêm xử lý input không hợp lệ / không rõ nghĩa
  - Format được enforce chặt hơn giúp parser ổn định

**Result:**

- Agent gọi tool ổn định và chính xác hơn
- Giảm lỗi do input nhiễu như: `@@@ CNTT ???`
- Xử lý đúng các biến thể ngôn ngữ:
  - `"tin học"`, `"IT"` → `"Công nghệ thông tin"`
- Giảm lỗi truyền sai kiểu dữ liệu (ví dụ: điểm không phải số)
- Tăng khả năng xử lý các câu hỏi thực tế hơn

### Experiment 2 (Bonus): Chatbot vs Agent

| Case                  | Input Example                          | Chatbot Result                                      | Agent Result                                      | Winner   |
|-----------------------|----------------------------------------|-----------------------------------------------------|---------------------------------------------------|----------|
| Tra cứu điểm chính xác | "Điểm chuẩn ngành CNTT là bao nhiêu?"  | Trả lời dựa trên knowledge nội bộ → có thể outdated / hallucinated | Gọi `tra_cuu_diem` → dữ liệu chính xác từ DB     | **Agent** |
| Synonym / Variants    | "Điểm ngành tin học?"                  | Có thể hiểu sai hoặc trả lời không nhất quán        | Normalize → CNTT → gọi tool đúng                  | **Agent** |
| Multi-step            | "Tôi được 26 điểm, học CNTT ở đâu?"    | Không xử lý được → tự bịa danh sách trường          | Gọi `loc_truong_theo_diem` → lọc trường phù hợp  | **Agent** |
| Noisy Input           | "@@@ CNTT ???"                         | Trả lời dựa trên keyword → sai ngữ cảnh             | Input được sanitize → phát hiện không hợp lệ          | **Agent**  |
| Specific Query        | "Điểm CNTT của Bách Khoa?"             | Có thể trả lời sai hoặc thiếu chính xác             | Đôi khi vẫn chọn sai tool (chưa có intent classifier rõ ràng)                  | Draw |
---

## 6. Production Readiness Review

### Security

- Đã bổ sung hàm `_sanitize_input` để loại bỏ ký tự đặc biệt và input rác
- Đã triển khai `_validate_args` để kiểm tra tham số trước khi gọi tool
- Giảm đáng kể nguy cơ injection và xử lý input không hợp lệ
- Tool hiện chỉ có quyền **read-only** → an toàn hơn cho môi trường production

### Guardrails

- Đã có `max_steps = 5` để tránh vòng lặp vô hạn
- Đã bổ sung timeout cho toàn bộ agent loop
- Có tracking token usage và logging chi tiết từng step (`AGENT_STEP`, `AGENT_END`)
- Đã triển khai fallback khi:
  - Không parse được action từ LLM
  - Arguments không hợp lệ
- **Hạn chế còn tồn tại**:
  - Chưa có cơ chế retry khi LLM trả về format sai
  - Chưa có confidence check trước khi gọi tool

### Scaling & Future Improvements

- State hiện tại vẫn dùng chuỗi (`current_context`) → nên chuyển sang **structured memory**
- Chưa hỗ trợ multi-branch reasoning
- Các cải tiến đề xuất:
  - Thêm intent classification layer trước khi chọn tool
  - Tách parser thành module riêng để dễ bảo trì
- Có thể nâng cấp lên:
  - **LangGraph**: hỗ trợ điều phối flow phức tạp và parallel tool calls
  - **LangSmith**: quan sát và debug trace chi tiết
  - **Arize AI**: monitoring và đánh giá chất lượng trong production

### Overall Assessment

Sau khi nâng cấp lên phiên bản **v2**, hệ thống đã:

- Giảm đáng kể lỗi do input nhiễu và synonym mismatch
- Tăng độ ổn định khi gọi tool
- Có các thành phần cơ bản của một production system: validation, timeout, logging

Tuy nhiên, để đạt mức **production-grade** hoàn chỉnh, vẫn cần cải thiện thêm:
- Tool selection thông qua intent classification
- Robust parsing và retry mechanism
- Structured state management
- Confidence scoring trước khi đưa ra final answer
---

> [!NOTE]
> Submit this report by renaming it to `GROUP_REPORT_[TEAM_NAME].md` and placing it in this folder.
