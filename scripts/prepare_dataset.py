import argparse
import json
import re
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "信件编号",
    "受理时间",
    "来源",
    "主题",
    "内容",
    "办理单位",
    "答复内容",
    "区域",
]


def text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def split_departments(value: object) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[、,，;/；]+", text(value))
        if item.strip()
    ]


def prepare(source_dir: Path, output_file: Path) -> None:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"数据目录不存在：{source_dir}")

    excel_files = sorted(source_dir.rglob("*.xlsx"))
    if not excel_files:
        raise FileNotFoundError(f"目录中未找到 Excel：{source_dir}")

    records: list[dict] = []
    for excel_file in excel_files:
        # 第一行是“综合查询”标题，第二行才是字段名。
        frame = pd.read_excel(excel_file, header=1, dtype=str)
        missing = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
        if missing:
            raise ValueError(f"{excel_file} 缺少字段：{missing}")

        for row in frame[REQUIRED_COLUMNS].to_dict(orient="records"):
            title = text(row["主题"])
            records.append(
                {
                    "source_id": text(row["信件编号"]),
                    "accepted_at": text(row["受理时间"]),
                    "source_channel": text(row["来源"]),
                    "title": title,
                    "request_content": text(row["内容"]),
                    "handling_departments": split_departments(row["办理单位"]),
                    "reply_content": text(row["答复内容"]),
                    "region": text(row["区域"]),
                    "category": excel_file.parent.name,
                    "urgent": "加急" in title,
                    "repeat_request": "再次反映" in title,
                    "source_file": excel_file.name,
                }
            )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"读取 Excel：{len(excel_files)} 个")
    print(f"生成工单：{len(records)} 条")
    print(f"输出文件：{output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="只整理官方 Excel，不处理录音。")
    # source_dir 是只含官方 Excel 副本的目录。
    parser.add_argument("source_dir", type=Path)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    prepare(
        args.source_dir,
        project_root / "data" / "processed" / "work_orders.jsonl",
    )
