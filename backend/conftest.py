"""pytest 全局配置。

测试环境强制使用确定性本地引擎：在导入任何 app 代码之前清空 LLM_API_KEY，
确保用例不依赖外部大模型、可重复运行（pydantic-settings 中环境变量优先级高于 .env）。

真实大模型能力请通过启动服务后访问 /api/meta（engine_mode=llm）与各接口返回的 source
字段人工确认，不纳入自动化测试，避免用例因外部服务不稳定而飘红。
"""
import os

os.environ["LLM_API_KEY"] = ""
