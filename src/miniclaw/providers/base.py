"""Provider 基类与数据模型 —— 定义 LLM 交互的核心数据结构与抽象接口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ---- 数据模型 ----

@dataclass
class ToolCallRequest:
    """单次工具调用请求，由模型生成。

    reasoning_content 用于保存支持"思考"的模型（如 Kimi-K2.5、DeepSeek-R1）
    在 tool_calls 中附带的推理过程，后续需要透传回对话。
    """

    id: str
    name: str
    arguments: dict
    reasoning_content: str | None = None


@dataclass
class LLMResponse:
    """一次 LLM 调用的完整响应。

    content 为模型文本输出（纯对话时为正文，tool_calls 时可能为空）。
    """

    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


# ---- 抽象基类 ----

class LLMProvider(ABC):
    """LLM 提供者抽象基类。所有模型适配器（OpenAI、Anthropic 等）均由此派生。"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """
        发送对话消息，返回统一格式的 LLMResponse。

        参数
        ----
        messages : 对话历史，格式为 [{"role": "...", "content": "..."}, ...]
        tools : 可选的工具定义列表（function calling JSON Schema）
        model : 可选的模型名，允许调用方覆盖默认模型
        """
        ...
