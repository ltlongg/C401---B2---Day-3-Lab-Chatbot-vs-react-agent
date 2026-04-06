# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: C401 - B2
- **Team Members**: Le Thanh Long, Truong Anh Long, La Thi Linh, Do Xuan Bang, Bui Van Dat, Nguyen Huy Hoang, Do Viet Anh
- **Deployment Date**: 2026-04-06

---

## 1. Executive Summary

Trong Lab 3, nhóm xây dựng một hệ thống tư vấn tuyển sinh theo hướng agentic để trả lời các câu hỏi về điểm chuẩn và lựa chọn trường đại học. Mục tiêu chính là so sánh sự khác biệt giữa một chatbot chỉ sinh câu trả lời bằng LLM và một ReAct Agent có khả năng suy luận từng bước, chọn công cụ phù hợp và dùng kết quả từ tool để hoàn thiện câu trả lời cuối cùng.

Baseline chatbot có thể trả lời được các câu hỏi mang tính mô tả chung, nhưng dễ bịa thông tin khi người dùng hỏi theo kiểu nhiều bước như: "Em được 27 điểm thì có thể vào trường nào?" hoặc "Ngành CNTT trường nào có điểm dưới mức X?". Trong khi đó, ReAct Agent của nhóm chủ động tách bài toán thành các bước `Thought -> Action -> Observation -> Final Answer`, nhờ vậy giảm đáng kể tỷ lệ trả lời cảm tính và tăng khả năng bám sát dữ liệu.

- **Success Rate**: ~87.5% trên 8 test case nội bộ của nhóm
- **Key Outcome**: Agent xử lý tốt hơn rõ rệt với câu hỏi đa bước, đặc biệt là các truy vấn cần vừa xác định ngành vừa đối chiếu ngưỡng điểm đầu vào
- **Main Improvement over Chatbot**: Thay vì trả lời trực tiếp bằng suy đoán từ mô hình, agent chỉ đưa ra kết luận sau khi đã gọi tool và đọc lại observation
- **Business Value**: Đây là một prototype phù hợp cho các hệ thống tư vấn tuyển sinh cơ bản, nơi độ tin cậy của dữ liệu quan trọng hơn độ "trôi chảy" của câu trả lời

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

Agent của nhóm được triển khai trong `src/agent/agent.py` dưới dạng vòng lặp ReAct có giới hạn `max_steps = 5`. Ở mỗi bước, agent gửi toàn bộ ngữ cảnh hiện tại cho mô hình, yêu cầu mô hình sinh ra suy nghĩ và hành động tiếp theo theo một format thống nhất.

Luồng xử lý tổng quát:

```text
User Question
    |
    v
Build system prompt + current context
    |
    v
LLM generates:
Thought: ...
Action: tool_name(args)
    |
    v
Regex parser extracts tool call
    |
    v
Execute tool in local admission database
    |
    v
Append Observation to context
    |
    +----> if "Final Answer:" exists -> return answer
    |
    +----> else continue until max_steps
```

Điểm quan trọng của kiến trúc này là agent không chỉ "nói" mà còn "hành động". Observation sau mỗi tool call được đưa ngược lại vào prompt cho bước tiếp theo, giúp mô hình có cơ sở để ra quyết định tiếp thay vì suy luận hoàn toàn trong đầu.

### 2.2 Tool Definitions (Inventory)

Nhóm hiện sử dụng 2 tool domain-specific phục vụ riêng cho bài toán tuyển sinh:

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `tra_cuu_diem` | `string` | Tra cứu điểm chuẩn theo tên ngành. Dùng khi người dùng muốn biết một ngành cụ thể có mức điểm đầu vào bao nhiêu. |
| `loc_truong_theo_diem` | `float` | Lọc danh sách trường có điểm chuẩn nhỏ hơn hoặc bằng điểm của thí sinh. Dùng trong các truy vấn tư vấn chọn trường theo mức điểm. |

Mô tả tiến hóa của tool design:

1. Ban đầu nhóm chỉ có ý tưởng để LLM tự trả lời dựa trên prompt.
2. Sau khi nhận thấy chatbot dễ hallucinate, nhóm tách kiến thức tuyển sinh thành các tool có trách nhiệm rõ ràng.
3. Mỗi tool được mô tả khá cụ thể trong `src/tools/admission_tools.py`, bao gồm tên, mục đích và ràng buộc kiểu dữ liệu đầu vào.
4. Việc viết description rõ ràng giúp giảm lỗi gọi sai tool, dù vẫn còn một số trường hợp mô hình truyền tham số chưa đúng format.

### 2.3 Data Layer Used by Tools

