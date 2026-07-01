"""OpenAI 兼容 Provider —— 对接 OpenAI / 硅基流动 / DeepSeek 等兼容 API。"""

import json

from openai import AsyncOpenAI

from .base import LLMProvider, LLMResponse, ToolCallRequest


class OpenAICompatProvider(LLMProvider):
    """OpenAI 协议兼容的 LLM 适配器。

    支持所有兼容 OpenAI Chat Completions 接口的 API（硅基流动、DeepSeek、Groq 等）。
    """

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """发送对话请求，自动处理 tool_calls / reasoning_content / usage。"""
        # ---- 构建请求参数 ----
        request_params: dict = {
            "model": model or self.model,
            "messages": messages,
        }

        # 仅在 tools 非空时才传入，避免部分厂商（硅基流动）报错
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"

        # ---- 调用 API ----
        try:
            response = await self._client.chat.completions.create(**request_params)
        except Exception as exc:
            return LLMResponse(
                content=f"API 调用失败：{exc}",
                finish_reason="error",
            )

        # ---- 解析响应 ----
        choice = response.choices[0]
        message = choice.message

        # 文本内容
        content: str | None = message.content

        # 工具调用 → ToolCallRequest 列表
        tool_calls: list[ToolCallRequest] = []
        if message.tool_calls:
            # 部分模型（如 Kimi-K2.5）把 reasoning_content 放在 message 顶层
            message_reasoning = getattr(message, "reasoning_content", None) or None

            for tc in message.tool_calls:
                # 解析 JSON 参数
                try:
                    arguments: dict = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}

                # 优先取 tool_call 级别的 reasoning_content，回退到 message 级别
                tc_reasoning = getattr(tc, "reasoning_content", None) or message_reasoning

                tool_calls.append(
                    ToolCallRequest(
                        id=tc.id or "",
                        name=tc.function.name,
                        arguments=arguments,
                        reasoning_content=tc_reasoning,
                    )
                )

        # Token 用量
        usage: dict = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
        )
