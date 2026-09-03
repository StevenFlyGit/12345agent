# 12345Agent-New 改造前基线测试结果

## 测试目的

在接入 LangChain、LangGraph、Chroma RAG 之前，先确认当前旧版串行工作流可以稳定跑通。后续每完成一个改造阶段，都应重新运行同一批测试。如果原本通过的测试在改造后失败，就说明新改造影响了既有能力，需要优先修复。

## 测试时间

2026-09-02

## 测试范围

本次基线测试覆盖当前项目已有的 API 闭环与业务边界场景：

- 后端健康检查
- 文本创建案件
- 工单生成
- 事项分类
- 承办单位推荐
- 回复辅助生成
- 人工审核确认
- 案件详情回看
- 样例文本与样例录音列表
- 官方样例录音文件名精确匹配
- 未知录音模拟转写兜底
- 历史案例检索
- 信息缺失澄清提示
- 紧急事项识别
- 重复反映识别
- 市场监管、交通运输、卫生健康等分类抽样

## 基线检查项

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 项目内 git 状态 | 通过 | `12345Agent-New` 下无未提交变更输出 |
| 编排文件模型导入 | 通过 | `app/workflow/orchestrator.py` 已显式导入 `CaseInput`、`CaseState`、`ClassificationResult`、`ReplyResult`、`WorkOrder` |
| 依赖冲突检查 | 通过 | `pip check` 输出 `No broken requirements found.` |
| 关键依赖导入 | 通过 | `fastapi`、`langchain`、`langgraph`、`chromadb`、`langchain_chroma`、`pandas`、`openpyxl`、`pydantic` 均可正常导入 |
| 现有测试用例 | 通过 | `14 passed in 2.45s` |

## 执行命令

在 `12345Agent-New/backend` 目录下执行：

```powershell
.\venv\Scripts\python.exe -m pip check
```

结果：

```text
No broken requirements found.
```

关键依赖导入检查：

```powershell
.\venv\Scripts\python.exe -c 'import fastapi, langchain, langgraph, chromadb, langchain_chroma, pandas, openpyxl, pydantic; print("critical imports ok")'
```

结果：

```text
critical imports ok
```

现有测试用例：

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\venv\Scripts\python.exe -m pytest tests -q
```

结果：

```text
..............                                                           [100%]
14 passed in 2.45s
```

## 结论

当前旧版串行 workflow 的核心 API 和主要业务场景均可稳定跑通，可以作为后续 LangChain、LangGraph、Chroma RAG 改造的基线。后续改造应优先保持这些接口和行为不回退，再逐步增加 RAG 检索依据、LangGraph 状态追踪、人工审核断点和教学扩展能力。

