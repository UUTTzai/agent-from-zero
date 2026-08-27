"""
阶段 0 · 连通性测试
目标：验证 API Key、网络、请求格式全部可用。
运行：uv run 01_test_connection.py

本脚本刻意不使用任何框架 —— 直接用 OpenAI SDK 调 OpenAI 兼容接口
（百炼 compatible-mode），先看清最底层的协议长什么样。
"""

from openai import OpenAI

from config import get_provider

PROVIDER_NAME = "qwen"  # 以后在 config.py 里加了其他服务商，可在这里切换


def main():
    provider, api_key = get_provider(PROVIDER_NAME)

    # OpenAI SDK 只要指定 base_url，就能指向任何 OpenAI 兼容的服务
    client = OpenAI(base_url=provider["base_url"], api_key=api_key)

    print(f"正在调用 {PROVIDER_NAME} / {provider['default_model']} ...")

    response = client.chat.completions.create(
        model=provider["default_model"],
        messages=[
            {"role": "system", "content": "你是一个简洁的助手，用一句话回答。"},
            {"role": "user", "content": "什么是 AI Agent？"},
        ],
        temperature=0.7,
    )

    # 看看返回值的结构 —— 这是后续所有学习的最基础协议
    print("\n=== 模型回复 ===")
    print(response.choices[0].message.content)

    # 面试考点：成本意识。每次调用的 token 用量要心里有数
    usage = response.usage
    print("\n=== 本次调用消耗 ===")
    print(f"输入 {usage.prompt_tokens} tokens，输出 {usage.completion_tokens} tokens，"
          f"合计 {usage.total_tokens} tokens")


if __name__ == "__main__":
    main()
