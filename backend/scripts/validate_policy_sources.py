"""校验自采政府公开文件及 .meta.json。"""
from __future__ import annotations

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.rag.policy_loaders import POLICY_ROOT, validate_policy_sources


def main() -> None:
    issues = validate_policy_sources()
    print(f"自采文件目录：{POLICY_ROOT}")
    if not issues:
        print("未发现需要处理的问题。")
        return

    for issue in issues:
        print(f"[{issue.level}] {issue.file}: {issue.message}")


if __name__ == "__main__":
    main()

