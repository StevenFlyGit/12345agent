# 12345 热线工单智能生成与转派辅助智能体（Demo v0.1）

群众诉求（文本 / 录音）→ 诉求理解 → 工单生成 → 分类与承办单位推荐 → 回复辅助 → 工作人员审核确认，
全流程以 `case_id` 串联。后端 FastAPI + SQLite，前端 React + TypeScript + Vite。

> 可靠性优先：有 LLM Key 走大模型，无 Key **自动回退确定性本地引擎**；ASR 以「文件名→样例精确匹配」为主、whisper 为辅、模拟转写为兜底。所有 AI 产出标注 `source`（llm / local-engine），ASR 来源标注 `transcript_source`。

## 一、目录结构（单仓库）

```
12345Agent/                单仓库根（本仓库）
  backend/                 后端（FastAPI + SQLite）
    app/                   FastAPI 入口、配置、schemas、services、workflow、api
    data/                  分类目录、部门规则、历史工单(json)、mock 样例、官方原始数据
    storage/cases.db       SQLite 库（自动创建，已 gitignore）
    scripts/prepare_dataset.py   官方 Excel -> work_orders.json 预处理
    tools/                 环境/连通性自检脚本（verify_env.py、test_deepseek.py）
    tests/                 pytest 测试（test_api / test_edge_cases / test_health）
    docs/architecture.md   架构设计文档
    requirements.txt       后端依赖
    pytest.ini             pytest 配置
    .env / .env.example    LLM 配置（.env 不入库；.env.example 入库）
  frontend/                前端（React + TypeScript + Vite）
    src/                   源码（main.tsx / App.tsx / api.ts / components/ / styles.css）
    dist/                  构建产物（已提交仓库，由后端静态托管，无需 Node 即可演示）
    package.json / vite.config.ts / tsconfig.json / index.html
  .conda/                  虚拟环境（本机自带，已 gitignore，与 backend 同级）
  run_server.bat           一键启动（自动 cd backend 并拉起 uvicorn）
  README.md                本文件
  .gitignore
```

## 二、安装与运行（最简：一键启动）

直接双击仓库根目录的 **`run_server.bat`** 即可：它会自动进入 `backend/`、使用仓库根自带的 `.conda` 虚拟环境安装依赖并启动后端（http://127.0.0.1:8000）。
前端 `frontend/dist` 已随仓库提交，单条 `uvicorn` 同时提供 API 与页面，**无需安装 Node.js 也能直接演示**。

手动方式：

### 1. 后端

```bash
cd 12345Agent\backend
# 虚拟环境（仓库根 .conda 已存在则跳过；注意必须用 Scripts 下的解释器）
..\conda\Scripts\python.exe -m pip install -r requirements.txt
..\conda\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 前端（仅在你需要改界面、重新构建时才需要 Node.js）

```bash
cd 12345Agent\frontend
npm install
npm run dev      # 开发服务器 http://127.0.0.1:5173，/api 已代理到 8000
npm run build    # 重新生成 dist/，由后端静态托管
```

访问：
- 页面（前端）：http://127.0.0.1:8000/
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health
- 引擎模式：http://127.0.0.1:8000/api/meta

## 三、LLM 配置（可选）

复制 `backend/.env.example` 为 `backend/.env`，填入真实 Key（`config.py` 仅当 Key 非 `replace_me` 时启用大模型）：

```
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
APP_ENV=development
```

- 配置真实 Key 后，`/api/meta` 的 `engine_mode` 为 `llm`，理解/分类/工单/回复优先调用大模型，失败自动回退本地引擎。
- Key 为占位符 `replace_me` 或为空时，`engine_mode` 为 `local-engine`，全程使用确定性本地引擎，**无需联网即可演示**。
- 判别是否真用上大模型：看每个接口返回里的 `source` 字段——`"llm"` 为真调用，`"local-engine"` 为回退。

## 四、核心接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/cases` | 创建案件（JSON `{text?,audio_filename?}` 或 `multipart/form-data` 带 `audio`） |
| GET | `/api/cases` | 案件列表 |
| GET | `/api/cases/{case_id}` | 案件详情（含各阶段结果） |
| POST | `/api/cases/{case_id}/workorder` | 生成工单 |
| POST | `/api/cases/{case_id}/classify` | 分类与承办单位推荐 |
| POST | `/api/cases/{case_id}/reply` | 回复辅助 |
| POST | `/api/cases/{case_id}/confirm` | 审核确认 `{operator, note?}` |
| POST | `/api/cases/{case_id}/handling` | 处理录入 `{text}` |
| GET | `/api/samples` | 样例文本与样例录音（可按文件名精确转写） |
| GET | `/api/history?q=` | 相似历史案例检索 |

## 五、快速全链路验证

```bash
curl -X POST http://127.0.0.1:8000/api/cases -H "Content-Type: application/json" \
  -d "{\"text\":\"南陵县某理发店没有公示服务价格，也没有在醒目位置悬挂营业执照，希望有关部门核查。\"}"
# 取返回 case_id，依次调用 /workorder /classify /reply /confirm
```

## 六、测试

```bash
cd 12345Agent\backend
..\conda\Scripts\python.exe -m pytest tests/ -q
```

## 七、说明与免责

- 部门职责（`backend/data/departments/department_rules.json`）与分类目录为**示例性归纳**，非现行权威权责，仅用于演示；正式版本以主办方提供目录为准。
- 系统**仅提供辅助建议**，最终由工作人员确认（confirm 写 audit_log）。
- 可选增强（faster-whisper / qdrant 向量检索 / RAG 多轮追问）未强制，按需安装。
- 官方原始数据集（`backend/data/raw/official_work_orders/`）仅保存在本机，不入库；演示样例 `work_orders.json` 已随仓库提供。
