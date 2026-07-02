"""Shell 命令执行工具 —— 在工作区目录下执行命令，内置危险命令拦截和超时保护。"""

import asyncio
import os
import re
import subprocess

from .base import Tool

# ---- 危险命令正则模式列表 ----

DENY_PATTERNS = [
    r"rm\s+.*-r",            # 递归删除（rm -r / rm -rf）
    r"rm\s+-rf",             # rm -rf 强制递归删除
    r"rmdir\s+/s",           # Windows 递归删除目录
    r"format\s+",            # 格式化磁盘
    r"mkfs",                 # Linux 格式化文件系统
    r"shutdown",             # 关机
    r"reboot",               # 重启
    r"sudo\s+",              # sudo 权限提升
    r"\bsu\b",               # su 切换用户
    r"chmod\s+777",          # 危险权限修改
    r">\s*/dev/",            # 覆盖设备文件
    r"wget\s+.*\|\s*sh",     # 下载并通过 sh 执行（管道注入）
    r"curl\s+.*\|\s*bash",   # 下载并通过 bash 执行（管道注入）
    r"nc\s+-l",              # netcat 监听模式（后门）
    r"ncat\s+-l",            # ncat 监听模式（后门）
    r"dd\s+if=",             # dd 磁盘镜像覆写
    r":\(\)\{.*\}",          # Fork 炸弹
]


class ExecTool(Tool):
    """在工作区目录下执行 Shell 命令，内置安全拦截、超时保护和输出截断。"""

    def __init__(self, workspace: str = ".") -> None:
        self.workspace = os.path.abspath(workspace)

    # ---- 元信息 ----

    @property
    def name(self) -> str:
        return "exec"

    @property
    def description(self) -> str:
        return (
            "在工作区目录下执行 Shell 命令并返回输出结果。"
            "60 秒超时，输出超过 10000 字符自动截断。"
            "危险命令（如 rm -rf、sudo、格式化等）会被拦截。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要在工作区目录下执行的 Shell 命令",
                },
            },
            "required": ["command"],
        }

    # ---- 安全检查 ----

    @staticmethod
    def _is_dangerous(command: str) -> str | None:
        """检查命令是否命中危险模式，命中返回拦截信息，否则返回 None。"""
        for pattern in DENY_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return f"安全拦截：检测到危险命令模式 '{pattern}'"
        return None

    # ---- 执行逻辑 ----

    async def execute(self, command: str) -> str:
        # 1. 安全检查
        dangerous = self._is_dangerous(command)
        if dangerous is not None:
            return dangerous

        # 2. 创建子进程
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.workspace,
            )
        except Exception as exc:
            return f"错误：无法创建子进程 —— {exc}"

        # 3. 等待执行（60 秒超时）
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=60
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return "命令执行超时（60秒），已终止"

        # 4. 拼接输出
        output = stdout_bytes.decode("utf-8", errors="replace")

        if stderr_bytes:
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")
            output += f"\n标准错误:\n{stderr_text}"

        # 5. 截断过长输出
        max_chars = 10000
        if len(output) > max_chars:
            output = output[:max_chars] + "\n...(输出过长，已截断)"

        # 6. 附加退出码
        returncode = proc.returncode if proc.returncode is not None else -1
        output += f"\n[退出码: {returncode}]"

        return output
