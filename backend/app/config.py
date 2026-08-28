"""应用配置：从 .env 读取 LLM 相关设置。

所有配置均携带安全默认值；无 Key 时 LLM 不可用，系统自动回退本地确定性引擎。
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""
    EMBEDDING_MODEL: str = ""
    APP_ENV: str = "development"

    # 语音识别（可选）：阿里云百炼 ASR。
    # 留空（或占位符 replace_me）时 ASR 不可用，自动走精确匹配 / 模拟兜底。
    ASR_API_KEY: str = ""
    ASR_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ASR_MODEL: str = "qwen3-asr-flash"

    # 语音识别（可选）：科大讯飞录音文件转写大模型。
    # 与 kdxf.md 对齐：本地音频先上传 /v2/upload，再通过 /v2/getResult 轮询结果。
    KDXF_ASR_APP_ID: str = ""
    KDXF_ASR_ACCESS_KEY_ID: str = ""
    KDXF_ASR_ACCESS_KEY_SECRET: str = ""
    KDXF_ASR_BASE_URL: str = "https://office-api-ist-dx.iflyaisol.com"
    KDXF_ASR_LANGUAGE: str = "autodialect"
    KDXF_ASR_POLL_INTERVAL_SECONDS: int = 5
    KDXF_ASR_POLL_TIMEOUT_SECONDS: int = 900


settings = Settings()

# 仅当配置真实 Key（非占位符 replace_me）时，LLM 才被视为可用。
LLM_AVAILABLE = bool(settings.LLM_API_KEY) and settings.LLM_API_KEY != "replace_me"


def _valid_secret(value: str) -> bool:
    return bool(value) and value != "replace_me"


# 同上，ASR 可用判定。百炼和讯飞任一配置完整即可启用真实 ASR。
ASR_AVAILABLE = _valid_secret(settings.ASR_API_KEY) or all(
    _valid_secret(value)
    for value in (
        settings.KDXF_ASR_APP_ID,
        settings.KDXF_ASR_ACCESS_KEY_ID,
        settings.KDXF_ASR_ACCESS_KEY_SECRET,
    )
)