Trong phiên bản lab hiện tại, dữ liệu được mô phỏng bằng một local in-memory database ngay trong hàm `_execute_tool()`. Tập dữ liệu gồm các trường và ngành tiêu biểu:

- DH Bach Khoa - CNTT - 28.15
- DH Kinh Te Quoc Dan - Logistics - 27.0
- DH Cong Nghe - DHQGHN - CNTT - 27.5
- DH Giao Thong Van Tai - CNTT - 24.5

Điểm mạnh của cách làm này là đơn giản, dễ debug và phù hợp cho bài lab. Điểm hạn chế là dữ liệu nhỏ, chưa có khả năng cập nhật real-time, chưa tách riêng thành database hoặc API layer.

### 2.4 LLM Providers Used

Kiến trúc provider của nhóm được tách thành interface chung `LLMProvider`, cho phép hoán đổi backend mà không phải sửa logic agent.

- **Primary**: Gemini 2.5 Flash (`src/core/gemini_provider.py`)
- **Secondary / Alternative**: OpenAI provider (`src/core/openai_provider.py`)
- **Offline / Local Option**: Local GGUF model qua `llama-cpp-python` (`src/core/local_provider.py`)

Thiết kế này là một điểm cộng lớn về mặt kỹ thuật vì:

- Tách biệt business logic và model provider
- Dễ benchmark giữa các model khác nhau
- Hỗ trợ mở rộng sang production hoặc local inference khi cần tối ưu chi phí

---

## 3. Telemetry & Performance Dashboard

Nhóm có tích hợp khung telemetry cơ bản thông qua `src/telemetry/logger.py` và `src/telemetry/metrics.py`. Logger ghi event ở dạng JSON, còn metrics tracker hỗ trợ thu thập token, latency và ước lượng cost cho mỗi request.

Kết quả tổng hợp từ lần final test run nội bộ:

- **Average Latency (P50)**: ~9.96s
- **Max Latency (P99)**: ~19.60s
- **Average Tokens per Task**: ~2459.75 tokens/task
- **Total Cost of Test Suite**: ~$0.01968

Phân tích các chỉ số:

1. **Latency còn cao so với chuẩn production**
   Với bài toán chatbot tư vấn thông thường, gần 10 giây cho một tác vụ là khá chậm. Nguyên nhân chính đến từ:
   - Agent phải gọi LLM nhiều vòng thay vì một lần
   - Mỗi vòng lặp mang theo ngữ cảnh dài hơn vòng trước
   - Mô hình Gemini cần thời gian xử lý cả reasoning lẫn format output

2. **Token usage cao do ReAct loop**
   Mỗi vòng lặp đều gửi lại system prompt và toàn bộ history hiện tại. Điều này làm số token tăng nhanh, nhất là khi output của mô hình dài hoặc observation verbose.

3. **Cost hiện ở mức chấp nhận được cho demo**
   Tổng chi phí test suite vẫn thấp, phù hợp cho môi trường học tập và prototype. Tuy nhiên nếu scale lên hàng nghìn request mỗi ngày thì cần tối ưu prompt, giảm loop và nén context.

4. **Telemetry framework đã có nhưng tích hợp chưa hoàn toàn khép kín**
   Mã nguồn có `PerformanceTracker`, tuy nhiên trong phiên bản hiện tại tracker chưa được gọi trực tiếp bên trong `ReActAgent.run()`. Điều này cho thấy nhóm đã có tư duy đúng về observability nhưng vẫn còn việc phải làm để đạt mức production-ready thực sự.

---

## 4. Root Cause Analysis (RCA) - Failure Traces

Phần failure analysis là nơi nhóm rút ra nhiều bài học nhất. Agent không thất bại vì "không thông minh", mà thường thất bại ở giao diện giữa LLM reasoning và deterministic code như parser, format output và chuẩn hóa dữ liệu đầu vào.

### Case Study 1: Mismatch giữa tên ngành người dùng và dữ liệu tool

- **Input**: "Toi muon biet diem chuan nganh Cong nghe thong tin."
- **Expected Behavior**: Agent gọi `tra_cuu_diem("Cong nghe thong tin")` và trả về kết quả cho nhóm ngành CNTT.
- **Observed Behavior**: Agent gọi đúng tool nhưng observation trả về rỗng hoặc "Khong tim thay du lieu nganh nay."
- **Why it Happened**:
  - Database lưu dữ liệu dưới dạng viết tắt `CNTT`
  - Người dùng nhập tên đầy đủ `Cong nghe thong tin`
  - Tool hiện dùng so khớp chuỗi đơn giản bằng `in`, chưa có bước synonym mapping hay chuẩn hóa miền dữ liệu
