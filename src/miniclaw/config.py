"""MiniClaw 配置管理 —— 从 JSON 文件和环境变量加载配置。"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MiniClawConfig:
    """MiniClaw Agent 运行配置。

    所有字段均可通过 config.json 设置，api_key 额外支持环境变量覆盖。
    """

    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "Pro/moonshotai/Kimi-K2.5"
    workspace: str = "."
    max_iterations: int = 32
    identity_file: str = "identity.md"


def load_config(config_path: str = "config.json") -> MiniClawConfig:
    """从 JSON 文件加载配置，环境变量 NANOCLAW_API_KEY 优先级最高。

    参数:
        config_path: JSON 配置文件路径，默认为工作目录下的 config.json。

    返回:
        填充好的 MiniClawConfig 实例。
    """
    config_path_obj = Path(config_path)

    # 1. 用默认值初始化
    config = MiniClawConfig()

    # 2. 读取 JSON 文件，覆盖默认值
    if config_path_obj.exists():
        with open(config_path_obj, "r", encoding="utf-8") as f:
            data: dict = json.load(f)
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)

    # 3. 环境变量 NANOCLAW_API_KEY 优先级最高
    env_api_key = os.getenv("NANOCLAW_API_KEY", "")
    if env_api_key:
        config.api_key = env_api_key

    return config
