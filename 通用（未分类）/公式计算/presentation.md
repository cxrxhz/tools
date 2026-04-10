---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section {
    background-color: #fbfdff;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    color: #2c3e50;
  }
  h1, h2, h3 {
    color: #1a5276;
    font-weight: 600;
  }
  .lead-slide {
    text-align: center;
    background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
    color: white;
  }
  .lead-slide h1 {
    color: white;
    font-size: 3em;
    margin-bottom: 20px;
    letter-spacing: 2px;
  }
  .lead-slide h3 {
    color: #e8f8f5;
    font-weight: 400;
    font-size: 1.5em;
  }
  .highlight {
    color: #c0392b;
    font-weight: bold;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
  }
  th {
    background-color: #1a5276;
    color: white;
    padding: 12px;
  }
  td {
    padding: 12px;
    border-bottom: 1px solid #ddd;
    background-color: white;
  }
  .card {
    background: white;
    border-left: 5px solid #2980b9;
    padding: 15px;
    margin: 15px 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    border-radius: 4px;
  }
  .footer {
    position: absolute;
    bottom: 20px;
    left: 40px;
    font-size: 0.5em;
    color: #7f8c8d;
  }
---

<!-- _class: lead-slide -->

# 智能公式计算与推导系统
### 基于 SymPy 的自动化表达式解析与渲染方案

<br><br>
**汇报人：** 课题参与人
**汇报时间：** 2026年04月

---

## 1. 研发背景与研究目标

在复杂的工程计算与理论推导中，手工计算极易产生**人因误差*且难以追溯中间过程。本系统旨在解决以下痛点：

<div class="card">
<strong>🎯 核心目标：</strong>
构建一个支持<b>动态无限层级推导</b>的自动化公式解析平台，实现输入即计算、计算即出具报告。
</div>

- **痛点一**：传统计算器无法保存复杂公式的依赖关系。
- **痛点二**：中间推导步骤丢失，导师溯源和检查极度不便。
- **痛点三**：复杂数学公式缺乏排版级的高清图元留存，无法直接用于论文写作。

---

## 2. 核心架构与技术路线

系统深度整合了 Python 生态中的顶尖工具链，实现了从 **UI交互 -> 本地内存 AST (抽象语法树) 解析 -> 报告落盘** 的全管线。

<div class="card">
<strong>💡 技术栈矩阵：</strong>
<ul>
  <li><b>[交互层]</b> Tkinter: 轻量级跨平台 GUI 响应式框架</li>
  <li><b>[计算层]</b> SymPy: 强健的符号计算与数学引擎</li>
  <li><b>[渲染层]</b> Matplotlib / PIL: 内存级别的 LaTeX 图元构建系统</li>
</ul>
</div>

**计算流转：**
用户输入公式 $\rightarrow$ `parse_expr` 构建对象树 $\rightarrow$ 提取变量子集 (`free_symbols`) $\rightarrow$ 逐层代入进行高精度求解。

---

## 3. 关键特性：自动化解析与动态级联

本系统的最大创新点在于 **“变量感知的动态下探推导”** 能力：

1. **自动变量辨识**
   - 通过正则表达式与符号集合比对，自动过滤已知内置函数（`sin, cos, exp`...），精确抓取未赋值变量。
2. **多层级动态交互**
   - 赋值阶段若变量未知，可**直接定义该部分的新子公式**。
   - 程序将嵌套调用赋值窗口，支持极高深度的级联方程推导。
3. **彻底杜绝数值丢失**
   - 统一采用 15位浮点数字高精度保留方案。

---

## 4. 全流程溯源与学术级数据输出

系统不仅仅是计算器，更是**科研流程的数据产出工具**。对于任何一次执行，均会自动静默打包以下文件组合：

| 产物类目 | 数据格式 | 学术应用场景 |
| :--- | :--- | :--- |
| **公式静态图元** | `.png (300dpi)` | 自动渲染成标准 LaTeX 排版图，直接贴入论文与汇报中。 |
| **全量变量库** | `.txt` 对齐文本 | 清晰罗列所有主公式和子公式中的参数值，方便溯源。 |
| **Web 溯源报告** | `.html` 格式 | 计算全景总览，从顶层结果到最底层的推导过程图文并茂展示。 |

---

<!-- _class: lead-slide -->

# 演示完毕，感谢指导！
### Q & A

---
