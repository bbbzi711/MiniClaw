"""Agent 主循环 —— 驱动 LLM ↔ Tool 的交互，含防死循环熔断机制。"""

import json

from ..providers.base import LLMProvider
from .tools.registry import ToolRegistry
from .context import ContextBuilder


class AgentLoop:
    """Agent 运行主循环。

    每轮：LLM 响应 → 有 tool_calls 则执行工具并回填结果 → 继续
                     → 无 tool_calls 则保存历史并返回最终回复

    内置滑动窗口防爆检测：同一工具+同一参数短时间重复调用 ≥10 次警告，≥20 次熔断。
    """

    def __init__(
        self,
        provider: LLMProvider,
        tools: ToolRegistry,
        context: ContextBuilder,
        model: str | None = None,
        max_iterations: int = 32,
    ) -> None:
        self.provider = provider
        self.tools = tools
        self.context = context
        self.model = model
        self.max_iterations = max_iterations

        # 内部状态
        self._tool_call_history: list[str] = []   # 滑动窗口（工具调用签名）
        self._session_history: list[dict] = []     # 跨轮对话历史
        self._round_start_idx: int = 0             # 本轮初始 messages 长度

    # ---- 核心方法 ----

    async def run(self, user_message: str) -> str:
        """执行一轮对话，返回最终回复文本。"""
        # 1. 构建初始 messages
        messages = self.context.build_messages(
            history=self._session_history,
            current_message=user_message,
        )
        self._round_start_idx = len(messages)

        # 2. 工具定义（只取一次，循环中不变）
        tools_defs = self.tools.get_definitions()

        # 3. 主循环
        for _ in range(self.max_iterations):
            response = await self.provider.chat(messages, tools_defs, self.model)

            # a. API 调用失败
            if response.finish_reason == "error":
                return response.content or "API 调用失败，未知错误。"

            # b. 模型要求调用工具
            if response.has_tool_calls:
                # 构造 assistant 消息（含 tool_calls）
                assistant_msg = self._build_assistant_message(response)
                messages.append(assistant_msg)

                # 逐个执行工具
                for tc in response.tool_calls:
                    args_json = json.dumps(tc.arguments, sort_keys=True, ensure_ascii=False)

                    # 防爆检测
                    verdict = self._check_tool_loop(tc.name, args_json)
                    if verdict is not None:
                        if verdict.startswith("熔断"):
                            return verdict  # 直接终止
                        # 警告 → 跳过执行，注入 SYSTEM_ERROR
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": verdict,
                        })
                        continue

                    # 正常执行
                    result = await self.tools.execute(tc.name, tc.arguments)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                continue  # 回到循环顶部，让模型处理工具结果

            # c. 模型直接回复（无 tool_calls）
            self._save_to_history(messages)
            return response.content or ""

        # 4. 超过最大迭代次数
        return f"已达到最大对话轮次（{self.max_iterations}），请简化问题后重试。"

    # ---- 防爆检测 ----

    def _check_tool_loop(self, tool_name: str, tool_args_json: str) -> str | None:
        """滑动窗口检测同一工具+同一参数是否被反复调用。

        返回
        ----
        None  → 放行，正常执行
        str   → 警告或熔断消息（调用方应注入 tool 角色消息或直接终止）
        """
        signature = f"{tool_name}:{tool_args_json}"
        count = self._tool_call_history.count(signature)

        if count >= 20:
            return (
                f"熔断：工具 '{tool_name}' 使用相同参数连续调用了 {count} 次，"
                f"判定为死循环，已强制终止。"
            )

        if count >= 10:
            return (
                f"SYSTEM_ERROR: 工具 '{tool_name}' 已使用相同参数调用了 {count} 次，"
                f"本次执行被跳过以避免死循环。请换一种方式完成任务。"
            )

        # 正常放行：记录签名，维护窗口上限
        self._tool_call_history.append(signature)
        if len(self._tool_call_history) > 30:
            self._tool_call_history.pop(0)

        return None

    # ---- 辅助方法 ----

    def _build_assistant_message(self, response) -> dict:
        """将 LLMResponse 中的 tool_calls 转为 OpenAI 格式的 assistant 消息。

        ⚠️ 绝对不能把 reasoning_content 放入 tool_calls 数组元素中 ——
        硅基流动等 API 遇到未知字段会报 error code 20015。
        reasoning_content 只能放在 assistant 消息顶层。
        """
        tool_calls: list[dict] = []
        for tc in response.tool_calls:
            tool_calls.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                },
            })

        msg: dict = {
            "role": "assistant",
            "content": response.content or "",
            "tool_calls": tool_calls,
        }

        # reasoning_content 放在消息顶层，不在 tool_calls 元素内
        if response.tool_calls and response.tool_calls[0].reasoning_content:
            msg["reasoning_content"] = response.tool_calls[0].reasoning_content

        return msg

    def _save_to_history(self, messages_snapshot: list[dict]) -> None:
        """将本轮新增的消息（assistant + tool 结果）保存到跨轮会话历史。"""
        new_msgs = messages_snapshot[self._round_start_idx:]
        self._session_history.extend(new_msgs)

    def clear_history(self) -> None:
        """清空所有内部状态（工具调用记录 + 会话历史）。"""
        self._tool_call_history.clear()
        self._session_history.clear()
