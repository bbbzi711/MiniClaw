"""网页搜索工具 —— 通过 DuckDuckGo 搜索互联网，返回格式化结果。"""

import asyncio

from .base import Tool


class WebSearchTool(Tool):
    """用 DuckDuckGo 搜索互联网，返回搜索结果摘要。"""

    # ---- 元信息 ----

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "搜索互联网获取最新信息。"
            "当你需要查询实时信息、最新新闻或不确定的知识时使用。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回几条结果，默认 5",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    # ---- 执行逻辑 ----

    async def execute(self, query: str, max_results: int = 5) -> str:
        try:
            results = await asyncio.to_thread(_ddgs_search, query, max_results)
        except Exception as exc:
            return f"搜索出错: {exc}"

        if not results:
            return "未找到相关结果"

        output = "\n".join(results)

        max_chars = 8000
        if len(output) > max_chars:
            output = output[:max_chars] + "\n...(输出过长，已截断)"

        return output


def _ddgs_search(query: str, max_results: int) -> list[str]:
    """同步搜索函数，在线程池中执行以保持异步。"""
    from ddgs import DDGS

    lines: list[str] = []
    with DDGS() as ddgs:
        for i, result in enumerate(ddgs.text(query, max_results=max_results), 1):
            title = result.get("title", "无标题")
            href = result.get("href", "")
            body = result.get("body", "")
            lines.append(f"### {i}. {title}\n链接: {href}\n{body}\n")

    return lines
