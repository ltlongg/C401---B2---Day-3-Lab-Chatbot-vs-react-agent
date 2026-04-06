import os
import re
import time
from typing import List, Dict, Any
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


class ReActAgent:
    """
    Agent theo mô hình ReAct:
    Thought -> Action -> Observation -> ... -> Final Answer
    """

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5, timeout: float = 10.0):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.timeout = timeout
        self.history = []

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""
Bạn là một trợ lý thông minh hỗ trợ tra cứu điểm thi và trường đại học.

Bạn có các công cụ:
{tool_descriptions}

FORMAT BẮT BUỘC:

Thought: ...
Action: ten_tool(tham_so)

HOẶC:
Thought: ...
Action: ten_tool
Action Input: tham_so

Khi đủ thông tin:
Final Answer: ...

QUY TẮC:
- Mỗi lần chỉ 1 Action
- Không được bỏ Action nếu chưa có Final Answer
- Nếu input không rõ nghĩa, yêu cầu người dùng nhập lại
- Nếu cần dữ liệu thật, bắt buộc gọi tool
"""

    # =============================
    def _sanitize_input(self, text: str) -> str:
        """Làm sạch input (fix Case: Noisy Input)"""
        text = text.strip()
        text = re.sub(r"[^\w\sÀ-ỹ]", "", text) 
        return text

    def _normalize_args(self, args: str) -> str:
        """Normalize synonym (fix Case: CNTT vs Công nghệ thông tin)"""
        mapping = {
            "tin học": "Công nghệ thông tin",
            "it": "Công nghệ thông tin",
            "cntt": "Công nghệ thông tin"
        }

        args_lower = args.lower()
        for k, v in mapping.items():
            if k in args_lower:
                return v
        return args

    def _validate_args(self, tool_name: str, args: str):
        """Validate args trước khi gọi tool (fix Case: invalid input)"""
        if tool_name == "loc_truong_theo_diem":
            try:
                return float(args)
            except:
                return None
        return args

    # =============================
    def run(self, user_input: str) -> str:
        start_time = time.time()

        user_input = self._sanitize_input(user_input)

        if not user_input or len(user_input) < 3:
            return "Input không hợp lệ. Vui lòng nhập lại."

        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name
        })

        current_context = f"User: {user_input}"
        steps = 0
        total_tokens = 0
        execution_trace = []

        while steps < self.max_steps:

            # ===== Timeout check =====
            if time.time() - start_time > self.timeout:
                return "Hệ thống xử lý quá lâu, vui lòng thử lại."

            step_start = time.time()

            raw_result = self.llm.generate(
                current_context,
                system_prompt=self.get_system_prompt()
            )

            if isinstance(raw_result, dict):
                result_text = raw_result.get("content", "")
                usage = raw_result.get("usage", {})
            else:
                result_text = str(raw_result)
                usage = {}

            step_tokens = usage.get("total_tokens", 0)
            total_tokens += step_tokens

            print(f"\n--- Step {steps + 1} ---")
            print(result_text)

            # ===== Final Answer =====
            if "Final Answer:" in result_text:
                final_response = result_text.split("Final Answer:")[-1].strip()

                logger.log_event("AGENT_END", {
                    "steps": steps + 1,
                    "status": "success",
                    "latency": time.time() - start_time,
                    "total_tokens": total_tokens,
                    "trace": execution_trace
                })

                return final_response

            # ===== Parse =====
            thought_match = re.search(r"Thought:\s*(.*)", result_text)
            thought = thought_match.group(1).strip() if thought_match else result_text.strip()

            tool_name, tool_args, parse_mode = self._parse_action(result_text)

            step_log = {
                "step": steps + 1,
                "thought": thought,
                "action": None,
                "observation": None,
                "parse_mode": parse_mode
            }

            if tool_name:
                tool_args = self._normalize_args(tool_args)
                validated_args = self._validate_args(tool_name, tool_args)

                if validated_args is None:
                    observation = "Tham số không hợp lệ."
                else:
                    observation = self._execute_tool(tool_name, validated_args)

                step_log["action"] = {
                    "tool": tool_name,
                    "args": tool_args
                }
                step_log["observation"] = observation

                current_context += f"\n{result_text}\nObservation: {observation}"

            else:
                observation = "Không parse được Action."
                step_log["observation"] = observation
                current_context += f"\n{result_text}\nObservation: {observation}"

            execution_trace.append(step_log)
            logger.log_event("AGENT_STEP", step_log)

            steps += 1

        logger.log_event("AGENT_END", {
            "steps": steps,
            "status": "max_steps_reached"
        })

        return "Không thể tìm ra câu trả lời sau nhiều bước."

    # =============================
    def _parse_action(self, text: str):

        match_1 = re.search(r"Action:\s*(\w+)\((.*?)\)", text)
        if match_1:
            return (
                match_1.group(1),
                match_1.group(2).strip().strip("'").strip('"'),
                "format_1"
            )

        match_2 = re.search(r"Action:\s*(\w+)\s*\nAction Input:\s*(.*)", text)
        if match_2:
            return (
                match_2.group(1),
                match_2.group(2).strip().strip("'").strip('"'),
                "format_2"
            )

        return None, None, "fail"

    def _execute_tool(self, tool_name: str, args: str) -> str:
        database = [
            {"truong": "ĐH Bách Khoa", "nganh": "Công nghệ thông tin", "diem_chuan": 28.15},
            {"truong": "ĐH Kinh Tế Quốc Dân", "nganh": "Logistics", "diem_chuan": 27.0},
            {"truong": "ĐH Công Nghệ - ĐHQGHN", "nganh": "Công nghệ thông tin", "diem_chuan": 27.5},
            {"truong": "ĐH Giao Thông Vận Tải", "nganh": "Công nghệ thông tin", "diem_chuan": 24.5},
        ]

        if tool_name == "tra_cuu_diem":
            res = [d for d in database if args.lower() in d['nganh'].lower()]
            return str(res) if res else "Không tìm thấy dữ liệu ngành này."

        elif tool_name == "loc_truong_theo_diem":
            res = [d for d in database if d['diem_chuan'] <= float(args)]
            return str(res)

        return f"Công cụ '{tool_name}' không tồn tại."