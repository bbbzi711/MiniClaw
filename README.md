# MiniClaw 🦞

一个基于 LLM 的轻量 AI Agent 框架，名字取自"小龙虾"的英文。核心链路简洁清晰：**用户输入 → AgentLoop → LLM Provider → Tool 执行 → 循环 → 返回结果**。

## 特性

- **插件式 Provider** — 抽象 `LLMProvider` 基类，目前已实现 OpenAI 兼容协议（硅基流动、DeepSeek、Groq 等），可轻松扩展 Anthropic、Ollama 等
- **Function Calling 工具系统** — `Tool` 抽象基类 + `ToolRegistry`，支持任意工具注册，内置文件读写/目录列表工具
- **防死循环熔断** — 滑动窗口检测同一工具+同一参数的重复调用，≥10 次警告跳过，≥20 次强制终止
- **可编辑人设** — 通过 `identity.md` 自定义 Agent 的角色、性格和回复风格
- **跨轮对话记忆** — 会话历史在 `/clear` 前持续累积
- **src layout** — 使用 `uv` 管理依赖，标准 Python 项目结构

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url> && cd MiniClaw

# 2. 同步依赖（自动创建虚拟环境 + 可编辑安装）
uv sync

# 3. 创建配置
cp config.example.json config.json
# 编辑 config.json，填入你的 API Key

# 4. 启动
uv run miniclaw
```

## 配置

创建 `config.json`（已加入 `.gitignore`，不会提交到仓库）：

```json
{
    "api_key": "sk-xxxxx",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Pro/moonshotai/Kimi-K2.5",
    "workspace": ".",
    "max_iterations": 32,
    "identity_file": "identity.md"
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `api_key` | API 密钥，也可通过环境变量 `MINICLAW_API_KEY` 覆盖（优先级更高） | — |
| `base_url` | API 地址 | `https://api.siliconflow.cn/v1` |
| `model` | 模型名称 | `Pro/moonshotai/Kimi-K2.5` |
| `workspace` | 文件工具的工作目录 | `.` |
| `max_iterations` | 单轮最大工具调用次数 | `32` |
| `identity_file` | 人设文件路径 | `identity.md` |

## 项目结构

```
MiniClaw/
├── src/miniclaw/              # 源代码
│   ├── main.py                # 入口：组装 Agent + 交互式 CLI
│   ├── config.py              # 配置 dataclass + 加载逻辑
│   ├── agent/
│   │   ├── loop.py            # AgentLoop 主循环（核心）
│   │   ├── context.py         # 上下文构建（system prompt + 记忆）
│   │   └── tools/
│   │       ├── base.py        # Tool 抽象基类
│   │       ├── registry.py    # ToolRegistry 注册/调度
│   │       └── filesystem.py  # 文件系统工具（读/写/列目录）
│   └── providers/
│       ├── base.py            # LLMProvider 抽象基类 + 数据模型
│       └── openai_compat.py   # OpenAI 兼容协议实现
├── memory/                    # 长期记忆（可选）
│   └── MEMORY.md
├── identity.md                # Agent 人设
├── config.example.json        # 配置模板（可提交）
├── config.json                # 用户配置（不提交到 git）
├── pyproject.toml             # 项目元数据 + 依赖
├── uv.lock                    # 依赖锁文件
└── CLAUDE.md                  # Claude Code 指引
```

## 架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  main.py     │────▶│  AgentLoop   │────▶│  Provider    │
│  (CLI 交互)  │◀────│  (主循环)     │◀────│  (LLM API)   │
└──────────────┘     └──────┬───────┘     └──────────────┘
                             │
                      ┌──────▼───────┐
                      │  ToolRegistry │
                      │  (工具调度)    │
                      └──────┬───────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
        │ ReadFile  │ │ WriteFile │ │ ListDir   │
        └───────────┘ └───────────┘ └───────────┘
```

每轮对话流程：

1. `ContextBuilder` 拼接 system prompt + 历史 + 当前输入 → messages
2. `Provider.chat(messages, tools)` 发请求
3. 有 `tool_calls` → `ToolRegistry.execute()` 逐个执行 → 结果回填 messages → 回到步骤 2
4. 无 `tool_calls` → 返回最终回复，保存历史

## 扩展

### 添加工具

```python
from miniclaw.agent.tools.base import Tool

class ShellTool(Tool):
    name = "shell"
    description = "执行 Shell 命令并返回输出"
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的命令"}
        },
        "required": ["command"],
    }

    async def execute(self, command: str) -> str:
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout or result.stderr
```

然后在 `main.py` 的 `build_agent()` 中注册：

```python
tools.register(ShellTool())
```

### 添加 Provider

继承 `LLMProvider` 并实现 `chat()` 方法即可，参考 `OpenAICompatProvider`。

## 内置命令

| 命令 | 功能 |
|------|------|
| `/exit` | 退出程序 |
| `/clear` | 清空对话历史 |
| `/tools` | 查看已注册的工具列表 |

## License

MIT
