# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Le Thanh Long
- **Student ID**: 2A202600105
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implementated**: `main.py`, `src/chatbot.py`
- **Code Highlights**: Em đóng góp vào file `main.py` để cấu hình và chạy thử luồng xử lý chính của agent với câu hỏi test cụ thể. Ngoài ra, em làm việc với `src/chatbot.py` để xây dựng và kiểm tra baseline chatbot streaming, từ đó so sánh hành vi giữa chatbot thông thường và ReAct agent.

```python
# main.py
def main():
    llm = GeminiProvider()
    agent = ReActAgent(llm=llm, tools=TOOLS_CONFIG)

    query = "Ngành CNTT lấy bao nhiêu điểm?"
    print(f"--- ĐANG XỬ LÝ CÂU HỎI: {query} ---")
    response = agent.run(query)

    print("\n" + "=" * 50)
    print("PHẢN HỒI CUỐI CÙNG:")
    print(response)


# src/chatbot.py
def streaming_chatbot() -> None:

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    history = []
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit"]:
            break

        history.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=history,
            stream=True
        )

        print("Assistant: ", end="", flush=True)
        assistant_response = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            print(delta, end="", flush=True)
            assistant_response += delta

        history.append({"role": "assistant", "content": assistant_response})
        history = history[-6:]  # Keep only the last 3 turns
```

- **Documentation**: File `main.py` đóng vai trò entry point, khởi tạo provider, khởi tạo agent và gửi truy vấn mẫu vào hệ thống. File `src/chatbot.py` cung cấp một baseline chatbot sử dụng OpenAI streaming, giúp đối chiếu khả năng hỏi đáp trực tiếp với cách agent suy nghĩ, gọi tool và quan sát kết quả.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Agent xử lý chưa chính xác truy vấn nhiều ý khi người dùng hỏi: *"CNTT lấy bao nhiêu điểm và có trường nào dưới 27 không?"* Ở bước đầu, agent gọi tool `tra_cuu_diem` nhưng truyền sai tham số `Công nghệ thông tin` thay vì `CNTT`, khiến hệ thống không tìm thấy dữ liệu. Sau đó agent tiếp tục dùng `loc_truong_theo_diem(27)` để xử lý phần thứ hai của câu hỏi, nhưng câu trả lời cuối cùng bị lặp lại nhiều đoạn `Thought/Action/Observation`, làm output bị bẩn và khó đọc.

- **Log Source** (`logs/2026-04-06.log`):

```json
{"timestamp": "2026-04-06T14:09:04.444409", "event": "AGENT_START", "data": {"input": "CNTT lấy bao nhiêu điểm và có trường nào dưới 27 không?", "model": "gemini-2.5-flash"}}
{"timestamp": "2026-04-06T14:09:14.458517", "event": "AGENT_END", "data": {"steps": 3, "status": "success"}}
```

- **Diagnosis**: Đây là lỗi kết hợp giữa truyền sai tham số cho tool và xử lý output cuối chưa chặt chẽ. User dùng từ viết tắt `CNTT`, nhưng LLM lại tự đổi thành `"Công nghệ thông tin"` khi gọi `tra_cuu_diem`, trong khi database nội bộ chỉ lưu ngành dưới dạng `"CNTT"`, nên bước tra cứu đầu tiên thất bại. Sau đó agent vẫn tiếp tục xử lý phần lọc trường dưới 27 điểm bằng `loc_truong_theo_diem(27)`, nhưng đến bước `Final Answer` thì model lặp lại cả reasoning trace cũ. Nguyên nhân gốc rễ là:

- Dữ liệu tra cứu chưa hỗ trợ alias giữa `"CNTT"` và `"Công nghệ thông tin"`.
- System prompt chưa ràng buộc đủ mạnh việc chỉ trả về một `Final Answer` sạch.
- Parser trong agent chỉ tách chuỗi theo `"Final Answer:"`, nên không loại bỏ được phần `Thought/Action/Observation` bị lặp lại.

- **Solution**: Em đề xuất cải thiện theo 3 hướng:

- Chuẩn hóa tên ngành trước khi tra cứu, ví dụ map `"công nghệ thông tin"` về `"CNTT"`.
- Viết lại tool descriptions và system prompt để nhấn mạnh agent phải giữ nguyên tên ngành từ user hoặc chỉ dùng alias hợp lệ.
- Cải thiện logic parser của `Final Answer` để chỉ lấy phần trả lời cuối cùng, không kèm các block reasoning đã lặp lại.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1. **Reasoning**: ReAct agent tốt hơn chatbot thường ở chỗ nó có khả năng tách bài toán thành các bước `Thought -> Action -> Observation` thay vì trả lời trực tiếp bằng trí nhớ mô hình.
2. **Reliability**: Agent mạnh hơn với bài toán nhiều bước, nhưng cũng dễ thất bại hơn chatbot nếu tool description mơ hồ, parser mong manh, hoặc model gọi sai format.
3. **Observation**: Observation đóng vai trò như phản hồi từ môi trường, giúp model điều chỉnh quyết định ở bước tiếp theo thay vì tiếp tục suy đoán trong "đầu" của nó.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Tách tool registry thành các hàm riêng, kết nối database thật thay vì hard-code danh sách dữ liệu trong `agent.py`.
- **Safety**: Thêm validation cho tham số tool, alias normalization, và guardrails để chặn hallucinated tools.
- **Performance**: Ghi thêm `LLM_METRIC`, latency, token usage, và cải thiện parser để giảm vòng lặp lỗi.

---

> [!NOTE]
> Rename this file to `REPORT_[YOUR_NAME].md` before submission.
