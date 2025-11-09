#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt


def process_file(file_path):
    """
    读取数据文件，跳过前两行，
    将每行数据按空白分隔并取：
      第一列作为 x，
      第二列作为 y1，
      第四列作为 y2。
    返回三个列表 [x, y1, y2]，解析失败则返回 None。
    """
    x, y1, y2 = [], [], []
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        if len(lines) <= 2:
            print(f"[提示] 文件 {file_path} 数据量不足，忽略。")
            return None
        for line in lines[2:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                x_val = float(parts[0])
                y1_val = float(parts[1])
                y2_val = float(parts[3])
                x.append(x_val)
                y1.append(y1_val)
                y2.append(y2_val)
            except Exception as e:
                print(f"[错误] 解析文件 {file_path} 的行：'{line}' 出错：{e}")
                continue
        if len(x) == 0:
            print(f"[提示] 文件 {file_path} 内没有获得有效数据。")
            return None
        return x, y1, y2
    except Exception as e:
        print(f"[错误] 读取文件 {file_path} 失败：{e}")
        return None


def plot_data(x, y1, y2, output_path, title=""):
    """
    根据数据绘制左右两张图（第一张：x-y1；第二张：x-y2），
    并保存到 output_path。title 用于图的总标题显示。
    """
    fig, axs = plt.subplots(1, 2, figsize=(12, 6))
    axs[0].plot(x, y1, marker='o')
    axs[0].set_title("Plot y1")
    axs[0].set_xlabel("x")
    axs[0].set_ylabel("y1")

    axs[1].plot(x, y2, marker='o', color='orange')
    axs[1].set_title("Plot y2")
    axs[1].set_xlabel("x")
    axs[1].set_ylabel("y2")

    if title:
        fig.suptitle(title)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    try:
        fig.savefig(output_path)
        print(f"[成功] 已保存图像至：{output_path}")
    except Exception as e:
        print(f"[错误] 保存图像 {output_path} 失败：{e}")
    plt.close(fig)


def generate_summary_html(summary_dir, summary_data):
    """
    在 summary_dir（例如形如 "4-3" 的目录）下生成一个汇总 HTML 文件，
    列出 summary_data 内的每个项，每项包含：
       - data_folder_path: 数据文件所在文件夹的绝对路径（点击后会复制此路径到剪贴板）
       - image_rel_path: 相对于 summary_dir 的图像路径（例如 "2025_3_20/graph/scan1.txt.png"）
       - title: 显示标题（例如 "2025_3_20/scan1.txt"）

    HTML 内置了 JavaScript 函数 copyToClipboard(text, el)，当点击对应文本时，
    将复制目录路径到剪贴板，并将该文本颜色改为绿色表示已复制成功。
    """
    html_lines = []
    html_lines.append("<html>")
    html_lines.append("<head>")
    html_lines.append("<meta charset='utf-8'>")
    html_lines.append(f"<title>Summary for {os.path.basename(summary_dir)}</title>")
    html_lines.append("<script>")
    html_lines.append(r"""
function copyToClipboard(text, el) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            el.style.color = "green";
        }, function(err) {
            el.style.color = "red";
        });
    } else {
        var input = document.createElement("input");
        input.value = text;
        document.body.appendChild(input);
        input.select();
        try {
            document.execCommand("copy");
            el.style.color = "green";
        } catch (err) {
            el.style.color = "red";
        }
        document.body.removeChild(input);
    }
}
    """)
    html_lines.append("</script>")
    html_lines.append("</head>")
    html_lines.append("<body>")
    html_lines.append(f"<h1>Summary for folder: {os.path.basename(summary_dir)}</h1>")
    html_lines.append("<ul>")
    for entry in summary_data:
        # 点击后调用 copyToClipboard，同时传入 this，让当前元素变色
        line = (
            "<li>"
            "<span onclick=\"copyToClipboard('{data_folder_path}', this)\" style=\"cursor:pointer; color:blue; text-decoration:underline;\">{title}</span><br>"
            "<img src='{image_rel_path}' style='max-width:600px;'><br><br>"
            "</li>"
        ).format(**entry)
        html_lines.append(line)
    html_lines.append("</ul>")
    html_lines.append("</body>")
    html_lines.append("</html>")
    summary_path = os.path.join(summary_dir, "summary.html")
    try:
        with open(summary_path, 'w', encoding="utf-8") as f:
            f.write("\n".join(html_lines))
        print(f"[成功] 生成汇总 HTML：{summary_path}")
    except Exception as e:
        print(f"[错误] 生成汇总 HTML {summary_path} 时出错：{e}")


def process_folder(root_dir):
    """
    遍历 root_dir 下的所有子目录，对文件扩展名为 ".txt"、空字符串或
    被 splitext 识别为扩展名但长度超过 5（这里认为此时文件名中包含的点并非真正扩展名）的文件进行处理，
    生成图像保存在原文件所在文件夹下的 graph 子目录内。

    同时，若文件所在路径形如 .../<汇总目录>/<日期文件夹>/数据文件，
    且汇总目录名称满足正则 r"^\d+-\d+$"（如 “4-3”、“4-1”），
    则将该数据记录保存用于后续在汇总目录下生成 HTML 汇总，图题显示为 “日期/文件名”，
    点击时复制数据文件所在目录（绝对路径）到剪贴板。
    """
    summary_dict = {}  # key: 汇总目录绝对路径； value: list（汇总数据字典）

    for current_dir, _, files in os.walk(root_dir):
        for file in files:
            base, ext = os.path.splitext(file)
            ext = ext.lower()
            # 如果扩展名为 ".txt" 或为空，直接处理；
            # 如果扩展名不为空，但长度超过 5（例如 ".0 10kV scan1"），认为这不是实际扩展名
            if not (ext == ".txt" or ext == ""):
                if len(ext) > 5:
                    # 当作无扩展名处理
                    pass
                else:
                    continue

            file_path = os.path.join(current_dir, file)
            data = process_file(file_path)
            if data is None:
                continue
            x, y1, y2 = data

            # 创建用于存放图像的 graph 文件夹
            graph_dir = os.path.join(current_dir, "graph")
            os.makedirs(graph_dir, exist_ok=True)

            output_file = file + ".png"
            output_path = os.path.join(graph_dir, output_file)
            plot_data(x, y1, y2, output_path, title=file)

            # 判断是否属于类似 .../<汇总目录>/<日期文件夹>/数据文件 的结构
            date_folder = os.path.basename(current_dir)
            parent_dir = os.path.dirname(current_dir)
            summary_folder_name = os.path.basename(parent_dir)
            if re.match(r"^\d+-\d+$", summary_folder_name):
                summary_folder_path = parent_dir  # 例如 .../4-1
                image_rel_path = os.path.join(date_folder, "graph", output_file).replace("\\", "/")
                # 获取数据文件所在目录的绝对路径，并将反斜杠替换为正斜杠，确保 JS 复制正确
                data_folder_abs = os.path.abspath(current_dir).replace("\\", "/")
                entry = {
                    'image_rel_path': image_rel_path,
                    'data_folder_path': data_folder_abs,
                    'title': f"{date_folder}/{file}"
                }
                summary_dict.setdefault(summary_folder_path, []).append(entry)

    # 为每个汇总目录生成 summary.html
    for summary_folder, summary_data in summary_dict.items():
        generate_summary_html(summary_folder, summary_data)


def main():
    root = tk.Tk()
    root.withdraw()  # 隐藏 tkinter 主窗口
    folder_selected = filedialog.askdirectory(title="请选择目标文件夹")
    if not folder_selected:
        print("未选择目标文件夹，程序退出。")
        return
    print(f"[信息] 选择的文件夹为：{folder_selected}")
    process_folder(folder_selected)
    print("所有文件处理完成！")


if __name__ == "__main__":
    main()
