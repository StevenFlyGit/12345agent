# 12345 热线工单智能生成与转派辅助智能体

本项目用于开发“12345 热线工单智能生成与转派辅助智能体”，基础闭环为：录音或文本输入 → 诉求理解与要素确认 → 标准化工单生成 → 事项分类与承办单位推荐 → 人工审核 → 处理结果录入 → 回复与回访话术辅助。

系统只提供辅助建议，最终工单内容、转派结果和群众回复必须由工作人员审核确认。

## 项目结构

```text
12345agent/
├─ activate_backend_venv.bat      # Windows：激活 backend venv 并启动后端
├─ activate_backend_venv.command  # macOS：双击激活 venv 并启动后端
├─ activate_frontend_venv.bat     # Windows：启动前端开发服务器
├─ activate_frontend_venv.command # macOS：双击启动前端开发服务器
├─ backend/                       # Python、FastAPI、LangGraph、数据与测试
│  ├─ app/
│  │  ├─ api/
│  │  │  └─ routes/              # FastAPI 路由与请求入口
│  │  ├─ agents/                 # Agent 节点、工具调用与模型逻辑
│  │  ├─ core/                   # 配置、日志和通用基础能力
│  │  ├─ repositories/           # SQLite、向量库等数据访问
│  │  ├─ schemas/                # Pydantic 输入、输出与状态模型
│  │  ├─ services/               # 业务服务与模块编排
│  │  ├─ workflow/               # LangGraph 状态与工作流
│  │  └─ main.py                 # FastAPI 应用入口
│  ├─ data/
│  │  ├─ categories/             # 事项分类目录（category_catalog.json）
│  │  ├─ departments/            # 承办单位职责规则（department_rules.json）
│  │  ├─ mock/                   # Mock 请求（mock_requests.json）与期望结果
│  │  ├─ processed/              # 数据准备脚本生成结果
│  │  ├─ raw/official_work_orders/  # 官方 Excel 与配套录音本机副本
│  │  └─ README.md               # 数据目录说明
│  ├─ scripts/                   # 数据准备和维护脚本（prepare_dataset.py）
│  ├─ storage/                   # SQLite、上传文件等本机运行数据
│  ├─ tests/                     # 后端自动化测试（test_health.py）
│  ├─ .env.example               # 后端环境变量模板，不含真实密钥
│  ├─ requirements.txt           # Python 后端依赖
│  ├─ verify_env.py              # 后端环境检查
│  ├─ check_deepseek.py          # DeepSeek 最小连通性检查（手动执行）
│  └─ README.md                  # 后端工程说明
├─ frontend/                     # React + TypeScript + Vite 前端工程
│  ├─ public/                    # 静态资源（favicon.svg、icons.svg）
│  ├─ src/
│  │  ├─ assets/                 # 图片等静态资源
│  │  ├─ App.tsx                 # 根组件（当前为 Vite 模板页）
│  │  ├─ App.css
│  │  ├─ main.tsx                # 前端入口
│  │  └─ index.css
│  ├─ index.html                 # HTML 模板
│  ├─ .env.example               # 前端非敏感环境变量模板
│  ├─ package.json               # 前端依赖与脚本
│  ├─ package-lock.json          # 前端依赖锁定文件
│  ├─ vite.config.ts             # Vite 配置
│  ├─ tsconfig.json              # TypeScript 基础配置
│  ├─ tsconfig.app.json          # 应用 TS 配置
│  ├─ tsconfig.node.json         # 节点侧 TS 配置
│  ├─ eslint.config.js           # ESLint 配置
│  └─ README.md                  # 前端工程说明
├─ .gitignore                     # 全仓库通用忽略规则
└─ README.md                      # 项目总说明
```

## 后端快速开始

先激活团队最终选定的 Python 项目环境，再从仓库根目录执行：

```powershell
cd backend
python -m pip install -r requirements.txt
python verify_env.py
python -m pytest
python -m uvicorn app.main:app --reload
```

启动后访问：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

后端的 `.env`、依赖和运行命令均以 `backend/` 为工作目录。详细说明见 `backend/README.md`。

## 前端快速开始

前端已初始化为 React + TypeScript + Vite 工程。首次使用时从仓库根目录执行：

```powershell
cd frontend
npm install
npm run dev
```

启动后访问 Vite 输出的本地地址，通常是：

- `http://localhost:5173`

生产构建检查：

```powershell
npm run build
```

前端只允许保存 `VITE_API_BASE_URL` 等非敏感配置，真实模型密钥不得写入前端代码或前端环境变量。

## 数据安全

官方 Excel 与配套录音按类别放入 `backend/data/raw/official_work_orders/`。当前 `prepare_dataset.py` 只匹配并处理 Excel，不会打开、转写或分析录音。

真实密钥只写入 `backend/.env`，不得提交 Git。真实姓名、手机号、身份证号、详细地址、未经授权的录音和未脱敏工单不得进入公开仓库。
