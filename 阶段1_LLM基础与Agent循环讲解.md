# 阶段 1 具体讲解：LLM 对话本质与 Agent 循环

> 对应《12 周学习路线》阶段 1（第 1–2 周）。
> 配合项目里的 `01_test_connection.py`（已完成）和 `02_agent_loop.py`（待你完成 TODO）使用。

---

## 0. 一句话总纲

**LLM 本身没有记忆、没有手脚、没有主动性**——每次请求它都"失忆"，只会生成文本，而且你不问它就不动。

- 对话 API 解决"没有记忆"：把历史对话每次都完整地塞进请求；
- function calling 解决"没有手脚"：让模型输出结构化的"调用意图"，由你的代码真正执行；
- Agent 循环解决"没有主动性"：你的程序拿着工具结果反复追问模型，直到任务完成。

理解了这句话，下面所有细节都是它的展开。

---

## 1. 对话 API 的本质：一个无状态函数

### 1.1 服务器不记任何东西

你在 `01_test_connection.py` 里调的 `chat.completions.create`，本质是一个**纯函数**：传入 messages，返回回复。服务器不会记住上一次调用。所谓"多轮对话"是一个假象——**是你自己在维护历史，每次都把全部历史重新发过去**。

```
第一轮请求：  [system, user₁]                    → assistant₁
第二轮请求：  [system, user₁, assistant₁, user₂]  → assistant₂
第三轮请求：  [system, user₁, assistant₁, user₂, assistant₂, user₃] → ...
```

推论一：**丢上下文是最常见的 bug**。如果你第二轮只发了 `[user₂]`，模型完全不知道第一轮说过什么。
推论二：**对话越长，请求越大，花钱越多**（按 token 计费，历史每轮都在重复计费）。这就是为什么"上下文管理"是后面阶段 4 的核心课题。

### 1.2 四种角色（role）

| role | 作用 |
|------|------|
| `system` | 设定身份、规则、输出要求。模型会尽量遵守，但不是硬约束 |
| `user` | 用户输入 |
| `assistant` | 模型的历史回复（也包括带工具调用意图的消息，见第 2 节） |
| `tool` | 工具执行结果（第 2 节详解） |

### 1.3 流式输出（stream）

`create(..., stream=True)` 时，响应不再一次性返回，而是以一小段一小段的 chunk 陆续到达（底层是 SSE 协议）。两个意义：用户体验（打字机效果，不用干等），以及避免长回答触发超时。CLI 工具建议一开始就用流式，写法：

```python
stream = client.chat.completions.create(model=..., messages=..., stream=True)
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
```

注意：流式时 `usage`（token 用量）默认拿不到，百炼支持传
`stream_options={"include_usage": True}` 在最后一个 chunk 里带回用量——成本统计要靠它。

### 1.4 关键参数

- `temperature`：采样随机性。0 附近确定性强（适合工具决策、抽取任务），0.7~1 适合闲聊创作。**做 Agent 时工具调用相关的主链路建议调低（0~0.3），减少"抽风式"乱调工具**。
- `max_tokens`：限制单次输出长度，防止模型无限输出烧钱。

---

## 2. 结构化输出：从"自然语言"到"协议"

### 2.1 为什么需要结构化

程序解析自由文本是脆弱的。如果让模型"想算数就输出 [CALC] 3*4"，你得写一堆字符串匹配，模型格式稍偏就崩。function calling 的做法是：**约定一套 JSON 协议，模型被专门训练过按这套协议输出**，可靠性完全不同。

（补充：还有 JSON mode / response_format 可以强制模型整体输出合法 JSON，适合"抽取信息"类任务；function calling 则是"调用动作"的协议。两者思想一致：用结构化约束替代自由文本。）

### 2.2 function calling 协议全景（核心中的核心）

一次完整的工具调用往返，涉及四种消息。用你 `02_agent_loop.py` 里已有的 `calculate` 工具举例，用户问"27 乘以 43 等于多少"：

**① 请求：声明工具 + 提问**

