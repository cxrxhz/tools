---
name: lfa-diffusivity-extract
description: '批量提取 LFA / laser flash CSV 中每个编号样品的热扩散率。Use when 用户要提取 LFA、热扩散率、激光闪射结果、#Mean/#Std_Dev、批量整理 LFA 数据，或要把 LFA 原始 CSV 先规范化后再用于 Origin/作图。'
argument-hint: '输入目录、输出路径、是否递归、CSV 命名规则'
user-invocable: true
---

# LFA 热扩散率提取

这个 skill 负责把一批 LFA 原始 CSV 规范化成一个可复用结果表，默认只做数据提取与清洗，不直接画图。

## 适用场景
- 用户说“批量提取 LFA 结果”。
- 用户说“从激光闪射 CSV 提取热扩散率”。
- 用户给出一个目录，希望按编号整理 `#Mean` 和 `#Std_Dev`。
- 用户后续还要进 Origin 作图，需要先得到干净的汇总表。

## 产出
- 一个规范化 CSV，至少包含：编号、样品信息、样品位置、平均热扩散率、标准差、源文件路径。
- 控制台摘要，说明成功提取的文件数、缺失字段、输出路径。

## 工作流程
1. 先抽查 1 个原始 CSV，确认字段模式是否包含 `#Material`、`#Mean`、`#Std_Dev`。
2. 运行 [提取脚本](./scripts/extract_lfa_diffusivity.py)。
3. 校验输出记录数是否和输入文件数一致，重点检查编号排序、空值和编码问题。
4. 如果用户下一步要在 Origin 中画图，继续调用 `origin-generic-plot` skill，不要在本 skill 中混入 Origin 逻辑。

## 运行约定
- 默认按文件名开头的数字作为样品编号排序，例如 `1 1.csv`、`2-3.csv`。
- 默认尝试多种编码：`utf-8-sig`、`gbk`、`utf-16`、`utf-8`、`latin-1`。
- 如果 `#Material` 形如 `1 - B1`，脚本会同时拆出编号部分和样品标签部分。
- 若某个文件缺少 `#Mean`，该文件会被标记到错误输出并在终端摘要中提示。

## 推荐命令
```powershell
python .github/skills/lfa-diffusivity-extract/scripts/extract_lfa_diffusivity.py "F:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22"
```

## 参考
- [输出字段说明](./references/output-schema.md)
- [提取脚本](./scripts/extract_lfa_diffusivity.py)
