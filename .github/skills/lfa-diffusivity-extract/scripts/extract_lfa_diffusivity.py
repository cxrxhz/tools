from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable

ENCODINGS = ("utf-8-sig", "gbk", "utf-16", "utf-8", "latin-1")
OUTPUT_COLUMNS = [
    "sample_number",
    "material_raw",
    "material_label",
    "sample",
    "sample_position",
    "date",
    "thickness_mm",
    "diameter_mm",
    "mean_diffusivity_mm2_s",
    "stddev_diffusivity_mm2_s",
    "source_file",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批量提取 LFA CSV 中的热扩散率汇总结果。"
    )
    parser.add_argument("input_dir", help="原始 LFA CSV 所在目录")
    parser.add_argument(
        "--output",
        help="输出 CSV 路径，默认写到输入目录下的 extracted_lfa_diffusivity.csv",
    )
    parser.add_argument(
        "--pattern",
        default="*.csv",
        help="文件匹配模式，默认 *.csv",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="是否递归搜索子目录",
    )
    return parser.parse_args()


def read_rows(file_path: Path) -> list[list[str]]:
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        try:
            with file_path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.reader(handle))
        except UnicodeError as exc:
            last_error = exc
    raise UnicodeError(
        f"无法用预设编码读取文件: {file_path}. 最后一次错误: {last_error}"
    )


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_number_from_name(file_path: Path) -> int | None:
    match = re.match(r"(\d+)", file_path.stem.strip())
    if not match:
        return None
    return int(match.group(1))


def split_material(material_raw: str | None) -> str | None:
    if not material_raw:
        return None
    parts = [part.strip() for part in material_raw.split("-", 1)]
    if len(parts) == 2:
        return parts[1]
    return material_raw.strip()


def extract_record(file_path: Path) -> dict[str, object]:
    fields: dict[str, str] = {}
    mean_diffusivity = None
    stddev_diffusivity = None

    for row in read_rows(file_path):
        if not row:
            continue
        key = row[0].strip()
        value = row[1].strip() if len(row) > 1 else ""
        if key.startswith("#Mean"):
            mean_diffusivity = to_float(row[3] if len(row) > 3 else None)
        elif key.startswith("#Std_Dev"):
            stddev_diffusivity = to_float(row[3] if len(row) > 3 else None)
        elif key.startswith("#"):
            fields[key] = value

    return {
        "sample_number": parse_number_from_name(file_path),
        "material_raw": fields.get("#Material"),
        "material_label": split_material(fields.get("#Material")),
        "sample": fields.get("#Sample"),
        "sample_position": fields.get("#Sample position"),
        "date": fields.get("#Date"),
        "thickness_mm": to_float(fields.get("#Thickness_RT/mm")),
        "diameter_mm": to_float(fields.get("#Diameter/mm")),
        "mean_diffusivity_mm2_s": mean_diffusivity,
        "stddev_diffusivity_mm2_s": stddev_diffusivity,
        "source_file": str(file_path),
    }


def iter_input_files(input_dir: Path, pattern: str, recursive: bool) -> Iterable[Path]:
    if recursive:
        yield from sorted(input_dir.rglob(pattern))
    else:
        yield from sorted(input_dir.glob(pattern))


def sort_key(record: dict[str, object]) -> tuple[int, str]:
    sample_number = record.get("sample_number")
    if isinstance(sample_number, int):
        return (sample_number, str(record["source_file"]))
    return (10**9, str(record["source_file"]))


def write_output(records: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"输入目录不存在: {input_dir}")

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_dir / "extracted_lfa_diffusivity.csv"
    )

    records: list[dict[str, object]] = []
    failed_files: list[str] = []

    for file_path in iter_input_files(input_dir, args.pattern, args.recursive):
        try:
            record = extract_record(file_path)
        except Exception as exc:  # noqa: BLE001
            failed_files.append(f"{file_path}: {exc}")
            continue

        if record["mean_diffusivity_mm2_s"] is None:
            failed_files.append(f"{file_path}: 缺少 #Mean 热扩散率")
            continue
        records.append(record)

    records.sort(key=sort_key)
    write_output(records, output_path)

    print(f"成功提取 {len(records)} 个文件 -> {output_path}")
    if records:
        print("前 5 条结果预览:")
        for record in records[:5]:
            print(
                "  编号={sample_number}, 样品={material_label}, α={mean_diffusivity_mm2_s}, 文件={source_file}".format(
                    **record
                )
            )
    if failed_files:
        print("\n以下文件未成功提取:")
        for item in failed_files:
            print(f"  - {item}")

    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
