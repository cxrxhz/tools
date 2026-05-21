from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import originpro as op
import sys

if hasattr(op, "excepthook"):
    sys.excepthook = op.excepthook

PLOT_TYPE_ALIASES = {
    "line": "line",
    "折线图": "line",
    "scatter": "scatter",
    "散点图": "scatter",
    "line-symbol": "line-symbol",
    "点线图": "line-symbol",
    "折线散点": "line-symbol",
    "column": "column",
    "柱状图": "column",
}
PLOT_TO_ORIGIN = {
    "line": "l",
    "scatter": "s",
    "line-symbol": "y",
    "column": "c",
}
TEMPLATE_BY_TYPE = {
    "line": "line",
    "scatter": "scatter",
    "line-symbol": "scatter",
    "column": "column",
}


class ConfigError(ValueError):
    pass


def resolve_path(path_value: str, base_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据配置文件调用 Origin 绘图。")
    parser.add_argument("--config", required=True, help="JSON 配置文件路径")
    parser.add_argument(
        "--keep-origin-open",
        action="store_true",
        help="执行完成后不主动关闭 Origin",
    )
    return parser.parse_args()


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ConfigError("配置文件顶层必须是 JSON 对象")
    config["__config_dir__"] = str(config_path.parent)
    return config


def normalize_plot_type(value: str) -> str:
    key = str(value).strip().lower()
    if key not in PLOT_TYPE_ALIASES:
        raise ConfigError(f"不支持的图类型: {value}")
    return PLOT_TYPE_ALIASES[key]


def resolve_column(df: pd.DataFrame, column: Any) -> str:
    if isinstance(column, int):
        try:
            return str(df.columns[column])
        except IndexError as exc:
            raise ConfigError(f"列序号越界: {column}") from exc
    if column not in df.columns:
        raise ConfigError(f"找不到列: {column}")
    return str(column)


def build_axis_title(axis_config: dict[str, Any], fallback: str) -> str:
    name = str(axis_config.get("name") or fallback).strip()
    unit = str(axis_config.get("unit") or "").strip()
    return f"{name} ({unit})" if unit else name


def to_origin_list(series: pd.Series) -> list[Any]:
    values: list[Any] = []
    for value in series.tolist():
        if pd.isna(value):
            values.append(None)
        else:
            values.append(value)
    return values


def load_dataframe(config: dict[str, Any]) -> pd.DataFrame:
    base_dir = Path(config["__config_dir__"])
    input_path = resolve_path(config["input_path"], base_dir)
    suffix = input_path.suffix.lower()
    if not input_path.exists():
        raise ConfigError(f"输入文件不存在: {input_path}")

    if suffix in {".csv", ".txt", ".dat"}:
        sep = config.get("sep")
        if not sep:
            sep = "\t" if suffix == ".txt" else ","
        return pd.read_csv(input_path, sep=sep)

    if suffix == ".tsv":
        return pd.read_csv(input_path, sep="\t")

    if suffix in {".xls", ".xlsx"}:
        try:
            return pd.read_excel(input_path, sheet_name=config.get("sheet_name", 0))
        except ImportError as exc:
            raise ConfigError(
                "读取 Excel 需要 openpyxl。当前环境缺少该依赖，请先安装后再运行。"
            ) from exc

    raise ConfigError(f"暂不支持的输入文件类型: {suffix}")


def normalize_wide_layout(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, list[str], str]:
    x_column = resolve_column(df, config["x_column"])
    y_columns = [resolve_column(df, col) for col in config["y_columns"]]
    sample_names = config.get("sample_names") or y_columns
    if len(sample_names) != len(y_columns):
        raise ConfigError("sample_names 的长度必须和 y_columns 一致")

    normalized = df[[x_column, *y_columns]].copy()
    normalized = normalized.dropna(how="all", subset=y_columns)
    normalized.columns = [x_column, *sample_names]
    return normalized, [str(name) for name in sample_names], x_column


def normalize_long_layout(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, list[str], str]:
    x_column = resolve_column(df, config["x_column"])
    y_column = resolve_column(df, config["y_column"])
    group_column = resolve_column(df, config["group_column"])

    working = df[[x_column, y_column, group_column]].copy()
    working.columns = ["x", "y", "group"]
    working = working.dropna(subset=["x", "y", "group"])

    discovered_order = [str(item) for item in working["group"].drop_duplicates().tolist()]
    sample_names = [str(item) for item in config.get("sample_names") or discovered_order]

    pivot = (
        working.pivot_table(index="x", columns="group", values="y", aggfunc="mean")
        .reset_index()
    )

    missing_groups = [name for name in sample_names if name not in pivot.columns]
    if missing_groups:
        raise ConfigError(f"以下 sample_names 在数据中不存在: {missing_groups}")

    ordered_columns = ["x", *sample_names]
    pivot = pivot.loc[:, ordered_columns]
    pivot.columns = [x_column, *sample_names]
    return pivot, sample_names, x_column


def normalize_dataframe(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, list[str], str]:
    layout = str(config.get("layout", "wide")).strip().lower()
    if layout == "wide":
        return normalize_wide_layout(df, config)
    if layout == "long":
        return normalize_long_layout(df, config)
    raise ConfigError(f"不支持的 layout: {layout}")


def export_normalized_csv(df: pd.DataFrame, config: dict[str, Any]) -> None:
    output_path = config.get("normalized_output_csv")
    if not output_path:
        return
    base_dir = Path(config["__config_dir__"])
    csv_path = resolve_path(output_path, base_dir)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")


def build_legend_text(sample_names: list[str]) -> str:
    lines = [f"\\l({index}) {name}" for index, name in enumerate(sample_names, start=1)]
    return "\n".join(lines)


def save_project_path(config: dict[str, Any]) -> Path:
    base_dir = Path(config["__config_dir__"])
    if config.get("save_project"):
        return resolve_path(config["save_project"], base_dir)
    input_path = resolve_path(config["input_path"], base_dir)
    return input_path.with_name(f"{input_path.stem}_origin_plot.opju")


def create_origin_plot(df: pd.DataFrame, sample_names: list[str], x_column: str, config: dict[str, Any]) -> Path:
    plot_type = normalize_plot_type(config.get("plot_type", "line-symbol"))
    x_axis_title = build_axis_title(config.get("x_axis", {}), x_column)
    y_axis_title = build_axis_title(config.get("y_axis", {}), "Y")
    worksheet_name = str(config.get("worksheet_name") or "Origin Plot Data")
    graph_name = str(config.get("graph_name") or "Origin Plot")
    show_origin = bool(config.get("show_origin", False))

    op.set_show(show_origin)

    wks = op.new_sheet("w", lname=worksheet_name)
    x_series = pd.Series(df.iloc[:, 0])
    wks.from_list(0, to_origin_list(x_series), lname=x_axis_title, axis="X")

    y_column_indices: list[int] = []
    for offset, sample_name in enumerate(sample_names, start=1):
        y_series = pd.to_numeric(df.iloc[:, offset], errors="coerce")
        wks.from_list(
            offset,
            to_origin_list(y_series),
            lname=y_axis_title,
            comments=sample_name,
            axis="Y",
        )
        y_column_indices.append(offset)

    graph = op.new_graph(lname=graph_name, template=TEMPLATE_BY_TYPE[plot_type])
    layer = graph[0]
    for column_index in y_column_indices:
        layer.add_plot(wks, column_index, 0, type=PLOT_TO_ORIGIN[plot_type])

    layer.axis("x").title = x_axis_title
    layer.axis("y").title = y_axis_title
    layer.rescale()

    legend = layer.label("Legend")
    if legend is not None:
        legend.text = build_legend_text(sample_names)

    save_path = save_project_path(config)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    op.save(str(save_path))
    return save_path


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    config = load_config(config_path)
    dataframe = load_dataframe(config)
    normalized_df, sample_names, x_column = normalize_dataframe(dataframe, config)
    export_normalized_csv(normalized_df, config)

    save_path: Path | None = None
    try:
        save_path = create_origin_plot(normalized_df, sample_names, x_column, config)
        print(f"Origin 工程已保存: {save_path}")
        print(f"数据组数: {len(sample_names)}")
        print(f"样品名: {sample_names}")
        return 0
    finally:
        if not args.keep_origin_open and op and op.oext:
            op.exit()


if __name__ == "__main__":
    raise SystemExit(main())
