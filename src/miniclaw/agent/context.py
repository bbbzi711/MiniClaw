"""上下文构建器 —— 拼接 System Prompt、历史对话与当前消息。"""

import os
from datetime import datetime


class ContextBuilder:
    """负责从人设文件、工作区信息、长期记忆中构建完整的对话上下文。

    使用示例::

        ctx = ContextBuilder(workspace="/home/user/project")
        messages = ctx.build_messages(history=prev_msgs, current_message="帮我重构这段代码")
    """

    def __init__(self, workspace: str, identity_file: str = "identity.md") -> None:
        self.workspace = workspace
        self.identity_file = identity_file

    # ---- 私有加载方法 ----

    def _load_identity(self) -> str:
        """读取人设文件内容，文件不存在时返回默认人设。"""
        path = os.path.join(self.workspace, self.identity_file)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return "你是一个乐于助人的 AI 助手。请用中文回答用户问题。"

    def _load_memory(self) -> str:
        """读取长期记忆文件，不存在则返回空字符串。"""
        path = os.path.join(self.workspace, "memory", "MEMORY.md")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    # ---- 公共构建方法 ----

    def build_system_prompt(self) -> str:
        """拼接完整的 System Prompt。"""
        identity = self._load_identity()
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        memory = self._load_memory()

        parts: list[str] = [identity]

        parts.append(
            f"\n\n## 当前环境\n"
            f"- 当前时间：{now}\n"
            f"- 工作区路径：{self.workspace}"
        )

        if memory:
            parts.append(f"\n\n## 长期记忆\n{memory}")

        return "".join(parts)

    def build_messages(
        self,
        history: list[dict] | None = None,
        current_message: str = "",
    ) -> list[dict]:
        """构建完整的 messages 列表。

        顺序：System Prompt → 历史对话 → 当前用户消息。

        参数
        ----
        history : 历史对话列表，格式 [{"role": "...", "content": "..."}, ...]
        current_message : 当前用户输入
        """
        messages: list[dict] = [
            {"role": "system", "content": self.build_system_prompt()},
        ]

        if history:
            messages.extend(history)

        if current_message:
            messages.append({"role": "user", "content": current_message})

        return messages
