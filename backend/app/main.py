"""FastAPI 应用入口：装配路由、CORS、静态托管与 /health。

启动顺序：
  1. 创建 app，配置全局 CORS（演示用 allow all）。
  2. 挂载业务路由 /api/*（必须在静态文件之前，避免被覆盖）。
  3. 尝试定位前端构建产物 dist，找到则用 StaticFiles(html=True) 挂载到 "/"，
     并提供 /api/meta 暴露引擎模式；找不到则 "/" 返回提示文字。
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.api import cases, history, samples
from app.config import LLM_AVAILABLE

ROOT = Path(__file__).resolve().parents[1]  # 后端项目根（backend/）

app = FastAPI(title="12345 热线工单智能辅助 API", version="demo-0.1")

# 全局 CORS（演示用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "llm_available": LLM_AVAILABLE}


@app.get("/api/meta")
def meta():
    return {
        "llm_available": LLM_AVAILABLE,
        "engine_mode": "llm" if LLM_AVAILABLE else "local-engine",
    }


# 业务路由（必须早于静态挂载）
app.include_router(cases.router)
app.include_router(samples.router)
app.include_router(history.router)


def _find_dist() -> Path | None:
    candidates = [
        ROOT.parent / "frontend" / "dist",   # 合并后结构：仓库根/frontend/dist
        ROOT / "frontend_dist",              # 兼容旧命名
    ]
    for c in candidates:
        c = c.resolve()
        if (c / "index.html").exists():
            return c
    return None


_dist = _find_dist()
if _dist is not None:
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(_dist / "index.html"))

    print(f"[前端托管] 已挂载静态资源：{_dist}")
else:

    @app.get("/")
    def index():
        return PlainTextResponse("前端未构建，请先在前端目录执行 npm run build（frontend/ 目录），或确认 frontend/dist 已存在。")
