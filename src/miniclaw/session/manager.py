"""会话持久化管理 —— 以 JSONL 文件存储对话历史，支持跨轮恢复。"""

import json
import os
from datetime import datetime, timezone


class SessionManager:
    """管理对话会话的持久化存储。

    每个 session 对应一个 .jsonl 文件，每行一条消息（含 timestamp）。
    读取时自动去掉 timestamp 字段，兼容 OpenAI API 格式。

    使用示例::

        mgr = SessionManager("workspace/sessions")
        mgr.save_message("cli:direct", {"role": "user", "content": "你好"})
        history = mgr.get_history("cli:direct")  # → [{role: user, content: 你好}, ...]
    """

    def __init__(self, sessions_dir: str = "workspace/sessions") -> None:
        self.sessions_dir = sessions_dir
        os.makedirs(self.sessions_dir, exist_ok=True)

    # ---- 内部工具 ----

    def _get_session_path(self, session_key: str) -> str:
        """将 session_key 转为安全的文件路径。

        "cli:direct" → "workspace/sessions/cli_direct.jsonl"
        """
        safe_name = session_key.replace(":", "_")
        return os.path.join(self.sessions_dir, f"{safe_name}.jsonl")

    # ---- 公共方法 ----

    def save_message(self, session_key: str, message: dict) -> None:
        """追加一条消息到指定会话的 JSONL 文件末尾。

        自动添加 timestamp 字段（ISO 8601 格式）。
        """
        record = dict(message)
        record["timestamp"] = datetime.now(timezone.utc).isoformat()

        filepath = self._get_session_path(session_key)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_history(self, session_key: str) -> list[dict]:
        """读取指定会话的完整对话历史。

        返回的消息列表中已去掉 timestamp 字段（OpenAI API 不识别）。
        文件不存在时返回空列表。
        """
        filepath = self._get_session_path(session_key)
        if not os.path.isfile(filepath):
            return []

        messages: list[dict] = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # 去掉 timestamp，OpenAI API 不认识它
                record.pop("timestamp", None)
                messages.append(record)

        return messages

    def clear(self, session_key: str) -> None:
        """删除指定会话的 JSONL 文件。"""
        filepath = self._get_session_path(session_key)
        if os.path.isfile(filepath):
            os.remove(filepath)

    def list_sessions(self) -> list[str]:
        """列出所有已存在的会话 key。"""
        if not os.path.isdir(self.sessions_dir):
            return []

        sessions: list[str] = []
        for filename in sorted(os.listdir(self.sessions_dir)):
            if not filename.endswith(".jsonl"):
                continue
            # 还原 session_key：cli_direct.jsonl → cli:direct
            stem = filename[:-6]  # 去掉 ".jsonl"
            session_key = stem.replace("_", ":")
            sessions.append(session_key)

        return sessions
