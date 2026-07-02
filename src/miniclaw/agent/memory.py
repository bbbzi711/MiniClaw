"""记忆压缩器 —— 当对话历史超过 Token 预算时，用 LLM 摘要压缩旧消息。"""

import json
import os
from datetime import datetime

from ..providers.base import LLMProvider


class MemoryConsolidator:
    """监控对话历史的 Token 用量，超预算时调用 LLM 将旧消息压缩为摘要。

    使用示例::

        consolidator = MemoryConsolidator(provider, "/workspace")
        compact = await consolidator.maybe_consolidate(messages)
    """

    def __init__(
        self,
        provider: LLMProvider,
        workspace: str,
        token_budget: int = 6000,
    ) -> None:
        self.provider = provider
        self.workspace = workspace
        self.token_budget = token_budget

    # ---- Token 估算 ----

    @staticmethod
    def estimate_tokens(messages: list[dict]) -> int:
        """粗略估算消息列表的 Token 数。

        规则：len(json.dumps(msg)) // 2，经验值，约等于英文 token 数。
        """
        total = 0
        for msg in messages:
            total += len(json.dumps(msg, ensure_ascii=False)) // 2
        return total

    # ---- 主入口 ----

    async def maybe_consolidate(self, messages: list[dict]) -> list[dict]:
        """检查 Token 用量，超预算时压缩旧消息。

        压缩策略：
        - 保留第一条（system prompt）和最后 6 条不动
        - 中间的旧消息用 LLM 生成一份摘要
        - 摘要写入 workspace/memory/HISTORY.md
        - 返回压缩后的 messages

        未超预算时直接返回原列表。
        """
        if self.estimate_tokens(messages) <= self.token_budget:
            return messages

        # 第一条不动（通常是 system prompt），最后 6 条不动
        if len(messages) <= 7:
            return messages  # 太少，没法压缩

        head = messages[:1]
        tail = messages[-6:]
        old_messages = messages[1:-6]

        if not old_messages:
            return messages

        # 生成摘要
        summary = await self._summarize(old_messages)

        # 写入 HISTORY.md
        self._save_to_history(summary, len(old_messages))

        # 组装压缩后的消息
        summary_msg = {
            "role": "system",
            "content": f"[历史摘要]: {summary}",
        }
        return head + [summary_msg] + tail

    # ---- 内部方法 ----

    async def _summarize(self, messages: list[dict]) -> str:
        """调用 LLM 将旧消息压缩为 3-5 句摘要。"""
        # 拼接旧消息文本
        lines: list[str] = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                lines.append(f"[{role}]: {content}")
        conversation_text = "\n".join(lines)

        prompt = [
            {
                "role": "system",
                "content": (
                    "请用 3-5 句话概括以下对话的关键信息，保留重要的事实和结论，"
                    "省略过程细节和寒暄。只输出摘要，不要其他内容。"
                ),
            },
            {
                "role": "user",
                "content": f"请概括以下对话：\n\n{conversation_text}",
            },
        ]

        try:
            response = await self.provider.chat(prompt, tools=None)
            return (response.content or "（摘要生成失败，旧消息已丢弃）").strip()
        except Exception:
            return "（摘要生成失败，旧消息已丢弃）"

    def _save_to_history(self, summary: str, original_count: int) -> None:
        """将摘要追加写入 workspace/memory/HISTORY.md。"""
        memory_dir = os.path.join(self.workspace, "workspace", "memory")
        os.makedirs(memory_dir, exist_ok=True)

        filepath = os.path.join(memory_dir, "HISTORY.md")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"## {now}\n"
            f"压缩了 {original_count} 条旧消息\n\n"
            f"{summary}\n\n"
            f"---\n"
        )

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)
