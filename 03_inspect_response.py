"""
阶段 1 辅助工具 · 解剖 API 返回值

作用：把一次对话请求的返回对象原样打印出来，看 response 里到底有什么。
当你对"SDK 返回的格式长什么样"没把握时，跑它 + 改它。

运行：uv run 03_inspect_response.py
"""

import json

from openai import OpenAI

from config import get_provider

provider, api_key = get_provider("qwen")
client = OpenAI(base_url=provider["base_url"], api_key=api_key)

resp = client.chat.completions.create(
    model=provider["default_model"],
    messages=[{"role": "user", "content": "请回复两个字：收到"}],
    max_tokens=20,
)

print("response 的对象类型：", type(resp).__name__)
print("\n=== 完整结构（转成 JSON 打印）===")

# 不同版本的 openai SDK 序列化方法名不同，逐个尝试（这也是一种'查'的技巧）
if hasattr(resp, "model_dump_json"):
    print(resp.model_dump_json(indent=2))
elif hasattr(resp, "model_dump"):
    print(json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))
else:
    print(json.dumps(json.loads(resp.json()), indent=2, ensure_ascii=False))

print("\n=== 常用访问路径速查 ===")
print("回复文本：resp.choices[0].message.content =",
      resp.choices[0].message.content)
print("tokens：  resp.usage.prompt_tokens / completion_tokens =",
      resp.usage.prompt_tokens, "/", resp.usage.completion_tokens)
