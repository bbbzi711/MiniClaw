"""网页抓取工具 —— 抓取指定 URL 的网页内容，转换为纯文本返回。"""

import re
from urllib.parse import urlparse

import httpx
import html2text

from .base import Tool


class WebFetchTool(Tool):
    """抓取指定 URL 的网页内容，HTML → 纯文本。"""

    # ---- 元信息 ----

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return (
            "抓取指定 URL 的网页内容。"
            "当你需要阅读某个具体网页的详细内容时使用。"
            "通常配合 web_search 工具先搜索再抓取。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要抓取的网页 URL",
                },
            },
            "required": ["url"],
        }

    # ---- 执行逻辑 ----

    async def execute(self, url: str) -> str:
        # 1. URL 安全检查
        try:
            parsed = urlparse(url)
        except Exception:
            return "URL 格式无效，无法解析"

        if parsed.scheme not in ("http", "https"):
            return "安全拦截：只允许 http/https 协议"

        if not parsed.netloc:
            return "URL 格式无效：缺少主机名"

        # 2. 发送 HTTP GET 请求
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                },
            ) as client:
                response = await client.get(url)
        except httpx.TimeoutException:
            return "抓取失败：请求超时（15 秒）"
        except httpx.ConnectError:
            return "抓取失败：无法连接到目标服务器"
        except Exception as exc:
            return f"抓取失败：{exc}"

        if response.status_code < 200 or response.status_code >= 300:
            return f"抓取失败：HTTP {response.status_code}"

        # 3. HTML → 纯文本
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return f"抓取失败：不支持的内容类型 ({content_type})"

        try:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0
            text = h.handle(response.text)
        except Exception as exc:
            return f"内容转换失败：{exc}"

        # 4. 清理输出
        text = re.sub(r"\n{3,}", "\n\n", text)

        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...(内容过长，已截断)"

        return text
