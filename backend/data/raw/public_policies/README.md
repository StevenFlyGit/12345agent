# 自采政府公开文件入口

将自行收集的政府部门公开文件放在本目录下，建议按主题或部门建立子目录。

每个文件必须配套一个同名 `.meta.json`，例如：

```text
housing/
  芜湖市物业管理办法.pdf
  芜湖市物业管理办法.meta.json
```

`.meta.json` 示例：

```json
{
  "source_name": "芜湖市物业管理办法",
  "source_url": "https://...",
  "publisher": "芜湖市住房和城乡建设局",
  "published_at": "2025-xx-xx",
  "collected_at": "2026-09-02",
  "category_name": "城乡建设",
  "doc_type": "policy",
  "sensitive_level": "public_demo",
  "usage_scope": "仅用于赛事演示和政策依据检索"
}
```

构建索引前可先运行：

```powershell
python scripts/validate_policy_sources.py
```

