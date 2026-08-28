import os

from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    load_dotenv()
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key or api_key == "replace_me":
        raise SystemExit("请先在 .env 中填写真实的 LLM_API_KEY。")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
    )
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        messages=[
            {"role": "system", "content": "你是 12345 热线工单辅助智能体。"},
            {"role": "user", "content": "请只回复：DeepSeek 连接成功。"},
        ],
        stream=False,
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
