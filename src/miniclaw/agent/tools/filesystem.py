"""文件系统工具 —— ReadFile / WriteFile / ListDir，均限制在 workspace 内操作。"""

import os

from .base import Tool


# ---- 安全工具函数 ----

def _resolve_safe_path(workspace: str, user_path: str) -> str | None:
    """将用户输入路径解析为绝对路径，通过 workspace 边界检查则返回，否则返回 None。"""
    workspace_abs = os.path.abspath(workspace)
    target_abs = os.path.abspath(os.path.join(workspace_abs, user_path))

    # 用 os.sep 后缀防止 /workspace2 误匹配 /workspace
    if not target_abs.startswith(workspace_abs + os.sep) and target_abs != workspace_abs:
        return None

    return target_abs


# ---- 读文件 ----

class ReadFileTool(Tool):
    """读取工作区内指定文件的内容，超过 16000 字符自动截断。"""

    def __init__(self, workspace: str) -> None:
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "读取工作区内指定路径的文件内容，返回文本。超过 16000 字符时截断并提示。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "相对于工作区根目录的文件路径，例如 'src/main.py'",
                },
            },
            "required": ["file_path"],
        }

    async def execute(self, file_path: str) -> str:
        resolved = _resolve_safe_path(self.workspace, file_path)
        if resolved is None:
            return f"错误：路径 '{file_path}' 不在工作区内，操作被拦截。"

        if not os.path.exists(resolved):
            return f"错误：文件 '{file_path}' 不存在。"

        if not os.path.isfile(resolved):
            return f"错误：'{file_path}' 不是文件。"

        try:
            with open(resolved, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

        max_chars = 16000
        if len(content) > max_chars:
            content = content[:max_chars] + (
                f"\n\n... [输出截断：共 {len(content)} 字符，仅展示前 {max_chars} 字符]"
            )

        return content


# ---- 写文件 ----

class WriteFileTool(Tool):
    """向工作区内写入文件，自动创建父目录。"""

    def __init__(self, workspace: str) -> None:
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "向工作区内指定路径写入文件内容，会自动创建不存在的父目录。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "相对于工作区根目录的文件路径，例如 'output/result.txt'",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的文本内容",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(self, file_path: str, content: str) -> str:
        resolved = _resolve_safe_path(self.workspace, file_path)
        if resolved is None:
            return f"错误：路径 '{file_path}' 不在工作区内，操作被拦截。"

        os.makedirs(os.path.dirname(resolved), exist_ok=True)

        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)

        return f"已写入：{file_path}"


# ---- 列目录 ----

class ListDirTool(Tool):
    """列出工作区内指定目录的内容。"""

    def __init__(self, workspace: str) -> None:
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "list_dir"

    @property
    def description(self) -> str:
        return "列出工作区内指定目录的内容，显示文件大小，目录以 / 结尾，按名称排序。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "相对于工作区根目录的路径，例如 '.' 或 'src'，默认为根目录",
                },
            },
            "required": [],
        }

    async def execute(self, dir_path: str = ".") -> str:
        resolved = _resolve_safe_path(self.workspace, dir_path)
        if resolved is None:
            return f"错误：路径 '{dir_path}' 不在工作区内，操作被拦截。"

        if not os.path.exists(resolved):
            return f"错误：目录 '{dir_path}' 不存在。"

        if not os.path.isdir(resolved):
            return f"错误：'{dir_path}' 不是目录。"

        try:
            entries = os.listdir(resolved)
        except PermissionError:
            return f"错误：没有权限访问目录 '{dir_path}'。"

        if not entries:
            return f"目录 '{dir_path}' 为空。"

        lines: list[str] = []
        for name in sorted(entries):
            full = os.path.join(resolved, name)
            if os.path.isdir(full):
                lines.append(f"{name}/")
            else:
                size = os.path.getsize(full)
                lines.append(f"{name}  ({_format_size(size)})")

        return "\n".join(lines)


def _format_size(size: int) -> str:
    """将字节数格式化为人类可读的大小字符串。"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"