```json
{
  "model": "qwen-plus",
  "messages": [
    {"role": "system", "content": "你是一个可以使用工具的助手"},
    {"role": "user", "content": "27 乘以 43 等于多少？"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "calculate",
        "description": "计算数学表达式，例如 '3 * (4 + 5)'",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string", "description": "数学表达式"}
          },
          "required": ["expression"]
        }
      }
    }
  ]
}
```

`tools` 用 JSON Schema 描述"有什么工具、参数长什么样"。**description 写得清不清楚，直接决定模型调得对不对**——这是提示工程的一部分。

**② 模型返回：调用意图（不是结果！）**

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "calculate",
          "arguments": "{\"expression\": \"27 * 43\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

三个关键细节：
- 模型只是**声明意图**，它自己不会也不能执行工具，真正执行的是你的 `execute_tool`；
- `arguments` 是一个 **JSON 字符串**，不是字典，必须 `json.loads` 解析（新手最常踩的坑）；
- `id` 很重要，回传结果时要靠它对账。

**③ 你执行工具，然后回传两条消息**

先把模型那条带 `tool_calls` 的 assistant 消息**原样追加**进 messages（漏掉它，下一步直接报错），再为每个 tool_call 追加一条：

```json
{"role": "tool", "tool_call_id": "call_abc123", "content": "1161"}
```

此时 messages 变成：

```
[system, user, assistant(带tool_calls), tool(结果)]
```

**④ 带着结果再调一次**

模型看到工具结果，生成最终回答："27 乘以 43 等于 1161。" 这一轮的返回里 `tool_calls` 为空、`content` 有值——循环结束的信号。

### 2.3 时间线总结

```
你 → API：  [system, user] + tools
API → 你：  assistant 消息，带 tool_calls（想调 calculate）
你：        本地执行 calculate("27 * 43") → "1161"
你 → API：  [system, user, assistant(tool_calls), tool("1161")]
API → 你：  assistant 消息，content="等于1161"，无 tool_calls → 结束
```

---

## 3. Agent 循环的本质

把第 2 节的单次往返套上循环，就是 Agent。伪代码（**这是你 02_agent_loop.py 三个 TODO 的答案形状，请把它翻译成真实代码自己写一遍**）：

```
messages = [system, user]

重复，最多 max_steps 轮：
    response = 调用LLM(messages, tools)
    msg = response.choices[0].message
    messages 追加 msg                     ← 无论哪种分支都要先追加

    如果 msg.tool_calls 为空：
        打印 msg.content（最终答案）
        结束

    对 msg.tool_calls 里的每个 tool_call：
        name      = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        result    = execute_tool(name, arguments)
        messages 追加 {"role": "tool",
                       "tool_call_id": tool_call.id,
                       "content": result}
    （进入下一轮，模型基于工具结果继续推理）

到达 max_steps 还没结束 → 提示"步骤超限"退出
```

三个必须写进去的工程细节（也是面试点）：

1. **步数上限**：没有 `max_steps` 的循环，模型一旦陷入"调工具→不满意→再调"就是死循环烧钱。生产代码里这是保命措施。
2. **工具出错不是异常退出，而是信息**：`execute_tool` 里把错误信息作为字符串返回（你的骨架已经这么写了），模型看到"计算失败：xxx"往往会自己修正参数重试——这是 Agent 自愈能力的来源。
3. **打印轨迹**：每一轮打印"模型想调什么工具、传了什么参数、得到什么结果"。你的产出要求里"打印每一步的推理与工具调用轨迹"就是靠这个。

---

## 4. ReAct：在 tool-use 之上多了什么？

ReAct = **Re**asoning + **Act**ing，2022 年提出的经典模式，核心思想：让模型**先显式说出推理（Thought），再行动（Action），看到结果（Observation），再推理……**，推理与行动交替进行。

在 function calling 出现之前，人们用纯提示词实现它：让模型按"Thought: 我需要先查一下…… Action: search[关键词] Observation: ……"的文本格式输出，程序用正则解析。今天模型的 tool_calls 能力，本质上是把这套思维**内化进了训练**——你会发现好的模型在决定调工具前，`content` 里常常已经带了简短的思考。

