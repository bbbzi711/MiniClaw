"""MiniClaw 入口 —— 组装 Agent 并启动交互式对话循环。"""

import asyncio
import sys

from .config import load_config
from .providers.openai_compat import OpenAICompatProvider
from .agent.tools.registry import ToolRegistry
from .agent.tools.filesystem import ReadFileTool, WriteFileTool, ListDirTool
from .agent.context import ContextBuilder
from .agent.loop import AgentLoop


BANNER = r"""
  __  __ _       _  ____ _
 |  \/  (_)     (_)/ ___| | __ ___      __
 | |\/| | |_ __  _| |   | |/ _` \ \ /\ / /
 | |  | | | '_ \| | |___| | (_| |\ V  V /
 |_|  |_|_| | | |_|\____|_|\__,_| \_/\_/
"""


def build_agent() -> AgentLoop:
    """组装 Agent：加载配置 → 创建 Provider / Tools / Context → 返回 AgentLoop。"""
    # 1. 加载配置
    config = load_config()

    # 2. 检查 API Key
    if not config.api_key:
        print("错误：未设置 API Key。请在 config.json 中填写 api_key 或设置环境变量 NANOCLAW_API_KEY。")
        sys.exit(1)

    # 3. 创建 Provider
    provider = OpenAICompatProvider(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
    )

    # 4. 创建 ToolRegistry 并注册文件系统工具
    tools = ToolRegistry()
    tools.register(ReadFileTool(config.workspace))
    tools.register(WriteFileTool(config.workspace))
    tools.register(ListDirTool(config.workspace))

    # 5. 创建 ContextBuilder
    context = ContextBuilder(config.workspace, config.identity_file)

    # 6. 组装 AgentLoop
    agent = AgentLoop(
        provider=provider,
        tools=tools,
        context=context,
        model=config.model,
        max_iterations=config.max_iterations,
    )

    # 7. 打印已注册的工具列表
    print(f"已注册工具：{tools.list_tools()}")

    return agent


async def interactive_loop(agent: AgentLoop) -> None:
    """交互式对话主循环。

    支持命令：
        /exit   — 退出程序
        /clear  — 清空对话历史
        /tools  — 查看已注册工具列表
    其他输入将作为对话消息发送给 Agent。
    """
    print("输入消息开始对话，/exit 退出，/clear 清空历史，/tools 查看可用工具。\n")

    while True:
        try:
            user_input = input(">>> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if not user_input:
            continue

        # ---- 内置命令 ----
        if user_input == "/exit":
            print("再见！")
            break

        if user_input == "/clear":
            agent.clear_history()
            print("对话历史已清空。")
            continue

        if user_input == "/tools":
            names = agent.tools.list_tools()
            if names:
                print(f"可用工具：{names}")
            else:
                print("没有已注册的工具。")
            continue

        # ---- 正常对话 ----
        try:
            reply = await agent.run(user_input)
            print(f"\n{reply}\n")
        except Exception as exc:
            print(f"\n运行异常：{exc}\n")


def main() -> None:
    """MiniClaw 入口函数。"""
    print(BANNER)
    print("MiniClaw Agent — 类小龙虾 AI 助手\n")

    agent = build_agent()
    asyncio.run(interactive_loop(agent))


if __name__ == "__main__":
    main()
