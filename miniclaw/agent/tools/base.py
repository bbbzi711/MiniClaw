"""Tool 抽象基类 —— 所有工具的模具，统一接口：声明 → 注册 → 调用。"""

from abc import ABC, abstractmethod


class Tool(ABC):
    """
    工具抽象基类。

    每个子类就是一个 Agent 可用的"技能"。工作流：
    1. 子类定义 name / description / parameters  →  声明工具元信息
    2. 调用 to_function_definition()  →  生成 OpenAI function calling 的 tools 数组项
    3. 大模型返回 function_call 后，调用 execute(**kwargs) 执行

    子类示例::

        class ReadFile(Tool):
            name = "read_file"
            description = "读取指定路径的文件内容"
            parameters = {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "文件路径"}
                },
                "required": ["filepath"],
            }

            async def execute(self, filepath: str) -> str:
                with open(filepath) as f:
                    return f.read()
    """

    # ---- 子类必须定义的元信息 ----

    @property
    @abstractmethod
    def name(self) -> str:
        """全局唯一工具名，对应 OpenAI function name。"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """一句话描述工具用途，模型据此判断何时调用。"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """
        JSON Schema 参数定义，遵循 OpenAI function calling 规范::

            {
                "type": "object",
                "properties": { "arg": {"type": "string", "description": "..."} },
                "required": ["arg"],
            }
        """
        ...

    # ---- 子类必须实现的执行逻辑 ----

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        执行工具逻辑，接收命名参数，返回字符串结果。

        返回 str 而非 dict 是为了直接拼入下轮对话的 tool message。
        """
        ...

    # ---- 公共方法：生成 OpenAI 函数定义 ----

    def to_function_definition(self) -> dict:
        """
        组装为 OpenAI function calling 格式::

            {
                "type": "function",
                "function": {
                    "name": "...",
                    "description": "...",
                    "parameters": { ... },
                }
            }
        """
        # 快速校验，子类未正确定义时提前报错
        if not self.name or not isinstance(self.name, str):
            raise TypeError(f"{self.__class__.__name__}: name 必须是非空 str")
        if not self.description or not isinstance(self.description, str):
            raise TypeError(f"{self.__class__.__name__}: description 必须是非空 str")
        if not isinstance(self.parameters, dict):
            raise TypeError(f"{self.__class__.__name__}: parameters 必须是 dict")
        if self.parameters.get("type") != "object":
            raise ValueError(f"{self.__class__.__name__}: parameters 顶层 type 必须为 'object'")

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    # ---- dunder，方便调试 ----

    def __repr__(self) -> str:
        return f"<Tool name={self.name!r}>"

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"
