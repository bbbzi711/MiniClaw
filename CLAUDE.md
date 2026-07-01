# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在本仓库工作时提供指引。

## 常用命令

```bash
uv sync             # 同步依赖 + 可编辑安装
uv run miniclaw     # 启动交互式 Agent
uv add <package>    # 添加依赖
uv lock --upgrade   # 更新锁文件
```

尚无测试和 lint 配置。

## 架构

MiniClaw 是一个基于 LLM 的 AI Agent 框架，核心链路：**用户输入 → AgentLoop → LLM Provider → Tool 执行 → 循环 → 返回结果**。

### 装配流程（main.py）

```
load_config() → OpenAICompatProvider + ToolRegistry + ContextBuilder → AgentLoop → interactive_loop()
```

- `build_agent()` 负责把所有组件组装起来，`interactive_loop()` 只负责读输入、调 `agent.run()`、打印结果。
- 内置命令 `/exit`、`/clear`、`/tools` 在 interactive_loop 层处理，不走 LLM。

### 配置（config.py）

`MiniClawConfig` dataclass 存放所有运行参数。`load_config("config.json")` 三层优先级：

1. dataclass 默认值（兜底）
2. JSON 文件覆盖
3. `MINICLAW_API_KEY` 环境变量（最高优先级）

### Provider 层（providers/）

- `LLMProvider` — 抽象基类，`chat(messages, tools, model) -> LLMResponse`
- `OpenAICompatProvider` — 对接硅基流动等 OpenAI 兼容 API，使用 `AsyncOpenAI`，自动处理 tool_calls / reasoning_content / usage 解析
- `LLMResponse` 包含 `content`、`tool_calls`（`ToolCallRequest` 列表）、`finish_reason`、`usage`

### Agent 主循环（agent/loop.py）

`AgentLoop.run(user_message)` 的核心逻辑：

1. `ContextBuilder.build_messages()` 构建完整 messages（system prompt + 历史 + 当前输入）
2. 向 Provider 发起 chat，拿到 `LLMResponse`
3. 有 `tool_calls` → 逐个执行工具，结果以 `role: "tool"` 回填 messages → 回到步骤 2
4. 无 `tool_calls` → 保存增量到 `_session_history`，返回 `content`
5. 超过 `max_iterations` 自动截断

**防死循环**：`_check_tool_loop()` 用滑动窗口（最近 30 次）检测同一工具+同一参数是否被反复调用。≥10 次警告跳过，≥20 次直接熔断终止。

### 工具系统（agent/tools/）

- `Tool` 抽象基类：`name` / `description` / `parameters`（JSON Schema）/ `execute(**kwargs) -> str`
- `to_function_definition()` 生成 OpenAI function-calling 格式
- `ToolRegistry`：`register()` 注册、`get_definitions()` 生成 tools 数组、`execute(name, arguments)` 调度
- 当前已实现：`ReadFileTool`、`WriteFileTool`、`ListDirTool`
- 所有文件工具通过 `_resolve_safe_path()` 做 workspace 沙箱校验，禁止路径穿越

### 上下文构建（agent/context.py）

`ContextBuilder` 从三个来源拼接 system prompt：

1. `identity.md`（人设文件，不存在则用默认人设）
2. 当前时间 + 工作区路径
3. `memory/MEMORY.md`（长期记忆，可选）
