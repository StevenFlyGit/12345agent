# 12345 热线工单智能生成与转派辅助智能体 — 架构设计

> 主理人：齐活林（Qi）｜架构师：高见远（Gao）｜版本：Demo v0.1
> 依据：赛题《12345热线工单智能生成与转派辅助智能体》+ Windows 环境搭建文档

## 1. 实现方案与框架选型

- **后端**：FastAPI（Python 3.11），代码在 `backend/app/`。负责受理录入、ASR、诉求理解、工单生成、分类转派、回复辅助、审核确认，并用 `case_id` 串联全流程；SQLite（标准库）持久化。
- **前端**：React + TypeScript + Vite + 自研简洁 CSS，代码在 `frontend/`。`npm run build` 产物（frontend/dist）由后端静态托管，**单条 `uvicorn` 命令即可演示前后端**。
- **可靠性优先**：依赖最小化；LLM 可选（有 Key 走大模型，无 Key 自动回退确定性本地引擎）；ASR 用「文件名→样例 transcript 精确匹配」为主、whisper 为辅、模拟转写为兜底。所有 AI 输出标注 `source`。

## 2. 文件清单

### 后端 `backend/`
- `app/main.py` — FastAPI 实例、CORS、挂载路由与前端静态资源、`/health`、根路径返回 index.html。
- `app/config.py` — pydantic-settings 加载 `.env`（LLM_API_KEY/BASE_URL/MODEL、APP_ENV）。
- `app/schemas/models.py` — 全部 Pydantic 模型。
- `app/data/loaders.py` — 加载分类目录、部门规则、历史工单样例、mock 样例。
- `app/services/llm.py` — OpenAI 兼容客户端封装，`is_available()` 探测。
- `app/services/asr.py` — 录音转写（精确匹配 / whisper / 模拟）。
- `app/services/local_engine.py` — 确定性本地引擎（分类/理解/工单/回复）。
- `app/services/understand.py` — 诉求理解编排（LLM 或本地）。
- `app/services/classify.py` — 分类与承办单位推荐编排。
- `app/services/workorder.py` — 工单生成编排。
- `app/services/reply.py` — 回复辅助编排。
- `app/services/history.py` — 相似历史案例检索（关键词重叠）。
- `app/workflow/store.py` — SQLite 案件存储（按 case_id）。
- `app/workflow/orchestrator.py` — 串联各阶段的业务流程。
- `app/api/cases.py` — cases 增删查、各阶段触发、确认、处理录入。
- `app/api/samples.py` — 样例录音/文本列表。
- `app/api/history.py` — 相似历史案例接口。
- `backend/scripts/prepare_dataset.py` — 官方 Excel 预处理（保留）。
- `data/departments/department_rules.json` — 填充 12 类部门规则（本设计第 6 节）。
- `requirements.txt` — 精简依赖。
- `tests/test_api.py` — API 测试。

### 前端 `frontend/`
- `package.json` / `vite.config.ts` / `tsconfig.json` / `index.html`
- `src/main.tsx` — 入口。
- `src/App.tsx` — 整体布局（顶栏 + 左侧步骤条 + 主面板）。
- `src/api.ts` — axios 封装（同域 `/api`）。
- `src/components/Stepper.tsx`、`InputPanel.tsx`、`UnderstandingPanel.tsx`、`WorkOrderPanel.tsx`、`ClassificationPanel.tsx`、`ReplyPanel.tsx`、`ConfirmPanel.tsx`、`CaseBar.tsx`。
- `src/styles.css` — 简洁大方主题（政务蓝主色 + 中性灰 + 卡片化）。

## 3. 核心数据模型（Pydantic）

```python
class CaseInput(BaseModel):
    text: str | None = None          # 文本输入
    audio_filename: str | None = None  # 录音文件名（用于精确匹配 transcript）

class UnderstandingResult(BaseModel):
    transcript: str                   # 文本或转写结果
    transcript_source: str           # "text" | "sample-match" | "whisper" | "simulated"
    time: str | None
    location: str | None
    parties: list[str]               # 涉及人员/对象
    event: str | None                # 主要事件
    demand: str | None               # 群众诉求
    other: str | None
    needs_clarification: bool
    missing_fields: list[str]
    urgent: bool
    repeat_request: bool
    source: str                      # "llm" | "local-engine"

class WorkOrder(BaseModel):
    title: str
    summary: str
    content: str
    key_elements: list[str]
    suggested_category: str | None
    source: str

class DepartmentSuggestion(BaseModel):
    main: str
    co: list[str]
    reason: str

class ClassificationResult(BaseModel):
    category: str | None
    category_name: str | None
    confidence: float
    suggestions: list[DepartmentSuggestion]
    needs_manual: bool
    manual_hint: str | None
    source: str

class ReplyResult(BaseModel):
    acceptance_notice: str
    handling_suggestion: str
    pre_reply: str
    callback_script: str
    modification_tips: list[str]
    source: str

class CaseState(BaseModel):
    case_id: str
    created_at: str
    input: CaseInput
    understanding: UnderstandingResult | None
    work_order: WorkOrder | None
    classification: ClassificationResult | None
    reply: ReplyResult | None
    confirmed: bool = False
    audit_log: list[dict] = []
```

## 4. 程序调用流程（时序）

