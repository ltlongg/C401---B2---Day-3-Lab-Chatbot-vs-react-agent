# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Bùi Văn Đạt
- **Student ID**: 2A202600355
- **Date**: 6/4/2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implementated**: `src/tools/admission_tool.py`
- **Code Highlights**: 
  
  TOOLS_CONFIG = [
    {
        "name": "loc_truong_theo_diem",
        "description": (
            "Dùng để tìm các trường đại học có điểm chuẩn thấp hơn hoặc bằng điểm của thí sinh. "
            "Tham số 'args' phải là một con số cụ thể (ví dụ: '25.5'). "
            "Không truyền văn bản vào công cụ này."
        )
    }
]
- **Documentation**: TOOLS_CONFIG(được dùng để build system prompt) là cầu nối giữa LLM reasoning và tool execution trong ReAct loop

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Agent gọi sai tool `loc_truong_theo_diem` thay vì `tra_cuu_diem` khi người dùng hỏi về điểm chuẩn của một ngành cụ thể: *"Điểm chuẩn ngành CNTT của ĐH Bách Khoa là bao nhiêu?"
- **Log Source**:(`logs/2026-04-06.log`):
{"timestamp": "2026-04-06T10:30:15.123456", "event": "AGENT_START", "data": {"input": "Điểm chuẩn ngành CNTT của ĐH Bách Khoa là bao nhiêu?", "model": "gemini-2.5-flash"}}
{"timestamp": "2026-04-06T10:30:18.456789", "event": "LLM_METRIC", "data": {"usage": {"total_tokens": 1250}, "latency_ms": 3200}}
{"timestamp": "2026-04-06T10:30:18.456790", "event": "AGENT_END", "data": {"steps": 1, "status": "success"}}

- **Diagnosis**: LLM hiểu sai intent của câu hỏi. Câu hỏi hỏi về điểm chuẩn cụ thể của một ngành tại một trường (lookup query), nhưng agent lại chọn loc_truong_theo_diem (filtering tool) vì thấy từ "điểm chuẩn". Nguyên nhân gốc rễ là tool descriptions quá mơ hồ - cả hai tools đều chứa từ "điểm chuẩn" khiến LLM nhầm lẫn. Ngoài ra, thiếu examples trong system prompt về cách phân biệt các loại queries.
  
- **Solution**: Cải thiện tool descriptions để rõ ràng hơn

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: Khối Thought giúp Agent có thời gian "suy nghĩ" để chuyển đổi ngôn ngữ tự nhiên của người dùng thành tham số kỹ thuật chính xác. ReAct phải đi qua bước trung gian này lên sẽ ko trả lời bừa như chatbot thường.
2.  **Reliability**: In which cases did the Agent actually perform *worse* than the Chatbot?
3.  **Observation**: Khi Observation trả về rỗng => tham số truy vấn có vấn đề.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: ....
- **Safety**: Kiểm soát tham số truy vấn đầu vào hợp lý, tránh lỗi SQL Injection hoặc truy cập trái phép dữ liệu nhạy cảm.
- **Performance**: Sử dụng Vector Database hoặc Fuzzy Matching cho các công cụ tìm kiếm để Agent có thể tìm thấy kết quả ngay cả khi người dùng nhập sai định dạng hoặc viết tắt khác nhau.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
