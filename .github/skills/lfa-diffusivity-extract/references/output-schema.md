# 输出字段说明

## 字段
- `sample_number`: 从文件名开头解析出的编号，用于排序。
- `material_raw`: 原始 `#Material` 文本，例如 `1 - B1`。
- `material_label`: 从 `material_raw` 拆出的标签部分，例如 `B1`。
- `sample`: `#Sample` 字段。
- `sample_position`: `#Sample position` 字段。
- `date`: `#Date` 字段。
- `thickness_mm`: `#Thickness_RT/mm`。
- `diameter_mm`: `#Diameter/mm`。
- `mean_diffusivity_mm2_s`: `#Mean` 行第 4 列热扩散率。
- `stddev_diffusivity_mm2_s`: `#Std_Dev` 行第 4 列标准差。
- `source_file`: 原始 CSV 完整路径。

## 约束
- 若文件缺少 `#Mean`，脚本不会把该文件写入结果表。
- 若文件名没有可解析编号，`sample_number` 为空，该文件会排到结果表末尾。
- 默认输出编码是 `utf-8-sig`，便于 Excel 和 Origin 直接打开。
