# agent-from-zero

AI Agent 开发学习项目 —— 手写实现、不依赖框架。
对应《Agent 开发 12 周学习路线》阶段 0–1。

## 快速开始

```bash
# 安装依赖（首次或依赖变更后）
uv sync

# 打开 .env，把 DASHSCOPE_API_KEY 替换成你的真实 Key

# 阶段 0：连通性测试
uv run 01_test_connection.py

# 辅助：解剖 API 返回值结构
uv run 03_inspect_response.py

# 阶段 1 练习：手写 Agent 循环（先完成文件里的 TODO 再运行）
uv run 02_agent_loop.py
```

## 文件说明

| 文件 | 作用 |
|------|------|
| config.py | 服务商配置与 Key 读取（学习「Key 只走环境变量」的写法） |
| 01_test_connection.py | 最简对话调用，理解 messages / usage 协议 |
| 02_agent_loop.py | 练习：手写 function calling 的 Agent 循环 |
| 03_inspect_response.py | 辅助：把 response 原样打印，解剖返回结构 |
| .env.example | 环境变量模板（可提交）；.env 存真实 Key（禁止提交） |

## 阶段 1 目标清单

- [ ] 跑通 01，能说清返回值里 choices / message / usage 各字段含义
- [ ] 完成 02 的 TODO，让 Agent 正确调用 calculate 回答「27 乘以 43」
- [ ] 自己新增一个工具（建议：read_file，读取本地文件内容），验证模型能正确调用
- [ ] 观察并记录：每次任务花了多少 token？哪一步消耗最大？
