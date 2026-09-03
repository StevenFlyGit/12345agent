"""查看 Chroma 向量库里实际存的内容。

给了 --collection 就直接打印该集合的记录正文，不再只报数量。

用法::

    # 列出各集合条数
    python scripts/inspect_chroma_index.py

    # 看 department_rules 的全部记录
    python scripts/inspect_chroma_index.py --collection department_rules

    # 只看前 3 条
    python scripts/inspect_chroma_index.py -c historical_cases --limit 3

    # 语义检索
    python scripts/inspect_chroma_index.py -c department_rules --query "路灯不亮找谁"

    # 关键词过滤 + 导出成文件
    python scripts/inspect_chroma_index.py -c department_rules --grep 住建
    python scripts/inspect_chroma_index.py -c department_rules --format md -o out.md
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import chromadb  # noqa: E402

from app.rag.retrievers import search_collection  # noqa: E402
from app.rag.vectorstore import CHROMA_DIR, COLLECTIONS, collection_counts  # noqa: E402


def to_jsonable(value):
    """metadata 里的列表字段是以字符串存的 JSON，这里还原成列表方便阅读。"""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return value
    return value


def fetch(collection_name: str, limit: int = 0, grep: str | None = None) -> list[dict]:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        col = client.get_collection(collection_name)
    except Exception as exc:  # 集合不存在时 chromadb 抛 ValueError
        raise SystemExit(f"集合不存在或无法打开：{collection_name}（{exc}）")

    total = col.count()
    if total == 0:
        return []

    result = col.get(limit=total, include=["documents", "metadatas"])
    ids = result.get("ids") or []
    records = []
    for idx, (doc, meta) in enumerate(zip(result["documents"], result["metadatas"])):
        records.append(
            {
                "id": ids[idx] if idx < len(ids) else "",
                "document": doc or "",
                "metadata": {k: to_jsonable(v) for k, v in (meta or {}).items()},
            }
        )

    if grep:
        keyword = grep.lower()
        records = [
            r
            for r in records
            if keyword in (r["document"] or "").lower()
            or keyword in json.dumps(r["metadata"], ensure_ascii=False).lower()
        ]

    if limit and limit > 0:
        records = records[:limit]
    return records


def render_text(collection_name: str, records: list[dict]) -> str:
    lines = [f"collection: {collection_name}（{len(records)} 条）", ""]
    for i, r in enumerate(records, 1):
        lines.append(f"----- [{i}] id={r['id']} -----")
        for key, value in r["metadata"].items():
            lines.append(f"{key}: {value}")
        lines.append("document:")
        lines.append(r["document"])
        lines.append("")
    return "\n".join(lines)


def render_md(collection_name: str, records: list[dict]) -> str:
    lines = [f"# collection: {collection_name}", "", f"共 {len(records)} 条记录", ""]
    for i, r in enumerate(records, 1):
        title = r["metadata"].get("category_name") or r["metadata"].get("title") or r["id"]
        lines.append(f"## {i}. {title}")
        lines.append("")
        lines.append("| 字段 | 值 |")
        lines.append("| --- | --- |")
        for key, value in r["metadata"].items():
            cell = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value)
            lines.append(f"| {key} | {cell.replace('|', '/')} |")
        lines.append("")
        lines.append("```text")
        lines.append(r["document"])
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def render_json(collection_name: str, records: list[dict]) -> str:
    return json.dumps(
        {"collection": collection_name, "count": len(records), "records": records},
        ensure_ascii=False,
        indent=2,
    )


def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def render_html(collection_name: str, records: list[dict]) -> str:
    """生成单文件自包含 HTML，便于在浏览器里浏览和搜索。"""
    cards = []
    for i, r in enumerate(records, 1):
        meta = r["metadata"]
        title = meta.get("category_name") or meta.get("title") or r["id"]

        rows = []
        for key, value in meta.items():
            if isinstance(value, list):
                cell = "".join(f'<span class="chip">{_esc(v)}</span>' for v in value)
            else:
                cell = _esc(value)
            rows.append(f"<tr><th>{_esc(key)}</th><td>{cell}</td></tr>")

        haystack = _esc((r["document"] + json.dumps(meta, ensure_ascii=False)).lower())
        cards.append(
            f"""    <article class="card" data-search="{haystack}">
      <div class="card-head"><span class="idx">{i}</span><h2>{_esc(title)}</h2></div>
      <table class="meta">{''.join(rows)}</table>
      <div class="doc-label">document</div>
      <pre>{_esc(r['document'])}</pre>
    </article>"""
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{_esc(collection_name)} - Chroma 内容</title>
<style>
  :root {{ --bg:#f6f7f9; --card:#fff; --line:#e3e6ea; --text:#1f2328; --muted:#6b7280; --accent:#2e5cff; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:0 0 48px; background:var(--bg); color:var(--text);
         font:14px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }}
  header {{ position:sticky; top:0; background:#fff; border-bottom:1px solid var(--line);
            padding:16px 24px; display:flex; align-items:center; gap:16px; flex-wrap:wrap; }}
  h1 {{ font-size:16px; margin:0; font-weight:600; }}
  .count {{ color:var(--muted); font-size:13px; }}
  #q {{ flex:1; min-width:240px; padding:7px 12px; border:1px solid var(--line);
        border-radius:8px; font-size:13px; outline:none; }}
  #q:focus {{ border-color:var(--accent); }}
  main {{ max-width:960px; margin:24px auto; padding:0 24px; display:flex; flex-direction:column; gap:16px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px 20px; }}
  .card-head {{ display:flex; align-items:center; gap:10px; margin-bottom:12px; }}
  .idx {{ width:24px; height:24px; border-radius:6px; background:#eef1fe; color:var(--accent);
          font-size:12px; display:flex; align-items:center; justify-content:center; flex:none; }}
  .card h2 {{ font-size:15px; margin:0; font-weight:600; }}
  table.meta {{ width:100%; border-collapse:collapse; margin-bottom:12px; }}
  table.meta th {{ width:150px; text-align:left; vertical-align:top; padding:5px 12px 5px 0;
                   color:var(--muted); font-weight:500; font-size:12.5px; white-space:nowrap; }}
  table.meta td {{ padding:5px 0; }}
  .chip {{ display:inline-block; background:#f1f3f5; border-radius:5px; padding:1px 7px;
           margin:0 5px 4px 0; font-size:12px; color:#40474f; }}
  .doc-label {{ font-size:12px; color:var(--muted); margin-bottom:6px; }}
  pre {{ margin:0; background:#fafbfc; border:1px solid var(--line); border-radius:8px;
         padding:12px 14px; white-space:pre-wrap; word-break:break-word; font-size:13px; }}
  .empty {{ color:var(--muted); text-align:center; padding:40px 0; }}
</style>
</head>
<body>
<header>
  <h1>collection: {_esc(collection_name)}</h1>
  <span class="count">共 {len(records)} 条</span>
  <input id="q" type="search" placeholder="搜索关键词、部门、正文…">
</header>
<main id="list">
{chr(10).join(cards)}
</main>
<div class="empty" id="empty" hidden>没有匹配的记录</div>
<script>
  var q = document.getElementById('q');
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var empty = document.getElementById('empty');
  q.addEventListener('input', function () {{
    var kw = q.value.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (c) {{
      var hit = !kw || c.dataset.search.indexOf(kw) !== -1;
      c.hidden = !hit;
      if (hit) shown++;
    }});
    empty.hidden = shown !== 0;
  }});
</script>
</body>
</html>
"""