手写 ReAct 的价值在于**把隐式思考变成显式约束**：在 system prompt 里要求模型"调用任何工具前，先说明你为什么需要它、预期得到什么"，并在你的轨迹打印里把这段思考记录下来。对复杂多步任务，这能明显减少"乱调工具"；它也让你调试时能看到模型"当时是怎么想的"。

面试角度：被问"ReAct 和 function calling 什么关系"，标准答案思路是——ReAct 是 Agent 的**思想/范式**（先推理后行动、交替迭代），function calling 是实现这个思想的**协议机制**之一，且是更可靠的那个。

---

## 5. 最终产出：三工具命令行 Agent

目标：能完成 **"查一下今天的新闻，把摘要写到 news_summary.txt"** 这类多步任务。

### 5.1 三个工具的选型建议

| 工具 | 推荐实现 | 要点 |
|------|----------|------|
| 联网搜索 | **首选：百炼自带的联网能力**——调用时加 `enable_search=True` 参数，把这次调用封装成你的 `web_search` 工具；备选：`pip install ddgs`（DuckDuckGo 免费、无需 Key，国内网络可能要代理） | 封装成工具时才符合"Agent 调工具"的训练目标 |
| 文件读写 | 就是 `open()`，封装 `write_file(path, content)` 和 `read_file(path)` | 练习时限制只能写当前目录下的文件（判断路径），这是安全习惯 |
| 计算器 | 已有 `calculate`（eval 实现） | 可以保留，面试时主动说明"生产环境要换成安全解析（如 asteval）"是加分项 |

### 5.2 轨迹打印的样子（产出验收参考）

```
--- 第 1 轮 ---
模型思考：用户要今天的新闻，我需要先搜索
调用工具：web_search(query="今日要闻")
工具结果：1. xxx  2. xxx ...

--- 第 2 轮 ---
模型思考：已获取新闻，现在把摘要写入文件
调用工具：write_file(path="news_summary.txt", content="...")
工具结果：写入成功

--- 第 3 轮 ---
最终回答：已经把今日新闻摘要写入 news_summary.txt
```

### 5.3 验收标准（对照自查）

- [ ] 不借助任何框架，全部基于 OpenAI SDK / requests 手写
- [ ] 多步任务能走通：搜索 → 写文件，至少两个工具在一次任务中被先后调用
- [ ] 每一步都有清晰轨迹输出（思考/工具/参数/结果）
- [ ] `max_steps` 超限保护生效（故意构造一个完不成的任务试试）
- [ ] 工具报错时模型能收到错误信息并尝试恢复
- [ ] 能说清每次任务消耗的 token 数（`usage`）

---

## 6. 两周时间安排建议

**第 1 周：吃透对话与协议**
- 把 `01_test_connection.py` 扩展成一个多轮 CLI 聊天：输入循环 + 自己维护 messages 列表（体会"历史靠你自己带"）；
- 加上流式输出；
- 读懂第 2 节的四步协议，能不看文档画出消息流转图。

**第 2 周：完成 Agent**
- 完成 `02_agent_loop.py` 的三个 TODO（对照第 3 节伪代码自己翻译）；
- 自己新增 `read_file` / `write_file` 工具（照 `calculate` 的样子声明 + 实现，检验你是否真懂协议）；
- 接入搜索工具，跑通"查新闻写文件"任务；
- 在 system prompt 里加入 ReAct 式要求，对比开/关时的轨迹差异。

卡住超过 30 分钟，把**报错原文和你的代码**拿来问我，我只给提示不给全码。

---

## 7. 高频坑清单

1. **忘记带全历史** → 模型"失忆"，回答牛头不对马嘴。
2. **漏掉带 tool_calls 的 assistant 消息** → 直接追加 tool 消息，API 报错（tool 消息必须紧跟在发起调用的 assistant 消息之后）。
3. **忘记 `json.loads(arguments)`** → 拿到的是字符串，按字典取值就崩。
4. **循环无上限** → 死循环烧钱。
5. **temperature 太高** → 模型随机乱调工具或参数乱填。
6. **把 API Key 写进代码或打印进日志** → 安全红线。
7. **模型不调工具、直接瞎编答案** → 通常是工具 description 写得不清楚，或者 system prompt 没告诉它"你拥有这些工具，需要时应该使用"。