- **Root Cause**: Domain normalization chưa tốt, không có lớp ánh xạ giữa từ vựng người dùng và schema dữ liệu nội bộ
- **Lesson Learned**: Trong hệ thống agent, chất lượng tool không chỉ nằm ở hàm gọi mà còn nằm ở cách chuẩn hóa dữ liệu trước và sau khi tool chạy

### Case Study 2: LLM sinh Action sai định dạng parser mong đợi

- **Input**: Một số câu hỏi phức tạp cần nhiều bước suy luận
- **Observed Behavior**: Mô hình sinh ra reasoning hợp lý nhưng quên xuống dòng đúng format `Action: ten_tool(tham_so)`
- **System Response**: Agent thêm observation báo lỗi: "Ban chua dua ra Action dung dinh dang..."
- **Why it Happened**:
  - Parser hiện dùng regex tương đối cứng: `Action:\\s*(\\w+)\\((.*)\\)`
  - Chỉ cần mô hình thêm mô tả thừa, đổi format, hoặc dùng dấu câu không đúng là parser thất bại
- **Root Cause**: Format contract giữa LLM và parser còn mong manh, phụ thuộc quá nhiều vào prompt compliance
- **Lesson Learned**: Khi xây agent cho production, nên ưu tiên JSON schema hoặc function calling thay vì regex text parsing

### Case Study 3: Tool argument không đúng kiểu dữ liệu

- **Input**: "Em duoc hai muoi bay diem thi hoc truong nao?"
- **Expected Behavior**: Agent chuyển đổi ý định người dùng thành `loc_truong_theo_diem(27.0)`
- **Observed Behavior**: Trong một số tình huống, mô hình có thể truyền argument ở dạng chữ hoặc câu mô tả dài thay vì số thực
- **Impact**: Tool trả về `"Loi: Tham so diem phai la mot so thuc."`
- **Root Cause**:
  - Prompt đã mô tả tool cần số thực nhưng chưa có few-shot đủ mạnh
  - Không có bước validate và coercion trước khi gọi tool
- **Lesson Learned**: Tool robust hơn khi có lớp adapter chuyển đổi input mềm dẻo trước khi vào business logic

### Summary of Failure Patterns

Ba nhóm lỗi chính mà nhóm quan sát được:

- **Semantic mismatch**: Người dùng và database gọi cùng một khái niệm bằng hai cách khác nhau
- **Parser fragility**: LLM sinh đúng ý nhưng sai format
- **Argument validation gap**: Tool nhận dữ liệu chưa được chuẩn hóa

Đây là khác biệt rất rõ giữa chatbot và agent: chatbot thường "sai trong im lặng", còn agent cho phép nhìn thấy lỗi ở từng bước và truy ngược nguyên nhân chính xác hơn.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Chatbot Baseline vs ReAct Agent

Mục tiêu của thí nghiệm này là kiểm tra xem việc thêm tool và vòng lặp ReAct có thực sự tạo ra khác biệt hay không.

| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Cau hoi don gian: "Diem chuan CNTT la bao nhieu?" | Thuong tra loi duoc, nhung co the khong sat data | Tra loi dua tren tool | **Agent** |
| Cau hoi theo nguong diem: "Em duoc 27 diem thi vao truong nao?" | De doan theo kien thuc mo hinh | Goi `loc_truong_theo_diem` va loc du lieu | **Agent** |
| Cau hoi da buoc: "Nganh CNTT co truong nao duoi 27 diem?" | Thuong lap luan mo ho, de hallucinate | Co the chia thanh cac buoc truy van va tong hop | **Agent** |
| Cau hoi mo ta chung, khong can tool | Tra loi nhanh | Tra loi duoc nhung cham hon | Draw |

**Kết luận**: ReAct Agent vượt trội khi bài toán yêu cầu truy xuất dữ liệu hoặc suy luận nhiều bước. Chatbot baseline chỉ phù hợp cho các câu hỏi chung, không đòi hỏi grounding vào nguồn dữ liệu cụ thể.

### Experiment 2: Prompt v1 vs Prompt v2

- **Prompt v1**: Chỉ yêu cầu agent suy nghĩ và trả lời
- **Prompt v2**: Bổ sung quy tắc rõ ràng hơn:
  - Luôn bắt đầu bằng `Thought`
  - Mỗi lượt chỉ được gọi một action
  - Action phải nằm trên một dòng riêng
  - Nếu đủ thông tin thì trả về `Final Answer` ngay

**Kết quả định tính**:

- Prompt v2 giúp agent ổn định hơn về format
- Giảm tình trạng mô hình trả lời thẳng mà quên action
- Dễ debug hơn vì trace nhất quán hơn

**Giới hạn còn lại**:

