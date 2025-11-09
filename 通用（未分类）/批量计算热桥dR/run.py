import os
import re
import tkinter as tk
from tkinter import filedialog
import platform
import subprocess
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.stats import linregress
import matplotlib.pyplot as plt
import threading

# 设置 Matplotlib 使用中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用中文黑体，需系统中已安装该字体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示问题

# 如果需要自动打开输出目录（这里保留此函数）
def open_directory(directory):
    system_name = platform.system()
    if system_name == 'Windows':
        os.startfile(directory)
    elif system_name == 'Darwin':  # macOS
        subprocess.Popen(['open', directory])
    else:
        subprocess.Popen(['xdg-open', directory])

# 处理单个数据文件，读取数据（跳过前两行）
def process_file(file_path):
    I2, R1, R2 = [], [], []
    with open(file_path, 'r') as file:
        lines = file.readlines()[2:]  # 跳过前两行
        for line in lines:
            columns = line.split()
            if len(columns) >= 5:
                I2.append(float(columns[1]))
                R1.append(float(columns[2]))
                R2.append(float(columns[4]))
    return np.array(I2), np.array(R1), np.array(R2)

# 根据数据计算拟合曲线，生成一个 Figure 对象，并返回图形及拟合信息
def create_figure_for_file(file_path, title):
    I2, R1, R2 = process_file(file_path)
    if len(I2) == 0:
        return None, None, None
    # 分别计算 R1 和 R2 的线性拟合
    slope_R1, intercept_R1, *_ = linregress(I2, R1)
    slope_R2, intercept_R2, *_ = linregress(I2, R2)
    dx = max(I2) - min(I2)
    dR1 = slope_R1 * dx
    dR2 = slope_R2 * dx

    # 使用 Matplotlib 创建一个图形对象
    fig = Figure(figsize=(4, 3), dpi=100)
    ax = fig.add_subplot(111)
    ax.plot(I2, R1, 'o', label='原始数据 R1')
    ax.plot(I2, intercept_R1 + slope_R1 * I2, 'r', label='拟合 R1')
    ax.set_xlabel('I2')
    ax.set_ylabel('R1')
    ax.set_title(title)
    ax.legend()
    return fig, dR1, dR2

# 主程序：创建带滚动条的窗口，嵌入所有图表，并将图保存到输出目录下的 graph 文件夹
def main():
    # 创建主窗口并设置初始尺寸
    root = tk.Tk()
    root.title("批量数据图表（滚动浏览）")
    root.geometry("400x800")

    # 创建顶层 Frame（用于放 Canvas 与滚动条）
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 创建 Canvas，并添加垂直滚动条
    canvas = tk.Canvas(main_frame)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    v_scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.configure(yscrollcommand=v_scrollbar.set)

    # 在 Canvas 内创建 Frame 用于放入所有图表
    graph_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=graph_frame, anchor="nw")

    # 当 Canvas 改变大小时，调整滚动区域
    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    canvas.bind('<Configure>', on_configure)

    # 选择包含数据文件的根目录（要求其下有子文件夹）
    root_directory = filedialog.askdirectory(title='选择包含数据文件夹的根目录')
    if not root_directory:
        print('未选择任何目录，程序退出。')
        return

    # 在输出目录下建立一个名为 "graph" 的文件夹，用于保存所有生成的图
    graph_folder = os.path.join(root_directory, 'graph')
    if not os.path.exists(graph_folder):
        os.makedirs(graph_folder)

    overall_result = ""  # 累计总体结果文本
    row = 0  # 用于 grid 布局的行号

    # 遍历根目录内的子文件夹（保持原遍历子文件夹的逻辑）
    for subdir in os.listdir(root_directory):
        subdir_path = os.path.join(root_directory, subdir)
        if os.path.isdir(subdir_path):
            for file_name in os.listdir(subdir_path):
                if file_name.lower().endswith('.txt'):
                    # 使用正则表达式提取温度
                    match = re.search(r'(\d+(?:\.\d+)?)K', file_name)
                    if not match:
                        continue
                    temperature = float(match.group(1))
                    file_path = os.path.join(subdir_path, file_name)
                    title = f"{file_name} (T={temperature})"
                    # 创建图形对象
                    fig, dR1, dR2 = create_figure_for_file(file_path, title)
                    if fig is None:
                        continue

                    # 保存图形到 graph 文件夹，文件名以原文件名为基础（.txt 替换为 .png）
                    save_path = os.path.join(graph_folder, file_name.replace('.txt', '.png'))
                    fig.savefig(save_path)

                    # 将图表嵌入到 Tkinter GUI 中
                    fig_canvas = FigureCanvasTkAgg(fig, master=graph_frame)
                    fig_canvas.draw()
                    widget = fig_canvas.get_tk_widget()
                    widget.grid(row=row, column=0, padx=5, pady=5, sticky="nw")

                    # 在图形旁边显示拟合结果信息
                    info = f"dR1: {dR1:.2f}, dR2: {dR2:.2f}"
                    label = tk.Label(graph_frame, text=info, anchor="w", font=("Microsoft YaHei", 10))
                    label.grid(row=row, column=1, padx=5, pady=5, sticky="nw")

                    overall_result += f"{file_name}: T={temperature}, {info}\n"
                    row += 1

    # 如果有总体结果，将其显示在界面下方的 Text 框中
    if overall_result:
        text_box = tk.Text(graph_frame, height=10, width=80)
        text_box.insert(tk.END, overall_result)
        text_box.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

    graph_frame.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))

    # 以新线程的方式打开输出目录 —— 这里打开的是包含输出表格的目录（即根目录）
    threading.Thread(target=lambda: open_directory(root_directory), daemon=True).start()

    root.mainloop()

if __name__ == '__main__':
    main()
