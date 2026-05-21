# 数据布局与配置说明

## 最小配置字段
- `input_path`: 输入数据文件路径。
- `layout`: `wide` 或 `long`。
- `plot_type`: `line`、`scatter`、`line-symbol`、`column`。
- `x_column`: X 列名或列序号。
- `save_project`: 输出 `.opju` 路径。

路径规则：
- 支持绝对路径。
- 也支持相对路径；相对路径会以当前配置 JSON 所在目录为基准解析。

## 宽表配置
额外需要：
- `y_columns`: 需要绘制的 Y 列列表。
- `sample_names`: 可选。若提供，长度必须和 `y_columns` 一致。

## 长表配置
额外需要：
- `y_column`: 数值列。
- `group_column`: 分组列，透视后每个 group 变成一列 Y。
- `sample_names`: 可选。若提供，将按这个顺序重排 group。

## 坐标轴配置
`x_axis` 和 `y_axis` 都支持：
- `name`: 轴名称。
- `unit`: 轴单位，可留空。

脚本会自动拼成 `名称 (单位)` 形式；若 `unit` 为空，只保留名称。

## 图例与 comments
- 每个 Y 列的样品名会写入 Origin 工作表的 `comments` 标签行。
- 图例文本会由同一组样品名重写，确保 Origin 图例和 comments 一致。

## Excel 支持
- `.xlsx` / `.xls` 通过 `pandas.read_excel()` 读取。
- 若缺少 `openpyxl`，脚本会报出明确错误并停止。
