# 12345 热线工单智能生成与转派辅助智能体（Demo v1）

群众诉求（文本 / 录音）→ 诉求理解 → 工单生成 → 分类与承办单位推荐 → 回复辅助 → 工作人员审核确认，全流程以 `case_id` 串联。后端 FastAPI + SQLite，前端 React + TypeScript + Vite。

> 可靠性优先：有 LLM Key 走大模型，无 Key **自动回退确定性本地引擎**；ASR 以「文件名→样例精确匹配」为主、whisper 为辅、模拟转写为兜底。所有 AI 产出标注 `source`（llm / local-engine），ASR 来源标注 `transcript_source`。

## 首页与导航

- `/`：工作流总入口、工单状态 KPI、在途工单接管列表与分类分布。
- `/pipeline`：原有六步工单工作台；支持 `/pipeline?case={case_id}` 加载并定位已有工单。
- `/data`：部门规则搜索、详情、编辑与删除；保存后同步更新 JSON 和部门规则 RAG 索引。
- 生产构建由 FastAPI 托管，以上页面路径可直接访问和刷新。

## 首页展示数据接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/meta` | 顶部引擎状态：显示 `engine_mode`，接口失败时显示 `local-engine` |
| GET | `/api/departments/rules` | 规则文件名：接口字段 `filename`，当前页面显示 `department_rules.json` |
| GET | `/api/departments/rules` | 部门规则数量：`rules.length` |
| GET | `/api/departments/rules` | 规则版本：优先取 `rules[0].version`，为空时取 `schema_version` |
| GET | `/api/departments/rules` | 最近更新时间：`updated_at`，页面格式为 `MM/DD` |
| GET | `/api/cases` | 工单总数：返回的工单数组长度 |
| GET | `/api/cases` | 在途工单：工单总数减去 `confirmed=true` 的工单数 |
| GET | `/api/cases` | 已确认完成：`confirmed=true` 的工单数 |
| GET | `/api/cases` | 紧急工单：`understanding.urgent=true` 的工单数 |
| GET | `/api/cases` | 概览进度条：在途工单数除以工单总数 |
| GET | `/api/cases` | “已录入”数量：未完成、未进入人工复核，且无 `reply`、`classification`、`work_order` 的工单数 |
| GET | `/api/cases` | “已生成工单”数量：未完成、未进入人工复核、无 `reply` 和 `classification`，但存在 `work_order` 的工单数 |
| GET | `/api/cases` | “已分派待处理”数量：未完成、未进入人工复核、无 `reply`，但存在 `classification` 的工单数 |
| GET | `/api/cases` | “已生成回复”数量：未完成、未进入人工复核，且存在 `reply` 的工单数 |
| GET | `/api/cases` | “待最终确认”数量：未完成且 `next_action=human_review` 的工单数 |
| GET | `/api/cases` | 在途工单列表总数：`confirmed` 不为 `true` 的工单数 |
| GET | `/api/cases` | 工单编号：`case_id` |
| GET | `/api/cases` | 工单状态：根据 `confirmed`、`next_action`、`reply`、`classification`、`work_order` 依次判断 |
| GET | `/api/cases` | 紧急标识：`understanding.urgent=true` 时显示“急” |
| GET | `/api/cases` | 工单标题：依次取 `work_order.title`、`understanding.demand`、`understanding.event`、`understanding.transcript`、`input.text` |
| GET | `/api/cases` | 工单创建时间：`created_at`，页面格式为 `MM/DD HH:mm` |
| GET | `/api/cases` | 工单列表顺序：按 `created_at` 倒序，默认显示前 8 条 |
| GET | `/api/cases` | 已分类工单数：存在 `classification.category_name` 或 `classification.category` 的工单数 |
| GET | `/api/cases` | 分类名称：优先取 `classification.category_name`，为空时取 `classification.category` |
| GET | `/api/cases` | 分类数量：按分类名称分组计数，页面显示数量最多的前 8 类 |
| GET | `/api/cases` | 未分类工单数：工单总数减去已分类工单数 |
| GET | `/api/cases/{case_id}` | 点击工单后加载该工单详情，并进入原工作流对应步骤 |
| GET | `/api/samples` | 点击“开始处理工单 →”进入工作流后，加载文本样例和录音样例 |
| GET | `/api/departments/rules` | 点击“打开数据管理 →”后，加载完整部门规则列表 |

