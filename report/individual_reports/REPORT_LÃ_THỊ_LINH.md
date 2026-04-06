# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Lã Thị Linh
- **Student ID**: 2A202600089
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

_Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.)._

- **Modules Implementated**: agent.py
- **Code Highlights**:
  '''
  def \_execute_tool(self, tool_name: str, args: str) -> str:
  """
  Thực thi các công cụ dựa trên tên.
  """ # Giả lập Database (Thay bằng database thật của bạn)
  database = [
  {"truong": "ĐH Bách Khoa", "nganh": "CNTT", "diem_chuan": 28.15},
  {"truong": "ĐH Kinh Tế Quốc Dân", "nganh": "Logistics", "diem_chuan": 27.0},
  {"truong": "ĐH Công Nghệ - ĐHQGHN", "nganh": "CNTT", "diem_chuan": 27.5},
  {"truong": "ĐH Giao Thông Vận Tải", "nganh": "CNTT", "diem_chuan": 24.5},
  ]

            if tool_name == "tra_cuu_diem":
                # Tìm ngành theo tên
                res = [d for d in database if args.lower() in d['nganh'].lower()]
                return str(res) if res else "Không tìm thấy dữ liệu ngành này."

            elif tool_name == "loc_truong_theo_diem":
                try:
                    diem_hs = float(args)
                    res = [d for d in database if d['diem_chuan'] <= diem_hs]
                    return str(res)
                except:
                    return "Lỗi: Tham số điểm phải là một số thực."

  '''

- **Documentation**:
  LLM sinh ra một Action theo định dạng:

Action: ten_tool(tham_so)
Agent sử dụng regex để trích xuất:
tool_name
args

Hàm \_execute_tool được gọi với các tham số này:

observation = self.\_execute_tool(tool_name, tool_args)

---

## II. Debugging Case Study (10 Points)

_Analyze a specific failure event you encountered during the lab using the logging system._

- **Problem Description**:
  Ngành CNTT điểm bao nhiêu?
  Cho tôi biết điểm CNTT
  CNTT có trường nào?
  Điểm CNTT của các trường là gì?
- **Log Source**:{"timestamp": "2026-04-06T08:55:58.309689", "event": "AGENT_START", "data": {"input": "Ngành CNTT lấy bao nhiêu điểm?", "model": "gemini-2.5-flash"}} {"timestamp": "2026-04-06T08:56:01.735923", "event": "AGENT_END", "data": {"steps": 2, "status": "success"}} {"timestamp": "2026-04-06T09:06:24.176181", "event": "AGENT_START", "data": {"input": "Cho tôi biết điểm CNTT", "model": "gemini-2.5-flash"}} {"timestamp": "2026-04-06T09:06:28.006251", "event": "AGENT_END", "data": {"steps": 2, "status": "success"}} {"timestamp": "2026-04-06T09:06:49.649105", "event": "AGENT_START", "data": {"input": "CNTT có trường nào?", "model": "gemini-2.5-flash"}} {"timestamp": "2026-04-06T09:06:59.834335", "event": "AGENT_END", "data": {"steps": 2, "status": "success"}} {"timestamp": "2026-04-06T09:07:19.979010", "event": "AGENT_START", "data": {"input": "Điểm CNTT của các trường là gì?", "model": "gemini-2.5-flash"}} {"timestamp": "2026-04-06T09:07:29.969209", "event": "AGENT_END", "data": {"steps": 2, "status": "success"}}
- **Diagnosis**: System prompt chưa đủ mạnh
  Không bắt buộc LLM phải follow đúng intent
  Không cấm hallucination
  Agent không validate output
  Chỉ cần có "Final Answer" là accept
  Không check xem có dùng tool hay không
  LLM drift context
  Do các câu trước đều liên quan CNTT → bị bias
- **Solution**: Nếu câu hỏi không chứa "điểm", "trường", "ngành" → skip tool

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

_Reflect on the reasoning capability difference._

1.  **Reasoning**:
    ReAct giúp:
    Chia nhỏ suy nghĩ (Thought)
    Quyết định rõ khi nào gọi tool
    So với chatbot:
    Chatbot: trả lời ngay (dễ sai)
    ReAct: có bước suy nghĩ → chính xác hơn khi cần data
    (Hiểu đơn giản Chatbot là một người giỏi nói(bịa giỏi), còn ReAct là một người vừa biết suy nghĩ vừa biết làm)

2.  **Reliability**: Một số case agent kém hơn chatbot:
    Khi input đơn giản:
    "Chào bạn"
    Agent vẫn cố follow format → dễ sai
    Khi tool hạn chế:
    "Công nghệ thông tin"
    Chatbot hiểu → agent fail do mismatch "CNTT"
3.  **Observation**:
    Là nguồn ground truth
    Giúp LLM không hallucinate

---

## IV. Future Improvements (5 Points)

_How would you scale this for a production-level AI agent system?_

- **Scalability**:
- **Safety**: Thêm validator layer:
  check format Action
  check hallucination
- **Performance**: Dùng Vector DB (FAISS, Chroma)

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
