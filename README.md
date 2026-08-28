# 12345 热线工单智能生成与转派辅助智能体

本项目用于开发“12345 热线工单智能生成与转派辅助智能体”，基础闭环为：录音或文本输入 → 诉求理解与要素确认 → 标准化工单生成 → 事项分类与承办单位推荐 → 人工审核 → 处理结果录入 → 回复与回访话术辅助。

系统只提供辅助建议，最终工单内容、转派结果和群众回复必须由工作人员审核确认。

## 项目结构

```text
12345agent/
├─ backend/                    # Python、FastAPI、LangGraph、数据与测试
│  ├─ app/
│  │  ├─ api/                 # HTTP 接口与路由
│  │  ├─ agents/              # Agent 节点、工具调用与模型逻辑
│  │  ├─ core/                # 配置、日志和通用基础能力
│  │  ├─ repositories/        # SQLite、向量库等数据访问
│  │  ├─ schemas/             # Pydantic 输入、输出与状态模型
│  │  ├─ services/            # 业务服务与模块编排
│  │  ├─ workflow/            # LangGraph 状态与工作流
│  │  └─ main.py              # FastAPI 应用入口
│  ├─ data/                   # 原始数据、标准化数据、目录和 Mock 数据
│  ├─ scripts/                # 数据准备和维护脚本
│  ├─ tests/                  # 后端自动化测试
│  ├─ .env.example            # 后端环境变量模板，不含真实密钥
│  ├─ requirements.txt        # Python 后端依赖
│  ├─ verify_env.py           # 后端环境检查
│  └─ check_deepseek.py       # DeepSeek 最小连通性检查（手动执行）
├─ frontend/                   # Web 前端工程预留目录
│  └─ README.md               # 前端初始化边界与后续规划
├─ .gitignore                  # 全仓库通用忽略规则
└─ README.md                   # 项目总说明
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

## 前端状态

`frontend/` 目前只保留目录说明，尚未创建 React、TypeScript、Vite、`package.json` 或 `node_modules`。完成前端环境学习后，再在该目录中初始化前端项目，不要把前端依赖安装到仓库根目录或 `backend/`。

## 数据安全

官方 Excel 与配套录音按类别放入 `backend/data/raw/official_work_orders/`。当前 `prepare_dataset.py` 只匹配并处理 Excel，不会打开、转写或分析录音。

真实密钥只写入 `backend/.env`，不得提交 Git。真实姓名、手机号、身份证号、详细地址、未经授权的录音和未脱敏工单不得进入公开仓库。