> `GET /api/cases` 请求失败时，首页会显示前端内置的演示数据，并标记数据来源为“本地演示数据”。

## 一、目录结构（单仓库）

```
12345Agent-New/            单仓库根（本仓库）
  backend/                 后端（FastAPI + SQLite）
    app/                   FastAPI 入口、配置、schemas、services、workflow、api、repositories
      data/loaders.py      数据加载器（分类目录、部门规则、历史工单等）
    data/                  分类目录(categories)、部门规则(departments)、mock 样例、
                           预处理产物(processed)、官方原始数据(raw)
    storage/cases.db       SQLite 库（自动创建，已 gitignore）
    scripts/prepare_dataset.py   官方 Excel -> work_orders.json 预处理
    scripts/inspect_chroma_index.py  查看 Chroma 向量库内容并导出
    tools/                 环境/连通性自检脚本（verify_env.py、test_deepseek.py）
    tests/                 pytest 测试（test_api / test_edge_cases / test_health）
    venv/                  后端虚拟环境（本机自带，已 gitignore）
    requirements.txt       后端依赖
    pytest.ini             pytest 配置
    .env / .env.example    LLM 配置（.env 不入库；.env.example 入库）
  frontend/                前端（React + TypeScript + Vite）
    src/                   源码（main.tsx / App.tsx / api.ts / components/ / styles.css）
      components/          Stepper（横向 Pipeline 轨道）+ 6 个阶段 Panel + CaseBar
    dist/                  构建产物（已提交仓库，由后端静态托管，无需 Node 即可演示）
    package.json / vite.config.ts / tsconfig.json / index.html
  docs/                    项目文档
    backend-architecture.md    后端架构设计文档
    backend-gap-list.md        后端能力缺口清单（前端改造配套，含 TODO 对照）
  activate_backend_venv.bat / .command    一键激活后端 venv（Win / macOS）
  activate_frontend_venv.bat / .command   前端开发环境说明（Win / macOS）
  run_server.bat           一键启动（位于上级目录，自动 cd backend 并拉起 uvicorn）
  README.md                本文件
  .gitignore
```

## 二、安装与运行（最简：一键启动）