- Prompt tốt hơn không giải quyết triệt để vấn đề synonym của dữ liệu
- Regex parser vẫn là điểm yếu nếu output hơi lệch format

### Experiment 3: Flexible Provider Architecture

Nhóm cũng thử thiết kế theo hướng provider abstraction thay vì hard-code một model duy nhất.

- Cùng một logic agent có thể chạy với Gemini, OpenAI hoặc local model
- Điều này cho phép so sánh giữa chất lượng reasoning, độ ổn định format và chi phí
- Về mặt kiến trúc, đây là tiền đề tốt cho production benchmarking và fallback strategy

---

## 6. Production Readiness Review

Phiên bản hiện tại đã là một prototype tốt cho mục tiêu học tập và demo, nhưng để đưa vào môi trường thực tế thì vẫn cần thêm nhiều lớp bảo vệ và tối ưu.

### 6.1 Security

- Input của người dùng hiện chưa được sanitize một cách có cấu trúc
- Tool execution đang chạy trên local logic nên chưa có rủi ro lớn về hệ thống ngoài, nhưng nếu đổi sang DB/API thật thì cần validate nghiêm ngặt hơn
- Chưa có cơ chế phân quyền, rate limiting hoặc audit log theo user session

### 6.2 Guardrails

- Đã có `max_steps = 5` để tránh vòng lặp vô hạn
- Agent có phản hồi fallback khi không parse được action
- Tuy nhiên vẫn chưa có:
  - retry strategy theo loại lỗi
  - confidence threshold trước khi kết luận
  - tool whitelist enforcement ở tầng parser/executor ngoài check tên cơ bản

### 6.3 Reliability

- Dữ liệu đang hard-code nên độ ổn định cao trong demo nhưng không phản ánh độ phức tạp của production
- Chưa có automated evaluation pipeline đọc log và tính aggregate reliability theo version
- Chưa có test coverage cho các failure path quan trọng như parser fail, wrong argument type, synonym mapping

### 6.4 Scalability

Để mở rộng hệ thống thành sản phẩm thật, nhóm đề xuất lộ trình sau:

1. Tách database tuyển sinh ra khỏi code và đưa vào file dữ liệu hoặc DB thật
2. Thay regex parsing bằng JSON schema hoặc native function calling
3. Chuẩn hóa tên ngành, trường, khu vực bằng dictionary hoặc retrieval layer
4. Gắn telemetry trực tiếp vào mỗi vòng lặp để đo:
   - số bước reasoning
   - latency từng bước
   - token theo step
   - tỷ lệ lỗi parser và lỗi tool
5. Nâng cấp thành graph-based orchestration nếu số tool tăng lên nhiều

### 6.5 Overall Production Verdict

**Mức hiện tại**: Prototype học tập tốt, đủ để minh họa rõ lợi ích của ReAct Agent so với chatbot thường.

**Chưa đạt production full-scale** vì:

- parser còn fragile
- dữ liệu còn nhỏ và hard-code
- telemetry chưa tích hợp end-to-end
- chưa có lớp chuẩn hóa input/output đủ mạnh

Dù vậy, phần quan trọng nhất của lab đã đạt được: nhóm không chỉ làm cho agent "chạy được", mà còn hiểu vì sao agent thành công, vì sao agent thất bại, và cần bổ sung gì để tiến gần hơn tới một hệ thống agentic thực tế.

---

## 7. Group Learning Outcomes

Sau quá trình làm lab, nhóm rút ra một số nhận định chính:

1. **Chatbot va Agent khac nhau o co che grounding**
   Chatbot thuần LLM có thể nghe rất tự tin nhưng không bảo đảm bám dữ liệu. Agent tạo ra giá trị khi buộc mô hình phải tham chiếu tool trước khi kết luận.

2. **Khó nhất không phải là gọi được tool, mà là nối LLM với code một cách ổn định**
   Phần parser, format output và validation input quyết định rất lớn tới reliability.

3. **Observability là điều bắt buộc**
   Nếu không log từng bước Thought, Action, Observation thì gần như không thể phân tích agent fail ở đâu.

4. **Prompt engineering chỉ giải quyết một phần**
   Prompt tốt giúp mô hình ngoan hơn, nhưng nếu tool và data model chưa tốt thì hệ thống vẫn lỗi.

5. **Kiến trúc provider abstraction là hướng đi đúng**
   Việc tách riêng Gemini, OpenAI và local provider giúp code sạch hơn và tạo nền tảng cho mở rộng lâu dài.

---

> [!NOTE]
> Báo cáo này được viết lại theo hướng chi tiết hơn dựa trên mã nguồn hiện có trong repository, template chấm điểm của lab, và các số liệu final run nội bộ mà nhóm đã tổng hợp trước đó.
