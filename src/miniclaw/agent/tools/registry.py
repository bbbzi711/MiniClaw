"""工具注册中心 —— 统一管理所有 Tool，提供注册、查询、执行调度。"""

from .base import Tool


class ToolRegistry:
    """工具注册表，内部用 dict[str, Tool] 存储，负责工具的增、查、执行。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    # ---- 注册 ----

    def register(self, tool: Tool) -> None:
        """注册一个工具实例，以 tool.name 为 key 存入。"""
        self._tools[tool.name] = tool

    # ---- 查询 ----

    def list_tools(self) -> list[str]:
        """返回所有已注册工具的名称列表。"""
        return list(self._tools.keys())

    def get_definitions(self) -> list[dict]:
        """遍历所有工具，调用各自的 to_function_definition()，返回 JSON 定义列表。"""
        return [tool.to_function_definition() for tool in self._tools.values()]

    # ---- 执行 ----

    async def execute(self, name: str, arguments: dict) -> str:
        """根据工具名查找并执行。找不到或执行出错时返回错误信息字符串。"""
        tool = self._tools.get(name)
        if tool is None:
            return f"错误：未找到工具 '{name}'，当前可用工具：{self.list_tools()}"

        try:
            return await tool.execute(**arguments)
        except Exception as exc:
            return f"错误：执行工具 '{name}' 时异常：{exc}"

    # ---- dunder ----

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.list_tools()}>"

    def __contains__(self, name: str) -> bool:
        """支持 'name' in registry 的成员检查。"""
        return name in self._tools