```
用户(前端) --POST /api/cases{text|audio}--> cases.py
  cases.py --asr--> asr.py(精确匹配/whisper/模拟) --transcript--> understand.py
  understand.py --(LLM|local-engine)--> UnderstandingResult --存 SQLite--> 返回 CaseState(含 understanding + case_id)

前端拿到 case_id 后分步调用：
  POST /api/cases/{id}/workorder  --> workorder.py --> WorkOrder
  POST /api/cases/{id}/classify   --> classify.py  --> ClassificationResult
  POST /api/cases/{id}/reply      --> reply.py     --> ReplyResult
  POST /api/cases/{id}/confirm    --> 写 audit_log(confirmed=True)
  GET  /api/cases/{id}            --> 组装全部阶段，前端展示闭环
  GET  /api/samples               --> 样例录音/文本（一键填充）
  GET  /api/history?q=            --> 相似历史案例
```

## 5. 有序任务列表（含依赖）

- T1 建项目结构与精简依赖（requirements.txt）；建 docs、前端脚手架。
- T2 `schemas/models.py` 全部模型。
- T3 `data/loaders.py` 加载四类数据。
- T4 `services/local_engine.py`：关键词分类、正则要素提取、模板化工单与回复（无 Key 可用核心）。
- T5 `services/llm.py` 封装 + `is_available()`；各 understand/classify/workorder/reply 编排（LLM 优先，失败回退 local）。
- T6 `services/asr.py`：精确匹配 → whisper → 模拟。
- T7 `workflow/store.py` SQLite；`workflow/orchestrator.py` 串联。
- T8 `api/cases.py`、`api/samples.py`、`api/history.py` + `main.py` 挂载前端。
- T9 前端工程：布局 + 步骤条 + 各面板 + API 调用 + 简洁样式。
- T10 `npm run build` → 后端托管 `dist/`。
- T11 `tests/test_api.py` 验证闭环（本地引擎，无需 Key）。

## 6. department_rules.json 字段规范与 12 类草稿

字段：`department`（主责）、`co_departments`（协办）、`keywords`（匹配关键词）、`responsibilities`（职责简述）、`source_name`（来源标注）、`note`（「示例/非权威」提示）。

| 类别 | 主责单位 | 协办 | 关键词 |
|---|---|---|---|
| 经济财贸 | 发改委/商务局、市场监管局（价格经营） | 属地政府 | 价格、收费、经营、消费、发票、商家 |
| 卫生健康 | 卫健委、医疗机构 | 医保局 | 医院、挂号、诊疗、医疗、卫生、疫苗 |
| 市场监管 | 市场监管局 | 属地政府、行业主管 | 营业执照、公示、价格公示、假冒、食品、计量、电梯 |
| 生态环境 | 生态环境局 | 属地政府、城管（噪声） | 污染、异味、扬尘、油烟、排污、工业噪声、水体 |
| 公共服务 | 供水/供电/供气/供热公司、政务服务管理 | 行业主管 | 水、电、气、供暖、宽带、公交（部分） |
| 城乡建设 | 住建局、房屋征收主管 | 属地政府 | 房屋、施工、工地、拆迁、危房、路灯、道路建设 |
| 公共安全 | 公安局、应急管理局、消防救援 | 相关运营单位 | 燃气泄漏、安全、消防、治安、报警、危化 |
| 劳动和社会保障 | 人社局（劳动监察/社保） | 属地政府、总工会 | 工资、拖欠、社保、工伤、劳动合同、退休、就业 |
| 交通运输 | 交通运输局、公交公司、公安交管 | — | 公交、线路、出租车、拥堵、停车、车站 |
| 科教文体 | 教育局、文旅局、体育局 | — | 学校、教育、补课、文化、旅游、体育、场馆 |
| 农林水土 | 农业农村局、水务局、自然资源局 | — | 农田、灌溉、养殖、土地承包、河湖、水库、耕地 |
| 城市管理 | 城管局/住建（市政） | 属地政府、社区、物业 | 垃圾、占道经营、违建、绿化、井盖、生活噪声、共享单车 |

> 注意：上述部门职责为**示例性归纳**，非现行权威权责，仅用于演示；正式版本应以主办方提供目录为准。

## 7. 依赖清单（精简）

后端：`fastapi`、`uvicorn[standard]`、`pydantic`、`pydantic-settings`、`python-dotenv`、`python-multipart`、`openai`。
前端：`react`、`react-dom`、`vite`、`typescript`、`@vitejs/plugin-react`、`axios`。

## 8. 共享约定

- `case_id`：后端 `wo_<timestamp>_<rand4>` 生成，全程贯穿。
- `source` 字段：所有 AI 产出标注 `llm` 或 `local-engine`，便于展示与合规。
- `transcript_source`：标注文本/精确匹配/whisper/模拟，透明展示 ASR 来源。
- 时间格式：ISO 8601（`%Y-%m-%d %H:%M:%S`）。
- 不引入登录鉴权（Demo 阶段），但所有写操作留 `audit_log`。

## 9. 待明确事项

- 正式「事项分类目录」细类与权威部门职责，待主办方提供后替换 `department_rules.json`。
- RAG/向量检索、多轮追问为可选增强，本期以关键词检索做「相似历史案例」演示。
