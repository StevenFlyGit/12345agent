# 12345 热线工单智能生成与转派辅助智能体

本项目用于开发“12345 热线工单智能生成与转派辅助智能体”，基础流程为：输入诉求 → 诉求理解 → 工单生成 → 事项分类与承办单位推荐 → 回复辅助。系统输出仅供人工参考，最终工单内容和转派结果必须由工作人员确认。

## 当前项目骨架

- `app/`：FastAPI 接口、数据结构、服务、工作流和数据访问代码。
- `data/`：官方 Excel 副本、标准化结果、分类目录、单位职责规则和 Mock 数据。
- `scripts/prepare_dataset.py`：只读取 Excel 的数据准备脚本，不处理录音。
- `tests/`：自动化测试。
- `storage/`：本机数据库、向量索引和运行文件，不提交 Git。

## Windows 快速开始

```powershell
# .conda 是当前项目内的 Conda 环境目录
conda activate .\.conda
python -m pip install -r requirements.txt
python verify_env.py
python -m uvicorn app.main:app --reload
```

## macOS 快速开始

```bash
# .conda 是当前项目内的 Conda 环境目录
conda activate ./.conda
python -m pip install -r requirements.txt
python verify_env.py
python -m uvicorn app.main:app --reload
```

启动后访问 `http://127.0.0.1:8000/health` 和 `http://127.0.0.1:8000/docs`。

## 配置大模型

`.env.example` 可以提交到仓库，其中只放占位值；本机 `.env` 已使用 DeepSeek 兼容接口作为示例，但 `LLM_API_KEY` 仍是占位值。请自行填写真实密钥，切勿将 `.env`、密钥、包含个人信息的工单或未经授权的录音提交到 Git。

## 准备官方 Excel

把官方 Excel 按类别目录复制到 `data/raw/official_work_orders/`，然后执行：

```powershell
# data/raw/official_work_orders 是官方 Excel 副本目录
python scripts\prepare_dataset.py data\raw\official_work_orders
```

标准化结果会写入 `data/processed/work_orders.jsonl`。历史办理单位和历史答复仅作案例参考，不代表当前权责或政策结论。
