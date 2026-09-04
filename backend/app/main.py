"""FastAPI 应用入口：装配路由、CORS、静态托管与 /health。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

from app.api import cases, departments, history, samples
from app.config import LLM_AVAILABLE, get_workflow_engine

ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(title="12345 热线工单智能辅助 API", version="demo-0.1")

# 本地开发前端地址；生产构建由本应用同源托管。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
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
        "workflow_engine": get_workflow_engine(),
    }


# 业务接口必须先于 SPA 回退注册。
app.include_router(cases.router)
app.include_router(samples.router)
app.include_router(history.router)
app.include_router(departments.router)


def _find_dist() -> Path | None:
    candidates = [
        ROOT.parent / "frontend" / "dist",
        ROOT / "frontend_dist",
    ]
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "index.html").exists():
            return resolved
    return None


_dist = _find_dist()
if _dist is not None:

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # 未定义的 API 始终返回 404，只有页面路径才回退到 React 入口。
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API 路径不存在")

        candidate = (_dist / full_path).resolve()
        try:
            candidate.relative_to(_dist)
            inside_dist = True
        except ValueError:
            inside_dist = False

        if full_path and inside_dist and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_dist / "index.html"))

    print(f"[前端托管] 已启用 SPA 回退：{_dist}")
else:

    @app.get("/")
    def index():
        return PlainTextResponse(
            "前端未构建，请先在 frontend/ 目录执行 npm run build，"
            "或确认 frontend/dist 已存在。"
        )
