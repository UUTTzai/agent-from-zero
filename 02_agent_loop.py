"""
阶段 1 练习 · 手写最小 Agent 循环（不使用任何框架）

目标：实现「模型决定调工具 → 你执行工具 → 结果回传给模型 → 继续推理」的循环。
工具协议使用 OpenAI function calling 格式（百炼兼容模式同样支持）。

本文件已替你准备好不需要从零思考的部分（工具定义、工具执行函数），
中间的三个 TODO 才是练习核心 —— 先自己写，卡住超过 30 分钟再来要提示。

运行：uv run 02_agent_loop.py
"""
"""
阶段 1 练习 · 手写最小 Agent 循环（不使用任何框架）
加成项 3：Token 记账
"""
import json  # 解析 tool_call 参数时会用到
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from config import get_provider

# 脚本所在目录 —— 用它锚定相对路径，程序就不再依赖"你在哪个目录运行它"
PROJECT_DIR = Path(__file__).resolve().parent

provider, api_key = get_provider("qwen")
client = OpenAI(base_url=provider["base_url"], api_key=api_key)
MODEL = provider["default_model"]


# ---------------- 第一部分：工具定义（已写好，读懂格式） ----------------

# 用 JSON Schema 告诉模型「你有哪些工具可用」
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间，返回 YYYY-MM-DD HH:MM:SS 格式字符串",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算一个数学表达式的结果，例如 '3 * (4 + 5)'",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"],
            },
        },
    },
        {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取本地文本文件的内容并返回文本，例如读取 'test.txt'",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "要读取的文件路径，例如 'test.txt'"}
                },
                "required": ["path"],
            },
        },
    },
        {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "把文本内容写入本地文件，例如写 'test.txt'",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "要写的文件路径，例如 'test.txt'"},
                    "content":{"type":"string","description": "要写进文件的内容"}
                },
                "required": ["path","content"],
            },
        },
        },
        {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "联网搜索实时信息，适用于新闻、最新动态等训练数据里没有的内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要询问的问题"},
                },
                "required": ["query"],
            },
        },
        },   
]


def execute_tool(name: str, arguments: dict) -> str:
    """根据工具名和参数真正执行工具，返回字符串结果。

    模型只负责「决定调哪个工具、传什么参数」，真正干活的是这个函数 ——
    这就是 Agent 里「大脑」和「手脚」的分工。
    """
    if name == "get_current_time":
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if name == "calculate":
        try:
            # 注意：eval 有安全风险，这里仅为学习演示，
            # 生产环境绝不能对任意用户输入使用
            return str(eval(arguments["expression"]))
        except Exception as e:
            return f"计算失败：{e}"
    if name == "read_file":
        try:
            path = Path(arguments["path"])
            # 相对路径 → 锚定到脚本所在目录，避免"工作目录不同导致找不到文件"
            if not path.is_absolute():
                path = PROJECT_DIR / path
            with open(path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"读取失败： {e}"
    if name == "write_file":
        try:
            path = Path(arguments["path"])
            # 相对路径 → 锚定到脚本所在目录，避免"工作目录不同导致找不到文件"
            content = arguments["content"]
            if not path.is_absolute():
                path = PROJECT_DIR / path
            with open(path,'w', encoding="utf-8") as f:
                f.write(content)
            print(f"已写入 {len(content)} 个字符")
            return f"已写入 {len(content)} 个字符"
        except Exception as e:
            return f"写文件失败： {e}"
    if name == "web_search":
        try:
            resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": arguments["query"]}],
                    extra_body={"enable_search": True},   # 百炼的搜索开关要通过 extra_body 传
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"搜索失败：{e}"
    return f"未知工具：{name}"


# ---------------- 第二部分：Agent 循环（TODO：你的练习区） ----------------
# ---------------- 第二部分：Agent 循环（加上 Token 记账） ----------------

def run_agent(user_input: str, max_steps: int = 5):
    messages = [
        {"role": "system", "content": "你是一个可以使用工具的助手，需要时请调用工具获取信息。"},
        {"role": "user", "content": user_input},
    ]

    # ========== 新增：累计 Token 变量 ==========
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0

    for step in range(max_steps):
        print(f"\n--- 第 {step + 1} 轮 ---")

        # TODO 1：调用 client.chat.completions.create(
        #             model=MODEL, messages=messages, tools=TOOLS)
        #          取出 response.choices[0].message
        response = client.chat.completions.create(model=MODEL,messages=messages,tools=TOOLS)
        message = response.choices[0].message
        # ========== 新增：读取并累加本轮消耗 ==========
        usage = response.usage
        if usage:
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_tokens += usage.total_tokens
            print(f"[本轮消耗] 输入 {prompt_tokens} / 输出 {completion_tokens} / 合计 {usage.total_tokens}")

        # TODO 3（进阶）：打印每一轮模型的「思考」过程，
        if message.content:
            print(f"[模型思考]{message.content}")
        if message.tool_calls:
            for tc in message.tool_calls:
                print(f"[工具调用] {tc.function.name}({tc.function.arguments})")
        # TODO 2：判断模型是否想调用工具
        #   提示：看 message.tool_calls 是否为空
        #   · 为空 → 模型已给出最终答案，打印 message.content 并 return
        #   · 非空 → 按顺序做三件事：
        #       a. 把模型这条带 tool_calls 的 message 追加进 messages
        #          （必须原样追加，tool 消息要靠它关联）
        #       b. 遍历每个 tool_call：解析出函数名和参数
        #          （注意 tool_call.function.arguments 是 JSON 字符串，
        #            需要 json.loads 解析），调用 execute_tool 执行
        #       c. 每个工具结果追加一条消息：
        #          {"role": "tool",
        #           "tool_call_id": <对应 tool_call 的 id>,
        #           "content": <结果字符串>}
        #          然后进入下一轮循环，让模型基于工具结果继续推理
        # ========== 新增：打印总计 ==========
        if not message.tool_calls:
            print(f"\n最终答案：{message.content}")
            print("\n" + "=" * 50)
            print("📊 Token 消耗总计")
            print(f"  输入 Token（prompt）: {total_prompt_tokens}")
            print(f"  输出 Token（completion）: {total_completion_tokens}")
            print(f"  合计 Token: {total_tokens}")
            print("=" * 50)
            return
        messages.append(message.model_dump())
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            result = execute_tool(tool_name,arguments)
            messages.append({
                "role":"tool",
                "tool_call_id":tool_call.id,
                "content":result,
            })
        # TODO 3（进阶）：打印每一轮模型的「思考」过程，
        #          观察它是如何决定调用工具的

    print(f"\n达到了最大步数，未得到最终答案。")


if __name__ == "__main__":

    # 先跑这个：模型应该调用 get_current_time
    # run_agent("现在几点了？")

    # 再跑这个：模型应该调用 calculate
    run_agent("27 乘以 43 等于多少？直接告诉我结果。")
    # run_agent("读一下 test.txt，告诉我里面写了什么？")
    # run_agent("把'今天学会了写文件'这句话写进 output.txt")
    # run_agent("搜索一下最近 AI Agent 领域的最新进展，用三句话总结")
    # run_agent("搜索今天的科技新闻，把摘要写进 news_summary.txt")