"""
加成项 1：多轮对话
实现一个命令行连续聊天机器人，核心是维护一个全局的消息列表，
每次对话后追加用户和助手的消息，使其拥有“记忆”。
验证方法：第一轮告知名字，第二轮问出名字即证明记忆生效。
"""

"""
加成项 2：流式输出（在 04 多轮对话基础上增加打字机效果）
"""


import sys 
from openai import OpenAI
from config import get_provider

# ---------- 初始化客户端和模型 ----------
provider, api_key = get_provider("qwen")
client = OpenAI(base_url=provider["base_url"], api_key=api_key)
MODEL = provider["default_model"]

# ---------- 核心：全局消息列表（对话历史） ----------
messages = [
    {"role": "system", "content": "你是一个乐于助人的助手。"}
]

def get_streaming_response(user_input: str) -> str:
    """
    调用模型并实现流式输出（打字机效果）。
    返回完整回复文本，同时将回复内容实时打印到终端。
    """
    # 先把用户消息加入历史（注意：本函数不修改全局 messages，只负责生成回复）
    messages.append({"role": "user", "content": user_input})

    # 发起流式请求
    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
        )
    except Exception as e:
        # 如果调用失败，移除刚加入的用户消息，避免污染历史
        messages.pop()
        print(f"\n调用模型失败：{e}")
        return ""

    full_reply = ""
    print("助手", end="", flush=True)

    for chunk in stream:
          # 注意：有些 chunk 的 choices 可能是空列表（例如最后一条结束信号）
          if not chunk.choices:
              continue

          delta = chunk.choices[0].delta
          # delta.content 可能为 None（比如只有 role 字段的 chunk）
          if delta.content:
              content = delta.content
              print(content, end="", flush=True)  # 逐字打印，不换行
              full_reply += content

    print()   # 最后补一个换行

          # 将完整的助手回复加入全局消息历史（确保记忆）
    messages.append({"role": "assistant", "content": full_reply})  # 记忆入库
    return full_reply

def main():
    print("多轮对话已启动 （输入 '退出' 或 'exit' 结束）")
    while True:
        try:
            user_input = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见")
            break
        if user_input in ("退出", "exit"):
            print("对话结束。")
            break
        # # 将用户消息加入历史
        # messages.append({"role": "user", "content": user_input})

        # try:
        #     # 请求模型回复
        #     response = client.chat.completions.create(
        #         model=MODEL,
        #         messages=messages
        #     )
        #     assistant_reply = response.choices[0].message.content

        #     # 打印助手回复
        #     print(f"助手：{assistant_reply}")

        #     # 必须将助手回复也加入历史，否则下一轮模型会“失忆”
        #     messages.append({"role": "assistant", "content": assistant_reply})

        # except Exception as e:
        #     print(f"调用模型时出错：{e}")
        #     # 出错时可以选择移除刚才添加的用户消息，避免污染历史
        #     # 这里简单处理：移除最后一条用户消息
        #     if messages and messages[-1]["role"] == "user":
        #         messages.pop()
        #     continue
        get_streaming_response(user_input)

if __name__ == "__main__":
        main()