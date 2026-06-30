import os
from openai import OpenAI

# 1. 定义函数：读取本地人设文件，完成"灵魂提取"
def build_system_prompt(file_path="identity.md"):
    if not os.path.exists(file_path):
        print(f"⚠️ 找不到文件: {file_path}，给你个默认人设先用着。")
        return "你是一个默认的AI助手。"

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# 2. 连上咱们的"无形网线"
client = OpenAI(
    api_key=os.environ.get("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)

# 3. 核心实操：给大模型"洗脑"
system_role_content = build_system_prompt("identity.md")
print(f"读取到的人设设定：\n【{system_role_content}】\n" + "=" * 30)

# 4. 发起文本接龙
response = client.chat.completions.create(
    model="Qwen/Qwen3.5-4B",
    messages=[
        # 灵魂注入！之前写死的字符串，现在变成了变量
        {"role": "system", "content": system_role_content},
        {"role": "user", "content": "你好老哥，我是个小白，想学编程，第一门语言该学啥？"}
    ],
    stream=True
)

# 5. 打印（打字机效果）
for chunk in response:
    if chunk.choices and chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="", flush=True)
print("\n")