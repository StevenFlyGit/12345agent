from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # 新添加

app = FastAPI(title="12345 Agent API")

# 这段配置必须放在 app 创建之后、接口路由之前
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}