RENDERERS = {
    "text": render_text,
    "md": render_md,
    "json": render_json,
    "html": render_html,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="查看 Chroma 向量库里存储的内容")
    parser.add_argument(
        "-c",
        "--collection",
        choices=COLLECTIONS,
        default=None,
        help="要查看的集合；不传则只列出各集合条数",
    )
    parser.add_argument("--query", default="", help="语义检索文本，给了就走检索而不是全量 dump")
    parser.add_argument("--top-k", type=int, default=3, help="检索返回条数")
    parser.add_argument("--limit", type=int, default=0, help="只显示前 N 条，0 表示全部")
    parser.add_argument("--grep", default=None, help="按关键词过滤 document 或 metadata")
    parser.add_argument(
        "--format",
        choices=RENDERERS.keys(),
        default="text",
        help="输出格式；html 会生成带搜索框的单文件页面，建议配合 -o 使用",
    )
    parser.add_argument("-o", "--out", default=None, help="输出到文件，默认打印到终端")
    parser.add_argument("--list", action="store_true", help="只列出各集合条数")
    args = parser.parse_args()

    if not args.collection or args.list:
        print("各 collection 条数：")
        for name, count in collection_counts().items():
            print(f"- {name}: {count}")
        if args.collection is None:
            print("\n要查看内容请用 -c 指定集合，例如：")
            print("  python scripts/inspect_chroma_index.py -c department_rules --limit 3")
        return

    if args.query:
        print(f"检索 collection={args.collection}, query={args.query}")
        for hit in search_collection(args.collection, args.query, top_k=args.top_k):
            source = hit.metadata.get("source_name") or hit.metadata.get("source_file")
            print("-" * 60)
            print(f"score: {hit.score}")
            print(f"source: {source}")
            print(hit.content[:500])
        return

    records = fetch(args.collection, args.limit, args.grep)
    output = RENDERERS[args.format](args.collection, records)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"已写入 {out_path}（{len(records)} 条）")
    else:
        print(output)


if __name__ == "__main__":
    main()