直接双击上级目录的 **`run_server.bat`**，或本目录的 **`activate_backend_venv.bat`** 即可：自动进入 `backend/`、使用 `backend/venv` 虚拟环境安装依赖并启动后端（[http://127.0.0.1:8000）。](http://127.0.0.1:8000%EF%BC%89%E3%80%82)
前端 `frontend/dist` 已随仓库提交，单条 `uvicorn` 同时提供 API 与页面，**无需安装 Node.js 也能直接演示**。

手动方式：

### 1. 后端

先从仓库根目录进入 `backend/`，用标准库 `venv` 构建 Python 虚拟环境，激活后再安装依赖并启动：

```powershell
cd backend
# 1. 构建 Python 虚拟环境（仅在首次或环境缺失时执行）
python -m venv venv
# Windows 激活虚拟环境：
venv\Scripts\activate
# macOS / Linux 激活虚拟环境：
source venv/bin/activate
# 2. 安装依赖、检查环境、运行测试与启动服务
python -m pip install --upgrade pip setuptools wheel #安装基础工具
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ #安装依赖
```

初次构建依赖后执行：

```PowerShell
# 验证环境是否构建完成
Copy-Item .env.example .env
python verify_env.py
```

后端服务启动

```PowerShell
cd backend
venv\Scripts\activate
python -m uvicorn app.main:app --reload
```

启动后访问：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

后端的 `.env`、依赖和运行命令均以 `backend/` 为工作目录。详细说明见 `backend/README.md`。

### 2. 前端

首次使用时从仓库根目录执行：

```powershell
cd frontend
npm install #前端依赖安装
npm run build #生产构建检查
```

前端服务启动

```PowerShell
cd frontend
npm run build
```

启动后访问 Vite 输出的本地地址，通常是：

- `http://localhost:5173`

前端只允许保存 `VITE_API_BASE_URL` 等非敏感配置，真实模型密钥不得写入前端代码或前端环境变量。

访问：

- 页面（前端）：[http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- API 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 健康检查：[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- 引擎模式：[http://127.0.0.1:8000/api/meta](http://127.0.0.1:8000/api/meta)

## 三、LLM 配置

复制 `backend/.env.example` 为 `backend/.env`，填入真实 Key（`config.py` 仅当 Key 非 `replace_me` 时启用大模型）：

```
# LLM Model - 推荐deepseek
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
APP_ENV=development

# 科大讯飞录音文件转写（可选，录音真实转写需要）
KDXF_ASR_APP_ID=replace_me
KDXF_ASR_ACCESS_KEY_ID=replace_me
KDXF_ASR_ACCESS_KEY_SECRET=replace_me
KDXF_ASR_BASE_URL=https://office-api-ist-dx.iflyaisol.com
KDXF_ASR_LANGUAGE=autodialect
KDXF_ASR_POLL_INTERVAL_SECONDS=4
KDXF_ASR_POLL_TIMEOUT_SECONDS=300
```

- 配置真实 Key 后，`/api/meta` 的 `engine_mode` 为 `llm`，理解/分类/工单/回复优先调用大模型，失败自动回退本地引擎。
- Key 为占位符 `replace_me` 或为空时，`engine_mode` 为 `local-engine`，全程使用确定性本地引擎，**无需联网即可演示**。
- 判别是否真用上大模型：看每个接口返回里的 `source` 字段——`"llm"` 为真调用，`"local-engine"` 为回退。
- 科大讯飞参数用于真实录音转写；配齐 `KDXF_ASR_APP_ID`、`KDXF_ASR_ACCESS_KEY_ID`、`KDXF_ASR_ACCESS_KEY_SECRET` 后，上传录音会优先调用讯飞 ASR。
- 科大讯飞参数保持 `replace_me` 或为空时，录音流程会继续使用样例精确匹配 / 模拟转写兜底，不影响文本工单演示。
- 所有真实密钥只写入 `backend/.env`，不要写入前端、截图、README 或提交到 Git。

## 四、核心接口

| 方法 | 路径                               | 说明                                                                                |
| ---- | ---------------------------------- | ----------------------------------------------------------------------------------- |
| POST | `/api/cases`                     | 创建案件（JSON`{text?,audio_filename?}` 或 `multipart/form-data` 带 `audio`） |
| GET  | `/api/cases`                     | 案件列表                                                                            |
| GET  | `/api/cases/{case_id}`           | 案件详情（含各阶段结果）                                                            |
| POST | `/api/cases/{case_id}/workorder` | 生成工单                                                                            |
| POST | `/api/cases/{case_id}/classify`  | 分类与承办单位推荐                                                                  |
| POST | `/api/cases/{case_id}/reply`     | 回复辅助                                                                            |
| POST | `/api/cases/{case_id}/confirm`   | 审核确认`{operator, note?}`                                                       |
| POST | `/api/cases/{case_id}/handling`  | 处理录入`{text}`                                                                  |
| GET  | `/api/departments/rules`         | 部门规则全量与文件信息                                                              |
| PUT  | `/api/departments/rules/{code}`  | 更新单条部门规则并重建规则检索索引                                                  |
| DELETE | `/api/departments/rules/{code}` | 删除单条部门规则并重建规则检索索引                                                  |
| GET  | `/api/samples`                   | 样例文本与样例录音（可按文件名精确转写）                                            |
| GET  | `/api/history?q=`                | 相似历史案例检索                                                                    |

## 五、快速全链路验证

```bash
curl -X POST http://127.0.0.1:8000/api/cases -H "Content-Type: application/json" \
  -d "{\"text\":\"南陵县某理发店没有公示服务价格，也没有在醒目位置悬挂营业执照，希望有关部门核查。\"}"
# 取返回 case_id，依次调用 /workorder /classify /reply /confirm
```

## 六、测试

```bash
cd 12345Agent-New\backend
venv\Scripts\python.exe -m pytest tests/ -q
```

## 七、查看 Chroma 向量库内容

`backend/scripts/inspect_chroma_index.py` 用于检查 Chroma 中各 collection 的记录内容、metadata 和检索结果。脚本会自动读取 `backend/app/rag/vectorstore.py` 中配置的 `CHROMA_DIR`，当前实际目录为 `backend/storage/chroma`，因此不需要额外传入 `--path`。

请在 `12345Agent-New/backend` 目录下执行。若尚未激活虚拟环境，可以直接使用项目自带 Python：

```powershell
cd 12345Agent-New\backend
venv\Scripts\python.exe scripts\inspect_chroma_index.py
```

### 1. 查看 collection 条数

不传参数时只列出各 collection 的记录数量，不会打印全部正文：

```powershell
venv\Scripts\python.exe scripts\inspect_chroma_index.py
```

当前项目预置的 collection 包括：

- `category_catalog`：分类目录
- `department_rules`：部门职责与规则
- `historical_cases`：历史工单
- `policy_docs`：政策文件

### 2. 查看指定 collection 的内容

使用 `-c` 或 `--collection` 指定 collection，使用 `--limit` 限制显示条数；`0` 表示不限制：

```powershell
# 查看分类目录前 10 条
venv\Scripts\python.exe scripts\inspect_chroma_index.py -c category_catalog --limit 10

# 查看部门规则全部记录
venv\Scripts\python.exe scripts\inspect_chroma_index.py --collection department_rules
```

### 3. 按关键词过滤

`--grep` 会同时在 document 正文和 metadata 中进行不区分大小写的关键词匹配：

```powershell
venv\Scripts\python.exe scripts\inspect_chroma_index.py -c department_rules --grep 住建
```

### 4. 执行语义检索

使用 `--query` 执行相似度检索，默认返回 3 条结果；可以通过 `--top-k` 调整返回数量：

```powershell
venv\Scripts\python.exe scripts\inspect_chroma_index.py -c department_rules --query "路灯不亮找谁" --top-k 5
```

### 5. 导出为 Markdown、JSON 或 HTML

支持 `text`、`md`、`json`、`html` 四种输出格式。HTML 是单文件页面，打开后可以使用页面内搜索框查看记录：

```powershell
# 导出 Markdown
venv\Scripts\python.exe scripts\inspect_chroma_index.py -c department_rules --format md -o out\department_rules.md

# 导出 JSON
venv\Scripts\python.exe scripts\inspect_chroma_index.py -c category_catalog --format json -o out\category_catalog.json

# 导出带搜索框的 HTML 页面
venv\Scripts\python.exe scripts\inspect_chroma_index.py -c historical_cases --format html -o out\historical_cases.html
```

说明：脚本一次只查看一个 collection 的详细内容；不传 `--collection` 时只显示所有 collection 的条数。若要查看全部 collection 的正文，需要分别指定 `-c` 执行，或分别导出为 HTML/JSON 文件。

## 八、说明与免责

- 部门职责（`backend/data/departments/department_rules.json`）与分类目录为**示例性归纳**，非现行权威权责，仅用于演示；正式版本以主办方提供目录为准。
- 系统**仅提供辅助建议**，最终由工作人员确认（confirm 写 audit_log）。
- 可选增强（faster-whisper / qdrant 向量检索 / RAG 多轮追问）未强制，按需安装。
- 官方原始数据集（`backend/data/raw/official_work_orders/`）仅保存在本机，不入库；演示样例 `work_orders.json` 已随仓库提供。
