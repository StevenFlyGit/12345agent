# 后端工程

`backend/` 是 12345 Agent 的 Python 后端工作目录，负责 FastAPI 接口、LangGraph 工作流、诉求理解、工单生成、事项分类、承办单位推荐、回复辅助、数据准备和自动化测试。

## 目录职责

- `app/api/`：FastAPI 路由和请求入口。
- `app/agents/`：大模型 Agent 节点、工具调用和 Prompt 逻辑。
- `app/core/`：配置、日志、异常和通用基础能力。
- `app/schemas/`：Pydantic 输入、输出、工单和工作流状态模型。
- `app/services/`：业务服务及跨模块编排。
- `app/workflow/`：LangGraph 状态、节点连接和人工审核中断点。
- `app/repositories/`：SQLite、向量检索和文件数据访问。
- `data/`：官方数据副本、标准化结果、分类目录、职责规则和 Mock 数据。
- `scripts/`：离线数据准备脚本。
- `tests/`：后端接口、服务和工作流测试。

## 配置本机环境变量

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS Terminal：

```bash
cp .env.example .env
```

只在本机 `.env` 中填写真实密钥，不要修改 `.env.example` 为真实值。

## 安装、检查和启动

以下命令均在 `backend/` 中执行：

```powershell
python -m pip install -r requirements.txt
python verify_env.py
python -m pytest
python -m uvicorn app.main:app --reload
```

## 准备官方业务数据

把官方 Excel 与配套录音按类别放入 `data/raw/official_work_orders/`，然后执行：

```powershell
# data/raw/official_work_orders 同时保存 Excel 与录音；脚本当前只匹配 *.xlsx
python scripts/prepare_dataset.py data/raw/official_work_orders
```

标准化结果写入 `data/processed/work_orders.jsonl`。

## 路径约定

后端程序、测试和脚本均以 `backend/` 为工作目录。不要从仓库根目录直接执行 `uvicorn app.main:app`，否则 Python 可能无法找到 `app` 包。
