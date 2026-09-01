"""
模型服务配置 —— 统一管理服务商信息与 API Key 的读取。

两个重要工程原则：
1. Key 只从环境变量 / .env 文件读取，绝不硬编码在代码里；
2. .env 已加入 .gitignore，永远不会被提交到 Git 仓库。
"""

import os

from dotenv import load_dotenv

# 把项目根目录的 .env 文件加载进环境变量
load_dotenv()


PROVIDERS = {
    # 阿里百炼（Qwen）—— OpenAI 兼容接口
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "default_model": "qwen3.7-plus",
    },
    # 以后拿到其他家的 Key，取消注释并在 .env 里配置对应环境变量即可
    # "deepseek": {
    #     "base_url": "https://api.deepseek.com",
    #     "api_key_env": "DEEPSEEK_API_KEY",
    #     "default_model": "deepseek-chat",
    # },
    # "zhipu": {
    #     "base_url": "https://open.bigmodel.cn/api/paas/v4",
    #     "api_key_env": "ZHIPU_API_KEY",
    #     "default_model": "glm-4.5-air",
    # },
    # "kimi": {
    #     "base_url": "https://api.moonshot.cn/v1",
    #     "api_key_env": "MOONSHOT_API_KEY",
    #     "default_model": "kimi-k2-0711-preview",
    # },
}


def get_provider(name: str = "qwen"):
    """获取服务商配置及其 API Key。

    返回：(provider 配置字典, api_key)
    如果 Key 未配置，抛出带操作指引的错误。
    """
    if name not in PROVIDERS:
        raise KeyError(f"未知的 provider: {name}，可选：{list(PROVIDERS)}")

    provider = PROVIDERS[name]
    env_name = provider["api_key_env"]
    api_key = os.getenv(env_name, "")

    if not api_key or api_key.startswith("sk-your"):
        raise RuntimeError(
            f"环境变量 {env_name} 还没有配置。\n"
            f"请打开项目根目录的 .env 文件，把你从百炼控制台拿到的 API Key "
            f"粘贴到 {env_name}= 后面，保存后重新运行。"
        )
    return provider, api_key
