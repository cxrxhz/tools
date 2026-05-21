---
name: origin-generic-plot
description: '调用 originpro / Origin 从任意数据来源画图。Use when 用户要用 Origin 画图、originpro 自动作图、点线图/散点图/折线图/柱状图、设置横纵坐标名称与单位、处理多组数据、把样品名写入注释列 comments 并同步图例。'
argument-hint: '输入文件、表结构（宽表/长表）、图类型、轴名单位、样品名、输出 opju 路径'
user-invocable: true
---

# Origin 通用绘图

这个 skill 负责把任意来源的数据规范化后送入 Origin，并生成可继续编辑的 `.opju` 工程。

## 适用场景
- 用户说“调用 Origin 画图”。
- 用户要画散点图、折线图、点线图、柱状图。
- 用户要求指定横纵坐标名称和单位。
- 用户有多组数据，需要把每组样品名写到 Origin 工作表的注释列，并在图例中显示。
- 用户数据来自 CSV、TSV、TXT，或 Excel（若环境具备 `openpyxl`）。

## 支持的数据布局
- 宽表：一列 X，多列 Y，每列 Y 代表一个样品。
- 长表：一列 X、一列 Y、一列 group，脚本会先透视成宽表再送入 Origin。

## 核心行为
- 将 X/Y 数据写入 Origin 工作表。
- 将每组样品名写入对应 Y 列的 `comments` 标签行。
- 用同一组样品名重写图例文本，避免图例和注释列不一致。
- 允许设置图类型、轴标题、轴单位、工作表名、图页名、是否显示 Origin。
- 可额外导出一份“归一化后的宽表 CSV”，便于追踪作图输入。

## 工作流程
1. 判断用户数据是宽表还是长表。
2. 生成配置 JSON，字段说明见 [数据布局与配置说明](./references/data-layouts.md)。
3. 运行 [Origin 绘图脚本](./scripts/plot_with_origin.py)。
4. 校验 `.opju` 是否成功保存，检查轴标题、图类型、图例文本是否符合要求。

## 运行约定
- 图类型支持：`line`、`scatter`、`line-symbol`、`column`，也兼容常见中文别名。
- 多组数据时，`sample_names` 的顺序必须和 Y 列顺序一致。
- 若使用 Excel，而环境中缺少 `openpyxl`，先报清楚依赖缺失，再给出安装命令。
- 若用户没有单独给样品名，宽表默认使用 Y 列列名，长表默认使用 `group_column` 中的分组名。

## 推荐资源
- [Origin 绘图脚本](./scripts/plot_with_origin.py)
- [宽表示例配置](./assets/config-wide.example.json)
- [长表示例配置](./assets/config-long.example.json)
- [数据布局与配置说明](./references/data-layouts.md)
